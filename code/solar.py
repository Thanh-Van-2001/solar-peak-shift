"""Utility solar and the timing of the net-load peak (PLAN.md). Writes out/results.json, out/ba_table.csv,
out/profile.csv, out/days.parquet. Run from the repository root:
    python -I code/solar.py            full run
    python -I code/solar.py --check    pipeline check (CISO, summers 2019 and 2025) -> out_check/
"""
import json
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

CHECK = "--check" in sys.argv
OUT = "out_check" if CHECK else "out"
os.makedirs(OUT, exist_ok=True)
SUMMER = [6, 7, 8, 9]

prim = json.load(open("data/peaks_results.json"))["log"]["primary"]
cov = pd.read_csv("out/gen_coverage.csv", index_col=0)
d = pd.read_parquet("data/eia930_gen.parquet")
d = d[d["ba"].isin(prim) & (d["date"] >= "2019-01-01") & (d["date"] <= "2026-09-30")]
if CHECK:
    d = d[(d["ba"] == "CISO") & d["date"].dt.year.isin([2019, 2025])]
bas = sorted(d["ba"].unique())


def group(ba, thr=0.05):
    s = cov.loc[ba, "solar_share_2025"] if ba in cov.index else np.nan
    return "high" if (np.isfinite(s) and s >= thr) else "low"


def prep(g, ba):
    g = g.set_index("utc_end").sort_index()
    g = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    ref = g["demand"].where(g["demand"] > 0).rolling(168, center=True, min_periods=24).median()
    for c in ("demand", "forecast"):
        x = g[c]
        g[c] = x.mask((x <= 0) | (x > 2.0 * ref) | (x < 0.3 * ref))
    g["solar"] = g["solar"].clip(lower=0)
    if cov.loc[ba, "wind_present"] < 0.01:
        g["wind"] = 0.0
    g["wind"] = g["wind"].clip(lower=0)
    g["nl"] = g["demand"] - g["solar"].fillna(np.nan) - g["wind"]
    return g.dropna(subset=["date"])


def days(g):
    g = g[g["date"].dt.month.isin(SUMMER)].copy()
    g["ok"] = g[["demand", "forecast", "nl"]].notna().all(axis=1)
    grp = g.groupby("date")
    n, nok = grp.size(), grp["ok"].sum()
    good = n.index[(n >= 24) & (nok == n)]
    g = g[g["date"].isin(good)]
    grp = g.groupby("date")
    iD, iN = grp["demand"].idxmax(), grp["nl"].idxmax()
    out = pd.DataFrame({"hD": g.loc[iD, "hour"].values, "hNL": g.loc[iN, "hour"].values,
                        "apeD": (100 * (g.loc[iD, "forecast"] - g.loc[iD, "demand"]).abs() / g.loc[iD, "demand"]).values,
                        "apeNL": (100 * (g.loc[iN, "forecast"] - g.loc[iN, "demand"]).abs() / g.loc[iN, "demand"]).values,
                        "nlpeak": g.loc[iN, "nl"].values}, index=iD.index)
    # evening ramp: NL at the peak minus NL three rows (hours) earlier on the hourly grid
    pos = g.index.get_indexer(iN.values)
    nl = g["nl"].values
    prev = np.where(pos >= 3, nl[np.maximum(pos - 3, 0)], np.nan)
    same_day = np.where(pos >= 3, g["date"].values[np.maximum(pos - 3, 0)] == g.loc[iN, "date"].values, False)
    out["ramp"] = np.where(same_day, 100 * (nl[pos] - prev) / nl[pos], np.nan)
    prof = g.assign(ape=100 * (g["forecast"] - g["demand"]).abs() / g["demand"]).groupby([g["date"].dt.year, "hour"])["ape"].median()
    return out, prof


def sign(x, alt):
    x = np.asarray([v for v in x if np.isfinite(v) and v != 0])
    k = int((x > 0).sum())
    if len(x) == 0:
        return {"pos": 0, "n": 0, "p": float("nan")}
    return {"pos": k, "n": int(len(x)), "p": float(stats.binomtest(k, len(x), 0.5, alternative=alt).pvalue)}


def summarise(D, early, late):
    e, l = D[D.index.year.isin(early)], D[D.index.year.isin(late)]
    if len(e) < 30 or len(l) < 30:
        return None
    r = {"n_early": len(e), "n_late": len(l),
         "hNL_early": float(e["hNL"].median()), "hNL_late": float(l["hNL"].median()),
         "hD_early": float(e["hD"].median()), "hD_late": float(l["hD"].median()),
         "apeNL_late": float(l["apeNL"].median()), "apeD_late": float(l["apeD"].median()),
         "apeNL_early": float(e["apeNL"].median()), "apeD_early": float(e["apeD"].median()),
         "ramp_early": float(e["ramp"].median()), "ramp_late": float(l["ramp"].median()),
         "sep2_early": float((e["hNL"] >= e["hD"] + 2).mean()), "sep2_late": float((l["hNL"] >= l["hD"] + 2).mean())}
    r["shift_NL"] = r["hNL_late"] - r["hNL_early"]
    r["gap_change"] = (r["hNL_late"] - r["hD_late"]) - (r["hNL_early"] - r["hD_early"])
    r["ape_diff_late"] = r["apeNL_late"] - r["apeD_late"]
    return r


