# Utility solar is moving the net-load peak

Code, analysis plan and results for the paper "Utility Solar Is Moving the Net-Load Peak: Evidence from 42 U.S. Balancing Authorities, 2019-2026".

- `PLAN.md`: the analysis plan, committed before any peak hour was computed, with Amendment 1 (zero rule for unreported minor sources), Amendment 2 (exploratory checks after an internal review) and Amendment 3 (exploratory checks after an independent review, logged before they were run).
- `code/download_eia930.sh`: downloads the EIA-930 six-month BALANCE files and writes SHA-256 hashes.
- `code/extract_gen.py`: extracts demand, forecast, solar (with and without integrated storage) and wind for every BA; `out/gen_coverage.csv` is the availability table used to define the sample.
- `code/solar.py`: the pre-specified analysis (`--check` runs the pipeline check). `out/results.json`, `out/ba_table.csv`, `out/profile.csv`; first run in `out/v1/`.
- `code/case_profiles.py`, `code/robustness2.py`: case profiles and the exploratory checks of Amendment 2.
- `code/robustness3.py`: Amendment 3 (low-solar BAs that moved, 2018-2019 pre-trends, continuous peak time, mechanical counterfactual, forecast-offset scan). `out/robustness3.json`, `out/robustness3_ba.csv`, `out/forecast_offset_scan.csv`.
- `code/make_macros.py`, `code/make_figures.py`: every number, table and figure in `paper/`.

The primary sample (43 BAs) comes from the companion repository ba-peak-forecasts (`out/peaks_primary.json`).
Python 3.11 with pandas 2.2.3, numpy 1.26.4, scipy 1.14.1, pyarrow 17.0.0, matplotlib 3.9.2.
