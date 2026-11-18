"""Amendment 2 (exploratory, after an internal review). Writes out/robustness2.json.
Run from the repository root: python -I code/robustness2.py

1. Net-load variants: D-S-W (main), D-S (solar only), D-W (wind only), D-S_ns-W (solar without integrated storage).
2. Days complete in D and NL only (no forecast requirement).
3. 2019 vs 2025; month-stratified shifts; without the BAs that do not observe daylight saving time.
4. Mean peak hour, share of days with the net-load peak at hour ending 20 or later; dose-response (Spearman).
5. H3 at fixed hours (each BA's late-period median hours, rounded) instead of each day's realised peak hour.
6. Solar timestamp check: hour of the median daily solar maximum and night-time solar share per BA and summer.
7. Swap: peak hour of median profiles D_early - (S+W)_late and D_late - (S+W)_early.
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

SUMMER = [6, 7, 8, 9]
NODST = ["AZPS", "SRP", "TEPC"]
T = pd.read_csv("out/ba_table.csv", index_col=0)
cov = pd.read_csv("out/gen_coverage.csv", index_col=0)
d = pd.read_parquet("data/eia930_gen.parquet")
d = d[d["ba"].isin(T.index) & d["date"].dt.year.isin([2019, 2020, 2021, 2024, 2025, 2026]) & d["date"].dt.month.isin(SUMMER)]
high = list(T.index[T["group"] == "high"])


def prep(ba):
    g = d[d["ba"] == ba].set_index("utc_end").sort_index()
    full = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    ref = full["demand"].where(full["demand"] > 0).rolling(168, center=True, min_periods=24).median().reindex(g.index)
    for c in ("demand", "forecast"):
        x = g[c]
        g[c] = x.mask((x <= 0) | (x > 2.0 * ref) | (x < 0.3 * ref))
    for c in ("solar", "solar_ns", "wind"):
        g[c] = g[c].clip(lower=0)
    if cov.loc[ba, "wind_present"] < 0.01:
        g["wind"] = 0.0
    for c in ("solar", "wind"):
        share = cov.loc[ba, f"{c}_share_2025"]
        if cov.loc[ba, f"{c}_present"] < 0.01 or not np.isfinite(share) or share < 0.01:
            g[c] = g[c].fillna(0.0)
            if c == "solar":
                g["solar_ns"] = g["solar_ns"].fillna(0.0)
    g["NL"] = g["demand"] - g["solar"] - g["wind"]
    g["NLs"] = g["demand"] - g["solar"]
    g["NLw"] = g["demand"] - g["wind"]
    g["NLns"] = g["demand"] - g["solar_ns"] - g["wind"]
    return g


def daily(g, col, needF=True):
    need = ["demand", col] + (["forecast"] if needF else [])
    ok = g[need].notna().all(axis=1)
    n = g.groupby("date").size()
    nok = ok.groupby(g["date"]).sum()
    good = n.index[(n >= 24) & (nok == n)]
    h = g[g["date"].isin(good)]
    grp = h.groupby("date")
    return pd.DataFrame({"hD": h.loc[grp["demand"].idxmax(), "hour"].values, "hNL": h.loc[grp[col].idxmax(), "hour"].values},
                        index=grp["demand"].idxmax().index)


def shifts(D, early, late):
    e, l = D[D.index.year.isin(early)], D[D.index.year.isin(late)]
    if len(e) < 30 or len(l) < 30:
        return None
    return {"shift": float(l["hNL"].median() - e["hNL"].median()),
            "gap": float((l["hNL"].median() - l["hD"].median()) - (e["hNL"].median() - e["hD"].median())),
            "mean_shift": float(l["hNL"].mean() - e["hNL"].mean()),
            "late20_e": float((e["hNL"] >= 20).mean()), "late20_l": float((l["hNL"] >= 20).mean()),
            "month_shift": float(np.nanmedian([l[l.index.month == m]["hNL"].median() - e[e.index.month == m]["hNL"].median()
                                               for m in SUMMER]))}


def sign(x, alt="greater"):
    x = np.asarray([v for v in x if np.isfinite(v) and v != 0])
    k = int((x > 0).sum())
    return {"pos": k, "n": int(len(x)), "p": float(stats.binomtest(k, len(x), 0.5, alternative=alt).pvalue) if len(x) else np.nan}


E, L = [2019, 2020], [2025, 2026]
res, per = {}, {}
G = {ba: prep(ba) for ba in T.index}
for name, col, needF, early, late in (("main_noF", "NL", False, E, L), ("solar_only", "NLs", True, E, L),
                                      ("wind_only", "NLw", True, E, L), ("solar_no_storage", "NLns", True, E, L),
                                      ("y2019_vs_2025", "NL", True, [2019], [2025]), ("main", "NL", True, E, L)):
    rows = {}
    for ba in T.index:
        s = shifts(daily(G[ba], col, needF), early, late)
        if s:
            rows[ba] = s
    R = pd.DataFrame(rows).T
    per[name] = R
    Hh = R.loc[[b for b in high if b in R.index]]
    res[name] = {"H1": sign(Hh["shift"]), "H2": sign(Hh["gap"]), "n_high": int(len(Hh)),
                 "median_shift": float(Hh["shift"].median()), "mean_shift_median": float(Hh["mean_shift"].median())}
M = per["main"]
Hm = M.loc[[b for b in high if b in M.index]]
res["month_stratified"] = sign(Hm["month_shift"])
res["no_dst_excluded"] = {"H1": sign(Hm.drop(index=[b for b in NODST if b in Hm.index])["shift"]),
                          "H2": sign(Hm.drop(index=[b for b in NODST if b in Hm.index])["gap"])}
res["mean_hour"] = sign(Hm["mean_shift"])
res["mean_hour_median"] = float(Hm["mean_shift"].median())
rng = np.random.default_rng(20261119)
bs = [np.median(rng.choice(Hm["mean_shift"].values, len(Hm))) for _ in range(5000)]
res["mean_hour_ci"] = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
res["median_shift_per_ba"] = float(Hm["shift"].median())
res["mean_shift_per_ba"] = float(Hm["shift"].mean())
res["late20"] = {"early": float(Hm["late20_e"].median()), "late": float(Hm["late20_l"].median()),
                 "test": sign(Hm["late20_l"] - Hm["late20_e"])}
sh = T["solar_share_2025"].fillna(0)
rho = stats.spearmanr(sh.loc[M.index], M["shift"])
res["spearman_all"] = {"rho": float(rho.statistic), "p": float(rho.pvalue), "n": int(len(M))}
low = M.drop(index=[b for b in high if b in M.index])
rl = stats.spearmanr(sh.loc[low.index], low["shift"])
res["spearman_low"] = {"rho": float(rl.statistic), "p": float(rl.pvalue), "n": int(len(low))}

# 5. H3 at fixed hours
fx = {}
for ba in high:
    g = G[ba]
    Dd = daily(g, "NL", True)
    l = Dd[Dd.index.year.isin(L)]
    if len(l) < 30:
        continue
    hd, hn = int(round(l["hD"].median())), int(round(l["hNL"].median()))
    gl = g[g["date"].dt.year.isin(L) & g["date"].isin(l.index)]
    ape = 100 * (gl["forecast"] - gl["demand"]).abs() / gl["demand"]
    a_d = ape[gl["hour"] == hd].median()
    a_n = ape[gl["hour"] == hn].median()
    fx[ba] = {"h_d": hd, "h_nl": hn, "ape_d": float(a_d), "ape_nl": float(a_n), "diff": float(a_n - a_d)}
F = pd.DataFrame(fx).T
dd = F["diff"].astype(float)
res["H3_fixed_hours"] = {"sign": sign(dd, "two-sided"), "median_diff": float(dd.median()),
                         "wilcoxon_p": float(stats.wilcoxon(dd[dd != 0]).pvalue) if (dd != 0).sum() > 5 else np.nan}
fx_noc = dd.drop(index=[b for b in ("CISO",) if b in dd.index])
res["H3_fixed_hours_noCISO"] = sign(fx_noc, "two-sided")

# 6. solar timestamp check
ts = {}
for ba in high:
    g = G[ba]
    s = g[g["solar"].notna()]
    yrs = {}
    for y, gy in s.groupby(s["date"].dt.year):
        if len(gy) < 24 * 30:
            continue
        idx = gy.groupby("date")["solar"].idxmax()
        hmax = float(gy.loc[idx, "hour"].median())
        night = gy[gy["hour"].isin([22, 23, 24, 1, 2, 3, 4])]["solar"].sum() / max(gy["solar"].sum(), 1)
        yrs[int(y)] = {"hmax": hmax, "night_share": float(night)}
    ts[ba] = yrs
res["solar_timestamps"] = ts
moved = [b for b, v in ts.items() if v and (max(x["hmax"] for x in v.values()) - min(x["hmax"] for x in v.values())) >= 1]
res["solar_hmax_moved_bas"] = moved
res["solar_night_share_max"] = float(max(x["night_share"] for v in ts.values() for x in v.values()))

# 7. swap of median profiles
sw = {}
for ba in high:
    g = G[ba].dropna(subset=["demand", "solar", "wind"])
    g = g.assign(sw=g["solar"] + g["wind"], per=np.where(g["date"].dt.year.isin(E), "e", np.where(g["date"].dt.year.isin(L), "l", "")))
    g = g[g["per"] != ""]
    prof = g.groupby(["per", "hour"])[["demand", "sw"]].median()
    try:
        De, Dl = prof.loc["e", "demand"], prof.loc["l", "demand"]
        Se, Sl = prof.loc["e", "sw"], prof.loc["l", "sw"]
    except KeyError:
        continue
    pk = lambda x: int(x.idxmax())
    sw[ba] = {"ee": pk(De - Se), "el": pk(De - Sl), "le": pk(Dl - Se), "ll": pk(Dl - Sl)}
S = pd.DataFrame(sw).T
res["swap"] = {"supply_effect": sign(S["el"] - S["ee"]), "demand_effect": sign(S["le"] - S["ee"], "two-sided"),
               "median_supply_effect": float((S["el"] - S["ee"]).median()),
               "median_demand_effect": float((S["le"] - S["ee"]).median()), "n": int(len(S))}
json.dump(res, open("out/robustness2.json", "w"), indent=1, default=float)
F.to_csv("out/h3_fixed_hours.csv")
S.to_csv("out/swap_profiles.csv")
print(json.dumps({k: v for k, v in res.items() if k != "solar_timestamps"}, indent=1, default=float))