rows, rows_alt, profs, alld = [], [], [], {}
E1, L1 = [2019, 2020], [2025, 2026]
E2, L2 = [2019, 2020, 2021], [2024, 2025, 2026]
for ba in bas:
    g = prep(d[d["ba"] == ba], ba)
    D, prof = days(g)
    alld[ba] = D
    r = summarise(D, E1, L1)
    if r:
        r.update({"ba": ba, "group": group(ba), "group10": group(ba, 0.10),
                  "solar_share_2025": float(cov.loc[ba, "solar_share_2025"]) if ba in cov.index else np.nan})
        rows.append(r)
    r2 = summarise(D, E2, L2)
    if r2:
        r2.update({"ba": ba, "group": group(ba)})
        rows_alt.append(r2)
    p = prof.rename("ape").reset_index().rename(columns={"date": "year"})
    p["ba"], p["group"] = ba, group(ba)
    profs.append(p)

T = pd.DataFrame(rows).set_index("ba")
T.to_csv(f"{OUT}/ba_table.csv")
A = pd.DataFrame(rows_alt).set_index("ba") if rows_alt else pd.DataFrame()
pd.concat(profs).to_csv(f"{OUT}/profile.csv", index=False)
pd.concat(alld, names=["ba", "date"]).to_parquet(f"{OUT}/days.parquet")
H = T[T["group"] == "high"]
L = T[T["group"] == "low"]
res = {"H1": sign(H["shift_NL"], "greater"), "H2": sign(H["gap_change"], "greater"),
       "H3": sign(H["ape_diff_late"], "two-sided")}
if len(H) and len(L):
    mw = stats.mannwhitneyu(H["shift_NL"], L["shift_NL"], alternative="greater")
    res["H4"] = {"p": float(mw.pvalue), "U": float(mw.statistic), "n_high": len(H), "n_low": len(L),
                 "median_shift_high": float(H["shift_NL"].median()), "median_shift_low": float(L["shift_NL"].median())}
order = sorted([k for k in res if np.isfinite(res[k]["p"])], key=lambda k: res[k]["p"])
prev = 0.0
for i, k in enumerate(order):
    prev = min(1.0, max(prev, (len(order) - i) * res[k]["p"]))
    res[k]["p_holm"] = prev
for k in ("H1", "H2"):
    if k in res and "p_holm" in res[k]:
        res[k]["supported"] = bool(res[k]["p_holm"] < 0.05 and res[k]["pos"] > res[k]["n"] / 2)
if "p_holm" in res.get("H3", {}):
    res["H3"]["supported"] = bool(res["H3"]["p_holm"] < 0.05)
if "p_holm" in res.get("H4", {}):
    res["H4"]["supported"] = bool(res["H4"]["p_holm"] < 0.05)
sec = {"ramp": sign(H["ramp_late"] - H["ramp_early"], "greater"),
       "ramp_median_early": float(H["ramp_early"].median()) if len(H) else np.nan,
       "ramp_median_late": float(H["ramp_late"].median()) if len(H) else np.nan,
       "sep2": sign(H["sep2_late"] - H["sep2_early"], "greater"),
       "sep2_median_early": float(H["sep2_early"].median()) if len(H) else np.nan,
       "sep2_median_late": float(H["sep2_late"].median()) if len(H) else np.nan,
       "medians_high": H[["hNL_early", "hNL_late", "hD_early", "hD_late", "apeNL_late", "apeD_late"]].median().to_dict(),
       "medians_low": L[["hNL_early", "hNL_late", "hD_early", "hD_late", "apeNL_late", "apeD_late"]].median().to_dict()}
rob = {}
if len(A):
    HA = A[A["group"] == "high"]
    rob["alt_periods"] = {"H1": sign(HA["shift_NL"], "greater"), "H2": sign(HA["gap_change"], "greater"),
                          "H3": sign(HA["ape_diff_late"], "two-sided")}
HX = H.drop(index=[b for b in ("PJM", "CISO") if b in H.index])
rob["H3_excl_PJM_CISO"] = sign(HX["ape_diff_late"], "two-sided")
H10 = T[T["group10"] == "high"]
rob["thr10"] = {"H1": sign(H10["shift_NL"], "greater"), "H2": sign(H10["gap_change"], "greater"),
                "H3": sign(H10["ape_diff_late"], "two-sided"), "n": len(H10)}
desc = {"n_bas": len(T), "n_high": len(H), "n_low": len(L), "high": list(H.index), "low": list(L.index)}
json.dump({"hypotheses": res, "secondary": sec, "robustness": rob, "descriptive": desc},
          open(f"{OUT}/results.json", "w"), indent=1, default=float)
print(json.dumps({"hypotheses": res, "descriptive": desc}, indent=1, default=float))
