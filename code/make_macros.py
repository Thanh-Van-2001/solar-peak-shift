"""Every number in the paper. Reads out/results.json, out/ba_table.csv, out/gen_coverage.csv and
data/peaks_results.json (copied to out/peaks_primary.json); writes paper/macros.tex and out/macros.json.
Run from the repository root: python -I code/make_macros.py"""
import json

import numpy as np
import pandas as pd

R = json.load(open("out/results.json"))
T = pd.read_csv("out/ba_table.csv", index_col=0)
P = json.load(open("out/peaks_primary.json"))
H, S, RB, D = R["hypotheses"], R["secondary"], R["robustness"], R["descriptive"]
M = {}


def f(x, d=1):
    s = f"{x:.{d}f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def pv(p):
    return "<0.001" if p < 0.001 else "=" + (f"{p:.3f}" if p < 0.01 else f"{p:.2f}")


M["nPrimary"], M["nBas"] = str(len(P["primary"])), str(D["n_bas"])
M["nHigh"], M["nLow"] = str(D["n_high"]), str(D["n_low"])
drop = sorted(set(P["primary"]) - set(T.index))
M["nDropped"], M["dropped"] = str(len(drop)), ", ".join(drop)
for k, tag in (("H1", "One"), ("H2", "Two"), ("H3", "Three")):
    M[f"h{tag}Pos"], M[f"h{tag}N"], M[f"h{tag}P"], M[f"h{tag}Holm"] = str(H[k]["pos"]), str(H[k]["n"]), pv(H[k]["p"]), pv(H[k]["p_holm"])
M["hThreeNeg"] = str(H["H3"]["n"] - H["H3"]["pos"])
M["hFourP"], M["hFourHolm"] = pv(H["H4"]["p"]), pv(H["H4"]["p_holm"])
M["shiftHigh"], M["shiftLow"] = f(H["H4"]["median_shift_high"]), f(H["H4"]["median_shift_low"])
mh, ml = S["medians_high"], S["medians_low"]
for k, v in mh.items():
    M["high" + k.replace("_", "").replace("NL", "Nl").capitalize()] = f(v, 1 if "ape" in k else 1)
for k, v in ml.items():
    M["low" + k.replace("_", "").replace("NL", "Nl").capitalize()] = f(v, 1)
M["rampEarly"], M["rampLate"] = f(S["ramp_median_early"]), f(S["ramp_median_late"])
M["rampPos"], M["rampN"], M["rampP"] = str(S["ramp"]["pos"]), str(S["ramp"]["n"]), pv(S["ramp"]["p"])
M["sepEarly"], M["sepLate"] = f(100 * S["sep2_median_early"], 0), f(100 * S["sep2_median_late"], 0)
M["sepPos"], M["sepN"], M["sepP"] = str(S["sep2"]["pos"]), str(S["sep2"]["n"]), pv(S["sep2"]["p"])
a = RB["alt_periods"]
for k, tag in (("H1", "One"), ("H2", "Two"), ("H3", "Three")):
    M[f"alt{tag}Pos"], M[f"alt{tag}N"], M[f"alt{tag}P"] = str(a[k]["pos"]), str(a[k]["n"]), pv(a[k]["p"])
    t = RB["thr10"][k]
    M[f"ten{tag}Pos"], M[f"ten{tag}N"], M[f"ten{tag}P"] = str(t["pos"]), str(t["n"]), pv(t["p"])
x = RB["H3_excl_PJM_CISO"]
M["exclThreePos"], M["exclThreeN"], M["exclThreeP"] = str(x["pos"]), str(x["n"]), pv(x["p"])
Hg = T[T["group"] == "high"]
M["shareMin"], M["shareMax"] = f(100 * Hg["solar_share_2025"].min(), 0), f(100 * Hg["solar_share_2025"].max(), 0)
M["shareMinBa"], M["shareMaxBa"] = Hg["solar_share_2025"].idxmin(), Hg["solar_share_2025"].idxmax()
top = Hg["shift_NL"].idxmax()
M["maxShiftBa"], M["maxShift"] = top, f(Hg.loc[top, "shift_NL"], 0)
for b in ("CISO", "ERCO", "PACE"):
    if b in T.index:
        M[f"{b.lower()}NlEarly"], M[f"{b.lower()}NlLate"] = f(T.loc[b, "hNL_early"], 0), f(T.loc[b, "hNL_late"], 0)
        M[f"{b.lower()}RampEarly"], M[f"{b.lower()}RampLate"] = f(T.loc[b, "ramp_early"], 0), f(T.loc[b, "ramp_late"], 0)
