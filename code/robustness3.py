"""Amendment 3 (exploratory, after an independent review). Writes out/robustness3.json and out/robustness3_ba.csv.
Run from the repository root: python -I code/robustness3.py

1. Every BA: shift with solar only / wind only subtracted, summer solar and wind energy shares, profile swap,
   demand-profile gap between the demand peak hour and the late net-load peak hour, solar timestamps, local-UTC offset.
2. Pre-trend placebo: July-September 2018 against July-September 2019.
3. Continuous peak time: parabolic vertex at the daily net-load maximum; circular mean of the integer peak hour.
4. Mechanical counterfactual from median profiles: early shapes with late volumes.
5. Forecast-offset scan (BA x summer) and H3 without the BAs with data-quality issues.
"""
import json

import numpy as np
import pandas as pd
from scipy import stats

SUMMER = [6, 7, 8, 9]
E, L = [2019, 2020], [2025, 2026]
T = pd.read_csv("out/ba_table.csv", index_col=0)
cov = pd.read_csv("out/gen_coverage.csv", index_col=0)
d = pd.read_parquet("data/eia930_gen.parquet")
d = d[d["ba"].isin(T.index) & (d["date"] >= "2018-06-01") & (d["date"] <= "2026-09-30")]
high = list(T.index[T["group"] == "high"])
low = list(T.index[T["group"] == "low"])


def prep(ba):
    """Screening and zero rules exactly as code/solar.py (plus the solar-only and wind-only net loads)."""
    g = d[d["ba"] == ba].set_index("utc_end").sort_index()
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    ref = g["demand"].where(g["demand"] > 0).rolling(168, center=True, min_periods=24).median()
    for c in ("demand", "forecast"):
        x = g[c]
        g[c] = x.mask((x <= 0) | (x > 2.0 * ref) | (x < 0.3 * ref))
    g["solar"] = g["solar"].clip(lower=0)
    if cov.loc[ba, "wind_present"] < 0.01:
        g["wind"] = 0.0
    g["wind"] = g["wind"].clip(lower=0)
    for c in ("solar", "wind"):
        share = cov.loc[ba, f"{c}_share_2025"]
        if cov.loc[ba, f"{c}_present"] < 0.01 or not np.isfinite(share) or share < 0.01:
            g[c] = g[c].fillna(0.0)
    g["NL"] = g["demand"] - g["solar"] - g["wind"]
    g["NLs"] = g["demand"] - g["solar"]
    g["NLw"] = g["demand"] - g["wind"]
    g = g.dropna(subset=["date"])
    return g[g["date"].dt.month.isin(SUMMER)]


def vertex(Y):
    """Peak time of each row of Y (columns = hours 1..24): integer argmax plus the vertex offset of the parabola
    through the maximum and its two neighbours, clipped to +-0.5 h; integer hour at the first or last hour."""
    Y = np.asarray(Y, float)
    i = np.argmax(Y, axis=1)
    r = np.arange(len(Y))
    inner = (i > 0) & (i < Y.shape[1] - 1)
    ym = Y[r, np.clip(i - 1, 0, None)]
    y0 = Y[r, i]
    yp = Y[r, np.clip(i + 1, None, Y.shape[1] - 1)]
    den = ym - 2 * y0 + yp
    with np.errstate(divide="ignore", invalid="ignore"):
        delta = np.where(inner & (den < 0), 0.5 * (ym - yp) / den, 0.0)
    return i + 1 + np.clip(delta, -0.5, 0.5)


def daily(g, col, needF=True):
    """Complete days (as code/solar.py): integer peak hours of D and col, vertex peak time of col."""
    need = ["demand", col] + (["forecast"] if needF else [])
    ok = g[need].notna().all(axis=1)
    n = g.groupby("date").size()
    nok = ok.groupby(g["date"]).sum()
    good = n.index[(n == 24) & (nok == n)]
    h = g[g["date"].isin(good)]
    P = h.pivot_table(index="date", columns="hour", values=col, aggfunc="first").reindex(columns=range(1, 25))
    PD = h.pivot_table(index="date", columns="hour", values="demand", aggfunc="first").reindex(columns=range(1, 25))
    P, PD = P.dropna(), PD.loc[P.dropna().index]
    return pd.DataFrame({"hD": np.argmax(PD.values, axis=1) + 1, "hNL": np.argmax(P.values, axis=1) + 1,
                         "tNL": vertex(P.values)}, index=P.index)


def circ(h):
    a = 2 * np.pi * np.asarray(h, float) / 24
    return (24 * np.arctan2(np.sin(a).mean(), np.cos(a).mean()) / (2 * np.pi)) % 24


def wrap(x):
    return (x + 12) % 24 - 12


