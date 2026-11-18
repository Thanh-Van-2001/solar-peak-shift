"""Extract demand, forecast, utility solar and wind generation for every BA from the EIA-930 BALANCE files.

Solar = Net Generation from Solar without + with Integrated Battery Storage; wind likewise
(older files have a single Solar / Wind column; whichever exist are summed, all-missing stays missing).
Writes data/eia930_gen.parquet and out/gen_coverage.csv (share of hours with solar/wind present and
2025 energy shares; data availability only). Run: python -I extract_gen.py <raw_dir> <repo_root>
"""
import glob
import os
import sys

import pandas as pd

RAW, ROOT = sys.argv[1], sys.argv[2]
parts = []
for f in sorted(glob.glob(os.path.join(RAW, "EIA930_BALANCE_*.csv"))):
    head = pd.read_csv(f, nrows=0).columns
    sol = [c for c in head if c.startswith("Net Generation (MW) from Solar") and "Imputed" not in c and "Adjusted" not in c]
    wnd = [c for c in head if c.startswith("Net Generation (MW) from Wind") and "Imputed" not in c and "Adjusted" not in c]
    use = ["Balancing Authority", "Data Date", "Hour Number", "UTC Time at End of Hour", "Demand (MW)", "Demand Forecast (MW)"] + sol + wnd
    df = pd.read_csv(f, usecols=use, dtype=str, low_memory=False)
    num = lambda c: pd.to_numeric(df[c].str.replace(",", "", regex=False), errors="coerce")
    out = pd.DataFrame({"ba": df["Balancing Authority"], "date": df["Data Date"], "hour": pd.to_numeric(df["Hour Number"], errors="coerce"),
                        "utc_end": df["UTC Time at End of Hour"], "demand": num("Demand (MW)"), "forecast": num("Demand Forecast (MW)")})
    out["solar"] = pd.concat([num(c) for c in sol], axis=1).sum(axis=1, min_count=1) if sol else float("nan")
    out["wind"] = pd.concat([num(c) for c in wnd], axis=1).sum(axis=1, min_count=1) if wnd else float("nan")
    parts.append(out)
d = pd.concat(parts, ignore_index=True)
d["date"] = pd.to_datetime(d["date"], format="%m/%d/%Y", errors="coerce")
d["utc_end"] = pd.to_datetime(d["utc_end"], format="%m/%d/%Y %I:%M:%S %p", errors="coerce")
d = d.dropna(subset=["utc_end"]).drop_duplicates(["ba", "utc_end"], keep="last").sort_values(["ba", "utc_end"])
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
d.to_parquet(os.path.join(ROOT, "data", "eia930_gen.parquet"), index=False)
y = d[d["date"].dt.year == 2025]
cov = d.groupby("ba").agg(solar_present=("solar", lambda x: x.notna().mean()), wind_present=("wind", lambda x: x.notna().mean()))
g = y.groupby("ba")[["demand", "solar", "wind"]].sum(min_count=1)
cov["solar_share_2025"] = (g["solar"].clip(lower=0) / g["demand"]).round(4)
cov["wind_share_2025"] = (g["wind"].clip(lower=0) / g["demand"]).round(4)
first = d[d["solar"].notna()].groupby("ba")["date"].min().dt.date
cov["solar_first"] = first
cov.to_csv(os.path.join(ROOT, "out", "gen_coverage.csv"))
print(cov.sort_values("solar_share_2025", ascending=False).head(30).to_string())