lv = T[(T["apeD_late"] > 10)]
M["levelBas"] = " and ".join(sorted(lv.index))
M["nDaysMin"], M["nDaysMax"] = str(int(T[["n_early", "n_late"]].min().min())), str(int(T[["n_early", "n_late"]].max().max()))

def fh(x):
    return str(int(x)) if float(x).is_integer() else f"{x:.1f}"


for k in ("highHnlearly", "highHnllate", "highHdearly", "highHdlate", "lowHnlearly", "lowHnllate", "lowHdearly", "lowHdlate"):
    M[k] = fh(float(M[k]))
M["shiftHigh"], M["shiftLow"] = fh(H["H4"]["median_shift_high"]), fh(H["H4"]["median_shift_low"])
lvl = sorted(T[T["apeD_late"] > 10].index)
M["levelBas"] = ", ".join(lvl[:-1]) + " and " + lvl[-1] if len(lvl) > 1 else "".join(lvl)
rows = []
for b, r in T[T["group"] == "high"].sort_values("solar_share_2025", ascending=False).iterrows():
    mark = r"$^\ddagger$" if b in ("AZPS", "EPE", "SRP") else ""
    rows.append(f"{ {'ERCO': 'ERCOT'}.get(b, b)}{mark} & {100 * r['solar_share_2025']:.0f} & {fh(r['hNL_early'])}$\\to${fh(r['hNL_late'])} & "
                f"{fh(r['hD_early'])}$\\to${fh(r['hD_late'])} & {r['ramp_early']:.0f}$\\to${r['ramp_late']:.0f} & "
                f"{r['apeNL_late']:.1f} / {r['apeD_late']:.1f} \\\\")
open("paper/tab_bas.tex", "w", encoding="utf-8").write("\n".join(rows) + "\n")
PR = pd.read_csv("out/profile.csv")
PR["period"] = np.where(PR["year"].isin([2019, 2020]), "early", np.where(PR["year"].isin([2025, 2026]), "late", None))
PR = PR.dropna(subset=["period"])
ba_med = PR.groupby(["group", "ba", "period"])["ape"].median().unstack("period")
for g in ("high", "low"):
    x = ba_med.loc[g]
    M[f"err{g.capitalize()}Early"], M[f"err{g.capitalize()}Late"] = f(x["early"].median()), f(x["late"].median())
    M[f"err{g.capitalize()}Up"], M[f"err{g.capitalize()}N"] = str(int((x["late"] > x["early"]).sum())), str(int(x.dropna().shape[0]))
xh = ba_med.loc["high"].drop(index=[b for b in ("CISO",) if b in ba_med.loc["high"].index])
M["errHighUpNoCiso"], M["errHighNNoCiso"] = str(int((xh["late"] > xh["early"]).sum())), str(int(xh.dropna().shape[0]))
lowshift = T[(T["group"] == "low") & (T["shift_NL"] >= 2)]
M["lowShiftBas"] = ", ".join(sorted(lowshift.index))
cv = pd.read_csv("out/gen_coverage.csv", index_col=0)
M["misoWind"] = f(100 * cv.loc["MISO", "wind_share_2025"], 0) if "MISO" in cv.index else "--"

