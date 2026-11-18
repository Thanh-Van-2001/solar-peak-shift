"""Pre-specified secondary analysis 5: case profiles. For CISO, ERCO and the high-solar BA with the largest
2025 solar share among BAs above 5,000 MW median demand (other than CISO and ERCO), the median by hour of
day of demand and net load, each divided by its own daily maximum, over summer days of the early and late
periods. Writes out/case_profiles.csv. Run from the repository root: python -I code/case_profiles.py
"""
import json
import sys

import numpy as np
import pandas as pd

T = pd.read_csv("out/ba_table.csv", index_col=0)
peaks = json.load(open("data/peaks_results.json"))["log"]["median_mw"]
big = [b for b in T.index if T.loc[b, "group"] == "high" and peaks.get(b, 0) > 5000 and b not in ("CISO", "ERCO")]
third = max(big, key=lambda b: T.loc[b, "solar_share_2025"])
cov = pd.read_csv("out/gen_coverage.csv", index_col=0)
d = pd.read_parquet("data/eia930_gen.parquet")
rows = []
for ba in ("CISO", "ERCO", third):
    g = d[(d["ba"] == ba) & d["date"].dt.year.isin([2019, 2020, 2025, 2026]) & d["date"].dt.month.isin([6, 7, 8, 9])].copy()
    g = g.set_index("utc_end").sort_index()
    full = g.reindex(pd.date_range(g.index.min(), g.index.max(), freq="h"))
    ref = full["demand"].where(full["demand"] > 0).rolling(168, center=True, min_periods=24).median().reindex(g.index)
    g["demand"] = g["demand"].mask((g["demand"] <= 0) | (g["demand"] > 2 * ref) | (g["demand"] < 0.3 * ref))
    g["wind"] = 0.0 if cov.loc[ba, "wind_present"] < 0.01 else g["wind"].clip(lower=0)
    g["nl"] = g["demand"] - g["solar"].clip(lower=0) - g["wind"]
    g = g.dropna(subset=["demand", "nl"])
    g["d_n"] = g["demand"] / g.groupby("date")["demand"].transform("max")
    g["nl_n"] = g["nl"] / g.groupby("date")["nl"].transform("max")
    g["period"] = np.where(g["date"].dt.year <= 2020, "early", "late")
    p = g.groupby(["period", "hour"])[["d_n", "nl_n"]].median().reset_index()
    p["ba"] = ba
    rows.append(p)
pd.concat(rows).to_csv("out/case_profiles.csv", index=False)
print("third case:", third)