def sel(D, years, months=SUMMER):
    return D[D.index.year.isin(years) & D.index.month.isin(months)]


def contrast(D, early, late, months=SUMMER):
    e, l = sel(D, early, months), sel(D, late, months)
    if len(e) < 30 or len(l) < 30:
        return None
    return {"shift": float(l["hNL"].median() - e["hNL"].median()),
            "gap": float((l["hNL"].median() - l["hD"].median()) - (e["hNL"].median() - e["hD"].median())),
            "mean_shift": float(l["hNL"].mean() - e["hNL"].mean()),
            "vtx_early": float(e["tNL"].median()), "vtx_late": float(l["tNL"].median()),
            "vtx_shift": float(l["tNL"].median() - e["tNL"].median()),
            "circ_shift": float(wrap(circ(l["hNL"]) - circ(e["hNL"]))),
            "hD_shift": float(l["hD"].median() - e["hD"].median()), "n_e": int(len(e)), "n_l": int(len(l))}


def sign(x, alt="greater"):
    x = np.asarray([v for v in x if np.isfinite(v) and v != 0])
    k = int((x > 0).sum())
    return {"pos": k, "n": int(len(x)), "p": float(stats.binomtest(k, len(x), 0.5, alternative=alt).pvalue) if len(x) else np.nan}


def wil(x, alt="greater"):
    x = np.asarray([v for v in x if np.isfinite(v) and v != 0])
    return float(stats.wilcoxon(x, alternative=alt).pvalue) if len(x) > 5 else np.nan


def mw(a, b, alt="greater"):
    a, b = np.asarray(a, float), np.asarray(b, float)
    a, b = a[np.isfinite(a)], b[np.isfinite(b)]
    r = stats.mannwhitneyu(a, b, alternative=alt)
    return {"U": float(r.statistic), "p": float(r.pvalue), "n_high": int(len(a)), "n_low": int(len(b)),
            "median_high": float(np.median(a)), "median_low": float(np.median(b))}


G = {ba: prep(ba) for ba in T.index}
res, per = {}, {}
check = {}
for ba, g in G.items():
    row = {"group": T.loc[ba, "group"]}
    Dm = daily(g, "NL")
    m = contrast(Dm, E, L)
    check[ba] = m["shift"] - T.loc[ba, "shift_NL"] if m else np.nan
    row.update({f"main_{k}": v for k, v in (m or {}).items()})
    for col, tag in (("NLs", "sol"), ("NLw", "wnd")):
        c = contrast(daily(g, col), E, L)
        row[f"{tag}_shift"] = c["shift"] if c else np.nan
    # 2. pre-trend placebo, Jul-Sep 2018 vs Jul-Sep 2019; main contrast on Jul-Sep for comparison
    pt = contrast(Dm, [2018], [2019], [7, 8, 9])
    row.update({f"pre_{k}": v for k, v in (pt or {}).items()})
    js = contrast(Dm, E, L, [7, 8, 9])
    row.update({f"jas_{k}": v for k, v in (js or {}).items()})
    # 1. summer energy shares, solar timestamps, local-UTC offset
    for tag, yrs in (("e", E), ("l", L), ("y18", [2018])):
        gy = g[g["date"].dt.year.isin(yrs)].dropna(subset=["demand", "solar", "wind"])
        row[f"solar_share_{tag}"] = float(gy["solar"].sum() / gy["demand"].sum()) if len(gy) else np.nan
        row[f"wind_share_{tag}"] = float(gy["wind"].sum() / gy["demand"].sum()) if len(gy) else np.nan
    s = g[g["solar"].notna()]
    for y, gy in s.groupby(s["date"].dt.year):
        if len(gy) < 24 * 30 or gy["solar"].sum() <= 0:
            continue
        idx = gy.groupby("date")["solar"].idxmax()
        row[f"solar_hmax_{y}"] = float(gy.loc[idx, "hour"].median())
        row[f"solar_night_{y}"] = float(gy[gy["hour"].isin([22, 23, 24, 1, 2, 3, 4])]["solar"].sum() / gy["solar"].sum())
    off = (pd.Series(g.index, index=g.index) - (g["date"] + pd.to_timedelta(g["hour"], unit="h"))) / pd.Timedelta(hours=1)
    offs = off.groupby(g["date"].dt.year.values).agg(lambda x: x.mode().iloc[0] if len(x) else np.nan)
    row["utc_offsets"] = ",".join(f"{int(v)}" for v in sorted(set(offs.dropna())))
    # 1 + 4. median profiles: swap, demand-profile gap, mechanical counterfactual
    gp = g.dropna(subset=["demand", "solar", "wind"])
    gp = gp.assign(per=np.where(gp["date"].dt.year.isin(E), "e", np.where(gp["date"].dt.year.isin(L), "l", "")))
    gp = gp[gp["per"] != ""]
    prof = gp.groupby(["per", "hour"])[["demand", "solar", "wind"]].median()
    try:
        De, Dl = prof.loc["e", "demand"].reindex(range(1, 25)), prof.loc["l", "demand"].reindex(range(1, 25))
        Se, Sl = prof.loc["e", "solar"].reindex(range(1, 25)), prof.loc["l", "solar"].reindex(range(1, 25))
        We, Wl = prof.loc["e", "wind"].reindex(range(1, 25)), prof.loc["l", "wind"].reindex(range(1, 25))
    except KeyError:
        per[ba] = row
        continue
    kS = Sl.sum() / Se.sum() if Se.sum() > 0 else np.nan
    kW = Wl.sum() / We.sum() if We.sum() > 0 else (1.0 if Wl.sum() == 0 else np.nan)
    v = lambda x: float(vertex(np.asarray(x, float)[None, :])[0])
    ee, ll = v(De - Se - We), v(Dl - Sl - Wl)
    row.update({"kS": float(kS), "kW": float(kW), "prof_ee": ee, "prof_ll": ll, "prof_obs_shift": ll - ee,
                "swap_supply_shift": v(De - Sl - Wl) - ee, "swap_demand_shift": v(Dl - Se - We) - ee,
                "mech_shift": (v(Dl - kS * Se - kW * We) - ee) if np.isfinite(kS) and np.isfinite(kW) else np.nan})
    hDe, hNLl = int(np.argmax(De.values)) + 1, int(round(T.loc[ba, "hNL_late"]))
    row["d_gap_pct"] = float(100 * (De[hDe] - De[hNLl]) / De[hDe])
    row["s_drop_pct"] = float(100 * (Sl[hDe] - Sl[hNLl]) / De[hDe])
    row["w_drop_pct"] = float(100 * (Wl[hDe] - Wl[hNLl]) / De[hDe])
    row["hD_prof_e"], row["hNL_late_used"] = hDe, hNLl
    per[ba] = row