# ---- amendment 2 (exploratory checks after an internal review; code/robustness2.py) ----
R2 = json.load(open("out/robustness2.json"))
for k, tag in (("solar_only", "Sol"), ("wind_only", "Wnd"), ("solar_no_storage", "Nst"), ("y2019_vs_2025", "Yr"), ("main_noF", "NoF")):
    M[f"{tag}OnePos"], M[f"{tag}OneN"], M[f"{tag}OneP"] = str(R2[k]["H1"]["pos"]), str(R2[k]["H1"]["n"]), pv(R2[k]["H1"]["p"])
    M[f"{tag}TwoPos"], M[f"{tag}TwoN"], M[f"{tag}TwoP"] = str(R2[k]["H2"]["pos"]), str(R2[k]["H2"]["n"]), pv(R2[k]["H2"]["p"])
M["yrShift"] = fh(R2["y2019_vs_2025"]["median_shift"])
M["monthPos"], M["monthN"] = str(R2["month_stratified"]["pos"]), str(R2["month_stratified"]["n"])
M["nodstOnePos"], M["nodstOneN"] = str(R2["no_dst_excluded"]["H1"]["pos"]), str(R2["no_dst_excluded"]["H1"]["n"])
M["nodstTwoPos"], M["nodstTwoN"] = str(R2["no_dst_excluded"]["H2"]["pos"]), str(R2["no_dst_excluded"]["H2"]["n"])
M["meanShift"], M["meanShiftLo"], M["meanShiftHi"] = f(R2["mean_hour_median"]), f(R2["mean_hour_ci"][0]), f(R2["mean_hour_ci"][1])
M["meanPos"], M["meanN"] = str(R2["mean_hour"]["pos"]), str(R2["mean_hour"]["n"])
M["perBaMedianShift"], M["perBaMeanShift"] = fh(R2["median_shift_per_ba"]), f(R2["mean_shift_per_ba"])
M["lateTwentyEarly"], M["lateTwentyLate"] = f(100 * R2["late20"]["early"], 0), f(100 * R2["late20"]["late"], 0)
M["lateTwentyPos"], M["lateTwentyN"] = str(R2["late20"]["test"]["pos"]), str(R2["late20"]["test"]["n"])
M["rhoAll"], M["rhoAllP"], M["rhoLow"], M["rhoLowP"] = f(R2["spearman_all"]["rho"], 2), pv(R2["spearman_all"]["p"]), f(R2["spearman_low"]["rho"], 2), pv(R2["spearman_low"]["p"])
h3 = R2["H3_fixed_hours"]
M["fixPos"], M["fixN"], M["fixP"], M["fixDiff"], M["fixW"] = str(h3["sign"]["pos"]), str(h3["sign"]["n"]), pv(h3["sign"]["p"]), f(h3["median_diff"], 2), pv(h3["wilcoxon_p"])
sw = R2["swap"]
M["supPos"], M["supN"], M["supP"], M["supMed"] = str(sw["supply_effect"]["pos"]), str(sw["supply_effect"]["n"]), pv(sw["supply_effect"]["p"]), fh(sw["median_supply_effect"])
M["demPos"], M["demN"], M["demP"], M["demMed"] = str(sw["demand_effect"]["pos"]), str(sw["demand_effect"]["n"]), pv(sw["demand_effect"]["p"]), fh(sw["median_demand_effect"])
ts = R2["solar_timestamps"]
bad = sorted(b for b, yy in ts.items() if yy and (max(v["night_share"] for v in yy.values()) > 0.05
                                                  or max(v["hmax"] for v in yy.values()) - min(v["hmax"] for v in yy.values()) >= 3))
M["tsBad"] = ", ".join(bad[:-1]) + " and " + bad[-1] if len(bad) > 1 else "".join(bad)
M["tsNightMax"] = f(100 * R2["solar_night_share_max"])
Hx = T[(T["group"] == "high")].drop(index=[b for b in bad if b in T.index])
M["tsOnePos"], M["tsOneN"] = str(int((Hx["shift_NL"] > 0).sum())), str(int((Hx["shift_NL"] != 0).sum()))
M["tsTwoPos"], M["tsTwoN"] = str(int((Hx["gap_change"] > 0).sum())), str(int((Hx["gap_change"] != 0).sum()))
Hg2 = T[T["group"] == "high"]
M["rampRatio"] = f((Hg2["ramp_late"] / Hg2["ramp_early"]).median(), 1)
M["rampFell"] = " and ".join(sorted(Hg2.index[Hg2["ramp_late"] < Hg2["ramp_early"]]))
M["sepMajLate"], M["sepMajEarly"] = str(int((Hg2["sep2_late"] > 0.5).sum())), str(int((Hg2["sep2_early"] > 0.5).sum()))
M["hFourU"] = f(H["H4"]["U"], 1)

