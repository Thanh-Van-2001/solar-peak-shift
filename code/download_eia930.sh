#!/bin/bash
# Download EIA-930 six-month BALANCE files (public) and keep sha256 hashes.
# Atomic: write to .part, rename when complete. Polite pacing.
set -u
cd "$(dirname "$0")/../data/raw" || exit 1
BASE=https://www.eia.gov/electricity/gridmonitor/sixMonthFiles
for y in $(seq 2015 2026); do
  for h in Jan_Jun Jul_Dec; do
    [ "$y" = 2015 ] && [ "$h" = Jan_Jun ] && continue
    f=EIA930_BALANCE_${y}_${h}.csv
    if [ -s "$f" ]; then echo "have $f"; continue; fi
    code=$(curl -sS -m 600 --retry 3 --retry-delay 20 -o "$f.part" -w "%{http_code}" "$BASE/$f")
    if [ "$code" = 200 ] && [ -s "$f.part" ]; then mv "$f.part" "$f"; echo "got $f $(stat -c %s "$f")"
    else echo "FAIL $f http=$code"; rm -f "$f.part"; fi
    sleep 5
  done
done
sha256sum EIA930_BALANCE_*.csv > ../SHA256SUMS
echo DOWNLOAD_DONE
