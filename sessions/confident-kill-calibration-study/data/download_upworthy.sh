#!/usr/bin/env bash
# Fetch the raw Upworthy Research Archive CSVs from OSF (project jd64p).
# These are ~90MB total of third-party data, so they are NOT committed — run this
# to reproduce the labeled_pairs_*.csv build from scratch.
set -euo pipefail
cd "$(dirname "$0")"
echo "Downloading Upworthy Research Archive (exploratory + confirmatory + holdout)..."
curl -sL "https://osf.io/download/3vqmp/" -o upworthy_exploratory.csv    # 14MB
curl -sL "https://osf.io/download/vy8mj/" -o upworthy_confirmatory.csv   # 66MB
curl -sL "https://osf.io/download/ynf3k/" -o upworthy_holdout.csv        # 14MB
echo "Done. Columns of interest: clickability_test_id, headline, lede, impressions, clicks, winner."
echo "Source: https://osf.io/jd64p/  (Matias et al., Scientific Data 2021)"