# ---- amendment 3 (exploratory, after an independent review; code/robustness3.py) ----
R3 = json.load(open("out/robustness3.json"))
P3 = pd.read_csv("out/robustness3_ba.csv", index_col=0)
SC3 = pd.read_csv("out/forecast_offset_scan.csv", index_col=0)
assert R3["check_max_abs_diff_vs_main"] == 0.0 and R3["utc_offset_changes"] == []
movers = ["MISO", "PJM", "SC"]
assert sorted(T.index[(T["group"] == "low") & (T["shift_NL"] >= 2)]) == movers
for b in movers:
    t, r = b.lower(), P3.loc[b]
    assert r["main_hD_shift"] == 0 and r["sol_shift"] == r["main_shift"]
    M[f"{t}SolL"], M[f"{t}Gap"], M[f"{t}Drop"] = f(100 * r["solar_share_l"]), f(r["d_gap_pct"]), f(r["s_drop_pct"])
    M[f"{t}SolShift"], M[f"{t}WndShift"] = fh(r["sol_shift"]), fh(r["wnd_shift"])
    M[f"{t}HdPk"], M[f"{t}NlPk"] = str(int(r["hD_prof_e"])), str(int(r["hNL_late_used"]))
    M[f"{t}Obs"], M[f"{t}Mech"] = f(r["prof_obs_shift"]), f(r["mech_shift"])