P = pd.DataFrame(per).T
P.index.name = "ba"
num = lambda c: pd.to_numeric(P[c], errors="coerce")
res["check_max_abs_diff_vs_main"] = float(np.nanmax(np.abs(list(check.values()))))
Hh, Ll = P.loc[high], P.loc[low]

# 1. low-solar BAs that moved
movers = sorted(T.index[(T["group"] == "low") & (T["shift_NL"] >= 2)])
cols = ["main_shift", "main_hD_shift", "sol_shift", "wnd_shift", "solar_share_e", "solar_share_l", "wind_share_e",
        "wind_share_l", "swap_supply_shift", "swap_demand_shift", "mech_shift", "prof_obs_shift", "d_gap_pct",
        "s_drop_pct", "w_drop_pct", "hD_prof_e", "hNL_late_used", "utc_offsets"] + \
       [c for c in P.columns if c.startswith("solar_hmax_") or c.startswith("solar_night_")]
res["low_movers"] = {b: {c: (P.loc[b, c] if not isinstance(P.loc[b, c], (float, np.floating)) or np.isfinite(P.loc[b, c]) else None)
                         for c in cols if c in P.columns} for b in movers}
res["low_group"] = {"sol": sign(num("sol_shift").loc[low]), "wnd": sign(num("wnd_shift").loc[low]),
                    "median_solar_share_l": float(num("solar_share_l").loc[low].median())}
res["utc_offset_changes"] = sorted(b for b in P.index if "," in str(P.loc[b, "utc_offsets"]))

# 2. pre-trend placebo
res["pretrend"] = {"H1": sign(num("pre_shift").loc[high]), "H1_two_sided": sign(num("pre_shift").loc[high], "two-sided"),
                   "low": sign(num("pre_shift").loc[low], "two-sided"),
                   "median_shift_high": float(num("pre_shift").loc[high].median()),
                   "median_shift_low": float(num("pre_shift").loc[low].median()),
                   "median_mean_shift_high": float(num("pre_mean_shift").loc[high].median()),
                   "median_mean_shift_low": float(num("pre_mean_shift").loc[low].median()),
                   "median_vtx_shift_high": float(num("pre_vtx_shift").loc[high].median()),
                   "median_vtx_shift_low": float(num("pre_vtx_shift").loc[low].median()),
                   "H4": mw(num("pre_shift").loc[high], num("pre_shift").loc[low]),
                   "H4_vtx": mw(num("pre_vtx_shift").loc[high], num("pre_vtx_shift").loc[low]),
                   "n_high": int(num("pre_shift").loc[high].notna().sum()), "n_low": int(num("pre_shift").loc[low].notna().sum()),
                   "solar_share_high_2018": float(num("solar_share_y18").loc[high].median())}
