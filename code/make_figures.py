"""Figures. Reads out/ba_table.csv, out/case_profiles.csv, out/profile.csv; writes paper/fig_shift.pdf,
paper/fig_cases.pdf, paper/fig_error.pdf. Run from the repository root: python -I code/make_figures.py"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams.update({"font.size": 7.5, "font.family": "serif", "axes.linewidth": 0.6, "axes.edgecolor": "#555555",
                     "xtick.color": "#333333", "ytick.color": "#333333", "axes.labelcolor": "#222222",
                     "legend.frameon": False, "pdf.fonttype": 42})
BLUE, ORANGE, GRAY, GRID = "#0072B2", "#D55E00", "#888888", "#dddddd"
T = pd.read_csv("out/ba_table.csv", index_col=0)
rng = np.random.default_rng(1)

# Fig 1: shift of the median net-load peak hour (and demand peak hour) against 2025 solar share
fig, ax = plt.subplots(figsize=(3.45, 2.5))
x = 100 * T["solar_share_2025"].fillna(0)
jit = rng.uniform(-0.12, 0.12, len(T))
hi = T["group"] == "high"
ax.scatter(x[hi], T.loc[hi, "shift_NL"] + jit[hi.values], s=18, color=BLUE, edgecolor="white", lw=0.5, zorder=3,
           label="net-load peak, solar share $\\geq$ 5%")
ax.scatter(x[~hi], T.loc[~hi, "shift_NL"] + jit[~hi.values], s=18, color=GRAY, edgecolor="white", lw=0.5, zorder=3,
           label="net-load peak, solar share < 5%")
ax.scatter(x, T["hD_late"] - T["hD_early"] + jit, s=14, facecolor="none", edgecolor=ORANGE, lw=0.8, zorder=2,
           label="demand peak, all BAs")
ax.axvline(5, color="#bbbbbb", lw=0.7, ls="--")
ax.axhline(0, color="#444444", lw=0.6)
for b in ("ERCO", "PNM", "CISO", "FPL"):
    if b in T.index:
        ax.annotate(b, (x[b], T.loc[b, "shift_NL"]), xytext=(4, 3), textcoords="offset points", fontsize=6)
ax.set_xlabel("Utility solar share of 2025 demand (%)")
ax.set_ylabel("Shift of median peak hour (h)")
ax.grid(color=GRID, lw=0.5)
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), fontsize=6, handletextpad=0.2, ncol=2, columnspacing=0.8)
fig.tight_layout(pad=0.3)
fig.savefig("paper/fig_shift.pdf")

# Fig 2: case profiles
C = pd.read_csv("out/case_profiles.csv")
cases = list(dict.fromkeys(C["ba"]))
fig, axs = plt.subplots(1, len(cases), figsize=(7.0, 1.75), sharey=True)
for ax, b in zip(axs, cases):
    for per, ls in (("early", "--"), ("late", "-")):
        s = C[(C["ba"] == b) & (C["period"] == per)].sort_values("hour")
        yrs = "2019-20" if per == "early" else "2025-26"
        ax.plot(s["hour"], s["d_n"], ls=ls, color=GRAY, lw=1.2, label=f"demand {yrs}")
        ax.plot(s["hour"], s["nl_n"], ls=ls, color=BLUE, lw=1.6, label=f"net load {yrs}")
    ax.set_title(b, fontsize=7.5)
    ax.set_xticks([1, 6, 12, 18, 24])
    ax.set_xlabel("Hour ending (local)")
    ax.grid(color=GRID, lw=0.5)
axs[0].set_ylabel("Share of daily maximum")
axs[-1].legend(loc="lower right", fontsize=5.8, handlelength=2.2)
fig.tight_layout(pad=0.3, w_pad=0.6)
fig.savefig("paper/fig_cases.pdf")

# Fig 3: demand forecast error by hour of day, high- and low-solar groups, early vs late
P = pd.read_csv("out/profile.csv")
P["period"] = np.where(P["year"].isin([2019, 2020]), "early", np.where(P["year"].isin([2025, 2026]), "late", None))
P = P.dropna(subset=["period"])
P["hour"] = P["hour"].clip(upper=24)
grp = P.groupby(["group", "ba", "period", "hour"])["ape"].median().groupby(["group", "period", "hour"]).median().reset_index()
fig, ax = plt.subplots(figsize=(3.45, 2.0))
for g, col in (("high", BLUE), ("low", GRAY)):
    for per, ls in (("early", "--"), ("late", "-")):
        s = grp[(grp["group"] == g) & (grp["period"] == per)].sort_values("hour")
        ax.plot(s["hour"], s["ape"], ls=ls, color=col, lw=1.4 if g == "high" else 1.0,
                label=f"{'solar $\\geq$ 5%' if g == 'high' else 'solar < 5%'}, {'2019-20' if per == 'early' else '2025-26'}")
ax.set_xticks([1, 6, 12, 18, 24])
ax.set_xlabel("Hour ending (local)")
ax.set_ylabel("Median abs. error (%)")
ax.grid(color=GRID, lw=0.5)
ax.set_ylim(1.5, 6.3)
ax.legend(fontsize=5.8, loc="upper center", ncol=2, handlelength=2, columnspacing=0.8)
fig.tight_layout(pad=0.3)
fig.savefig("paper/fig_error.pdf")
print("ok")
