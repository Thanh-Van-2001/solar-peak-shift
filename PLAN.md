# Analysis plan: utility solar, the timing of the net-load peak, and operators' day-ahead forecasts

Status: fixed before any peak hour, ramp or forecast error was computed for this study. Changes
after this commit are logged as amendments at the end, with the reason and what they change.

Target venue: IEEE IESES 2027 (Industrial Electronics for Sustainable Energy Systems), IEEE
two-column format, at most 6 pages; alternative IEEE ICPS 2027.

## What was looked at before this plan

- The EIA-930 BALANCE files (November 2026 vintage) and, for this study, an extract of demand,
  day-ahead demand forecast and utility-scale solar and wind generation for every BA.
- Data availability only: the share of hours with solar and wind values per BA (generation by
  fuel starts in July 2018) and each BA's 2025 energy share of solar and wind
  (out/gen_coverage.csv).
- The author's other EIA-930 studies (peak-day bias, recording errors, coincident peaks)
  computed demand forecast errors, but never by hour of day and never with solar or net load.
  One finding carries over as a known data issue: PJM's forecast is offset by one hour from
  February 2019, CISO's in July 2022 to November 2025.

## Question

Utility solar pushes the peak of net load (demand minus solar and wind) into the evening.
Across U.S. BAs, how far has the summer net-load peak moved between 2019-2020 and 2025-2026,
has it separated from the demand peak, and how accurate is the operators' published demand
forecast at the hour that now matters for scarcity?

## Data and sample

- Hourly demand D, demand forecast F, solar S (with and without integrated storage summed) and
  wind W from EIA-930, local "Data Date" and hour number (prevailing local time).
- Screening as in the author's other studies: values of D or F that are <= 0 or outside
  [0.3, 2] x the centred 168-hour median of demand are set to missing; S and W below 0 are set
  to 0. For a BA whose wind column is present in fewer than 1% of hours, W = 0.
- Net load NL = D - S - W.
- Sample: the 43 BAs of the primary sample of ba-peak-forecasts (median demand >= 500 MW, both
  D and F present in >= 80% of hours in >= 8 of 11 years). High-solar group: the BAs in it whose
  2025 solar energy share is at least 5% (19 BAs expected from the availability table).
  Low-solar group: the rest.
- Periods: early = June to September of 2019 and 2020; late = June to September of 2025 and 2026.
- A day enters the analysis if all its hours have D, F and NL.

## Day-level quantities

- h_D: hour of the daily maximum of D; h_NL: hour of the daily maximum of NL.
- Evening ramp: NL at h_NL minus NL three hours earlier, in percent of NL at h_NL.
- Absolute percentage forecast error of demand at a given hour: 100 |F - D| / D.

## Hypotheses (unit = BA)

- **H1.** In the high-solar group, the median h_NL over late-period days is later than over
  early-period days in a majority of BAs. One-sided sign test; ties dropped.
- **H2.** In the high-solar group, (median h_NL - median h_D) is larger in the late period
  than in the early period in a majority of BAs. One-sided sign test.
- **H3.** In the high-solar group, in the late period, the median absolute percentage error of
  the demand forecast at h_NL differs from that at h_D. Two-sided sign test.
- **H4.** The early-to-late shift in median h_NL is larger in the high-solar group than in the
  low-solar group. One-sided Mann-Whitney test.

Holm over the four p-values at family alpha 0.05.

## Pre-specified secondary analyses

1. Evening ramp, early vs late, high-solar group (sign test, medians).
2. Demand forecast error profile by hour of day, early vs late, for each group.
3. Share of days on which h_NL is at least two hours after h_D, early vs late.
4. Robustness: periods 2019-2021 vs 2024-2026 (2026 to September); demand forecast errors with
   PJM and CISO excluded (known timestamp offsets); solar share threshold 10% instead of 5%.
5. Case figures for CISO, ERCO and one other high-solar BA chosen by the largest solar share
   among BAs above 5,000 MW median demand.

## Outputs

out/results.json (every number in the paper through generated macros), out/ba_table.csv,
figures. A pipeline check (one BA, 2019 and 2025) runs before the full run.

## Amendment 1 (18 November 2026, after the first full run)