res["jas_main"] = {"H1": sign(num("jas_shift").loc[high]), "median_shift_high": float(num("jas_shift").loc[high].median()),
                   "median_shift_low": float(num("jas_shift").loc[low].median()),
                   "median_vtx_shift_high": float(num("jas_vtx_shift").loc[high].median()),
                   "H4_vtx": mw(num("jas_vtx_shift").loc[high], num("jas_vtx_shift").loc[low])}

# 3. continuous peak time
vs = num("main_vtx_shift")
res["vertex"] = {"H1": sign(vs.loc[high]), "wilcoxon_p": wil(vs.loc[high]), "median_shift_high": float(vs.loc[high].median()),
                 "min_shift_high": float(vs.loc[high].min()), "max_shift_high": float(vs.loc[high].max()),
                 "median_shift_low": float(vs.loc[low].median()), "H4": mw(vs.loc[high], vs.loc[low]),
                 "median_early_high": float(num("main_vtx_early").loc[high].median()),
                 "median_late_high": float(num("main_vtx_late").loc[high].median())}
cs = num("main_circ_shift")
res["circular"] = {"H1": sign(cs.loc[high]), "median_shift_high": float(cs.loc[high].median()),
                   "median_shift_low": float(cs.loc[low].median()), "H4": mw(cs.loc[high], cs.loc[low])}

# 4. mechanical counterfactual
ob, mc, su = num("prof_obs_shift").loc[high], num("mech_shift").loc[high], num("swap_supply_shift").loc[high]
ok = ob.notna() & mc.notna()
res["mechanical"] = {"n": int(ok.sum()), "median_obs": float(ob[ok].median()), "median_mech": float(mc[ok].median()),
                     "median_swap_supply": float(su[ok].median()),
                     "within_half_hour": int(((ob - mc).abs()[ok] <= 0.5).sum()),
                     "median_abs_diff": float((ob - mc).abs()[ok].median()),
                     "median_obs_minus_mech": float((ob - mc)[ok].median()),
                     "spearman": float(stats.spearmanr(ob[ok], mc[ok]).statistic),
                     "obs_minus_mech_sign": sign((ob - mc)[ok], "two-sided"),
                     "within_half_hour_swap": int(((ob - su).abs()[ok] <= 0.5).sum()),
                     "median_kS": float(num("kS").loc[high].median())}

# 5. forecast-offset scan and H3 without data-quality BAs
scan = {}
for ba, g in G.items():
    for y, gy in g.groupby(g["date"].dt.year):
        if y < 2019:
            continue
        gy = gy.reindex(pd.date_range(gy.index.min(), gy.index.max(), freq="h"))
        a = {}
        for k in range(-3, 4):
            ape = 100 * (gy["forecast"].shift(k) - gy["demand"]).abs() / gy["demand"]
            a[k] = float(ape.median()) if ape.notna().sum() > 24 * 30 else np.nan
        if not np.isfinite(a[0]):
            continue
        best = min((k for k in a if np.isfinite(a[k])), key=lambda k: a[k])
        scan[f"{ba}_{y}"] = {"ba": ba, "year": int(y), "best": int(best), "ape0": a[0], "ape_best": a[best]}
S = pd.DataFrame(scan).T
off = S[(S["best"] != 0) & (S["ape_best"].astype(float) < 0.9 * S["ape0"].astype(float))]
res["forecast_offsets"] = {f"{b}": sorted(f"{int(r.year)}:{int(r.best):+d}" for r in off[off["ba"] == b].itertuples())
                           for b in sorted(off["ba"].unique())}
Hb = T.loc[high]
FX = pd.read_csv("out/h3_fixed_hours.csv", index_col=0)
fcast = ["CISO", "FPC", "PSCO"]
allq = fcast + ["AZPS", "EPE", "SRP"]
res["H3_excl"] = {"fcast_realised": sign(Hb.drop(index=fcast)["ape_diff_late"], "two-sided"),
                  "fcast_fixed": sign(FX.drop(index=fcast)["diff"], "two-sided"),
                  "all_realised": sign(Hb.drop(index=allq)["ape_diff_late"], "two-sided"),
                  "all_fixed": sign(FX.drop(index=allq)["diff"], "two-sided"),
                  "all_fixed_median_diff": float(FX.drop(index=allq)["diff"].median())}
P.to_csv("out/robustness3_ba.csv")
S.to_csv("out/forecast_offset_scan.csv")
json.dump(res, open("out/robustness3.json", "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
print(json.dumps(res, indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