assert P3.loc[movers, "hD_prof_e"].nunique() == 1  # the text says "in all three"
# the text: solar drop "more than the gap in MISO and PJM, about as much in SC"; AZPS "has no early wind"
assert all(P3.loc[b, "s_drop_pct"] > P3.loc[b, "d_gap_pct"] for b in ("MISO", "PJM"))
assert abs(P3.loc["SC", "s_drop_pct"] - P3.loc["SC", "d_gap_pct"]) < 0.5 and P3.loc["AZPS", "wind_share_e"] == 0
assert P3.loc["SC", "solar_night_2025"] < 0.001  # the text says "almost none in 2025"
M["moverSolE"] = f(100 * P3.loc[movers, "solar_share_e"].max())
M["scHmaxEarly"], M["scHmaxLate"] = fh(P3.loc["SC", "solar_hmax_2019"]), fh(P3.loc["SC", "solar_hmax_2025"])
M["scNight"] = f(100 * P3.loc["SC", ["solar_night_2018", "solar_night_2019", "solar_night_2020"]].max(), 0)
M["scSolE"] = f(100 * P3.loc["SC", "solar_share_e"], 2)
assert P3.loc["PJM", [f"solar_hmax_{y}" for y in range(2019, 2025)]].nunique() == 1  # "moved ... in 2025"
assert P3.loc["PJM", "solar_hmax_2025"] == P3.loc["PJM", "solar_hmax_2026"] != P3.loc["PJM", "solar_hmax_2024"]
M["pjmHmaxEarly"], M["pjmHmaxLate"] =fh(P3.loc["PJM", "solar_hmax_2019"]), fh(P3.loc["PJM", "solar_hmax_2025"])
pt = R3["pretrend"]
M["preOnePos"], M["preOneN"], M["preOneP"] = str(pt["H1"]["pos"]), str(pt["H1"]["n"]), pv(pt["H1"]["p"])
M["preVtxHigh"], M["preVtxLow"] = f(pt["median_vtx_shift_high"], 2), f(pt["median_vtx_shift_low"], 2)
M["preMwVtxP"], M["preMwP"] = pv(pt["H4_vtx"]["p"]), pv(pt["H4"]["p"])
M["preNHigh"], M["preNLow"] = str(pt["n_high"]), str(pt["n_low"])
M["preSolHigh"] = f(100 * pt["solar_share_high_2018"])
vx = R3["vertex"]
M["vtxPos"], M["vtxN"], M["vtxP"], M["vtxW"] = str(vx["H1"]["pos"]), str(vx["H1"]["n"]), pv(vx["H1"]["p"]), pv(vx["wilcoxon_p"])
M["vtxMed"], M["vtxMin"], M["vtxMax"], M["vtxLow"] = f(vx["median_shift_high"]), f(vx["min_shift_high"]), f(vx["max_shift_high"]), f(vx["median_shift_low"])
M["vtxMwP"], M["vtxEarly"], M["vtxLate"] = pv(vx["H4"]["p"]), f(vx["median_early_high"]), f(vx["median_late_high"])
M["vtxPerYear"] = f(vx["median_shift_high"] / 6, 2)
cr = R3["circular"]
M["circMed"], M["circLow"], M["circMwP"] = f(cr["median_shift_high"]), f(cr["median_shift_low"]), pv(cr["H4"]["p"])
mc = R3["mechanical"]
M["mechN"], M["mechObs"], M["mechPred"], M["mechSwap"] = str(mc["n"]), f(mc["median_obs"]), f(mc["median_mech"]), f(mc["median_swap_supply"])
M["mechWithin"], M["mechAbs"], M["mechRho"], M["mechKs"] = str(mc["within_half_hour"]), f(mc["median_abs_diff"], 2), f(mc["spearman"], 2), f(mc["median_kS"])
Hm3 = P3.loc[T.index[T["group"] == "high"]]
out3 = sorted(Hm3.index[(Hm3["prof_obs_shift"] - Hm3["mech_shift"]).abs() > 0.5])
M["mechOut"] = " and ".join(out3)
M["mechMissing"] = " and ".join(sorted(Hm3.index[Hm3["mech_shift"].isna()]))
e3 = R3["H3_excl"]
for k, tag in (("fcast_realised", "Fc"), ("fcast_fixed", "FcFix"), ("all_realised", "All"), ("all_fixed", "AllFix")):
    M[f"hThree{tag}Pos"], M[f"hThree{tag}N"], M[f"hThree{tag}P"] = str(e3[k]["pos"]), str(e3[k]["n"]), pv(e3[k]["p"])
sc = SC3.set_index(["ba", "year"])
M["pjmFcA"] = f(sc.loc["PJM", "ape0"].median())
M["pjmFcB"] = f(sc.loc["PJM", "ape_best"].median())
assert (sc.loc["PJM", "best"] == 1).all() and (sc.loc[("CISO", slice(2022, 2025)), "best"] == 1).all()
M["cisoFcA"] = f(sc.loc[("CISO", slice(2022, 2025)), "ape0"].median())
M["cisoFcB"] = f(sc.loc[("CISO", slice(2022, 2025)), "ape_best"].median())
M["azpsFcE"] = f(sc.loc[("AZPS", slice(2019, 2024)), "ape0"].median())
M["azpsFcL"] = f(sc.loc[("AZPS", slice(2025, 2026)), "ape0"].median())
M["scFcE"] = f(sc.loc[("SC", slice(2019, 2020)), "ape0"].median())
for k in [k for k, v in M.items() if (k.endswith("P") or k.endswith("Holm")) and v[:1] in "=<"]:
    M[k + "T"] = M[k][1:] if M[k][0] == "=" else "<" + M[k][1:]
with open("paper/macros.tex", "w", encoding="utf-8") as fh:
    fh.write("% generated by code/make_macros.py -- do not edit\n\\makeatletter\n")
    for k, v in sorted(M.items()):
        fh.write(f"\\expandafter\\def\\csname res@{k}\\endcsname{{{v}}}\n")
    fh.write("\\makeatother\n\\newcommand{\\res}[1]{\\ifcsname res@#1\\endcsname\\csname res@#1\\endcsname\\else\\textbf{??#1??}\\fi}\n")
json.dump(M, open("out/macros.json", "w"), indent=0)
print(len(M), "macros")
print(M)