The plan set wind to zero for a BA whose wind column is almost always empty, but had no such rule for
solar. Five BAs of the primary sample (AECI, GCPD, PGE, SCL, TPWR) report no solar generation, and PSEI
reports solar only from November 2021 at 0.1% of demand, so their net load was undefined and they fell out.
Change: a source (solar or wind) that a BA reports in fewer than 1% of hours, or whose 2025 energy share is
below 1%, counts as zero when missing. This affects only the low-solar group, hence only H4; H1 to H3 use the
high-solar group alone. WALC (6.6% solar) stays out because its solar and wind series have gaps that cannot
be set to zero. First-run results are kept in out/v1.

## Amendment 2 (19 November 2026, after an internal review)

No code bug was found. Exploratory checks added after the results (code/robustness2.py, out/robustness2.json):
- Net load as demand minus solar only and minus wind only; solar without integrated storage (the extract now keeps
  that column separately).
- Days required complete in demand and net load only (the main rule also requires the forecast).
- 2019 against 2025; month-stratified shifts; without the BAs that do not observe daylight saving time.
- Mean peak hour with a bootstrap interval over BAs; share of days with the net-load peak at hour ending 20 or later;
  Spearman correlation of the shift with solar share.
- H3 at fixed hours (each BA's late-period median hours) instead of each day's realised peak hour, which selects on
  the outcome.
- A check of solar timestamps (hour of the median daily solar maximum, night-time solar share) and H1/H2 without
  the BAs whose solar series look misaligned (night share above 5% or a drift of three hours or more).
- A swap of median profiles: early demand with late solar and wind, and the reverse.
Undisclosed rule now stated: a BA needs at least 30 complete days in each period (this removes WALC).

## Amendment 3 (19 November 2026, exploratory, after an independent review)

An independent automated review (AI-Scientist-v2 reviewer form) of the submitted paper asked why some low-solar
BAs moved, for pre-trends, for a continuous peak-time measure and for a mechanical counterfactual. The checks
below are written down before any of them is computed. All are exploratory; H1 to H4, the pre-specified secondary
analyses and their results are unchanged. Code: code/robustness3.py, output out/robustness3.json.

1. Low-solar BAs whose median net-load peak moved two hours or more (MISO, PJM, SC in the main run). For every BA:
   the shift with solar only (D - S) and wind only (D - W) subtracted, as in Amendment 2; summer (June to September)
   solar and wind energy as a share of demand in each period; the profile swap of Amendment 2; the gap in the
   early-period median demand profile between the demand peak hour and the late-period net-load peak hour (how much
   midday supply it takes to move the peak); the solar timestamp check of Amendment 2 (hour of the median daily solar
   maximum, night-time share) by year; and the offset between the local hour number and UTC by summer (a clock
   change would move every series). Known forecast offsets (PJM from February 2019, SC from August 2025) concern the
   forecast column only, so they cannot move a peak hour; they matter only for forecast errors.
2. Pre-trend placebo: July to September 2018 (generation by source starts in July 2018) against July to September
   2019, same day rule and screening. Per-BA shift in median and mean net-load peak hour; sign test in the
   high-solar group and Mann-Whitney test high against low, as for H1 and H4. For comparison, the main contrast
   restricted to July to September.
3. Continuous peak time. For each day, the vertex of the parabola through net load at the peak hour and the hours
   either side (left at the integer hour when the peak is at the first or last hour of the day). Per BA, the median
   over days in each period; shift; sign and Wilcoxon signed-rank tests in the high-solar group, Mann-Whitney high
   against low. Also the circular mean of the daily integer peak hour (24-hour circle).
4. Mechanical counterfactual. From median summer profiles by hour in each period: the observed peak hour of
   D_late - S_late - W_late against (a) the early profile D_early - S_early - W_early, (b) the swap D_early - S_late -
   W_late (Amendment 2) and (c) D_late - k_S S_early - k_W W_early, with k the ratio of late- to early-period mean
   summer output of each source (early shapes, late volumes). Peak times of the profiles by the same parabolic
   vertex. Reported: predicted against observed shift per BA.
5. Forecast data quality and H3. For each BA and summer, the shift of the forecast (-3 to +3 hours) that minimises
   the median absolute percentage error against demand. H3, at realised and at fixed hours, without CISO (forecast
   offset in summer 2025), FPC and PSCO (forecast level gaps) and AZPS, EPE and SRP (suspect solar timestamps,
   which set the hour at which the error is read). The pre-specified H3 robustness without PJM and CISO is computed
   by code/solar.py but was not reported; it is now reported.
