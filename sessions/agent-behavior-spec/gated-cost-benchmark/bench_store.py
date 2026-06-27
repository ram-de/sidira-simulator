#!/usr/bin/env python3
"""Append-only ledger for gated accuracy + cost benchmark runs (#39).

Every benchmark run (this gym one, and future live runs on the portfolio, a
re-run gym with per-case confidence, a customer backtest, …) records ONE row
here so results accumulate and stay comparable instead of being recomputed and
lost. Plain CSV on purpose: git-committed, diff-able, human-readable, no DB.

Reuse from any run script:
    from bench_store import record_run
    record_run(run_id="gym-rank-2026-06-26", dataset="milkman-gym", ...)

`run_id` is the idempotency key — re-running with the same id REPLACES that row
(so a corrected run overwrites cleanly rather than duplicating).
"""
from __future__ import annotations

import csv
from pathlib import Path

LEDGER = Path(__file__).resolve().parent / "RUNS.csv"

# Stable column order. Add new columns at the END only (old rows back-fill blank).
COLUMNS = [
    "run_id",            # idempotency key
    "run_date",          # ISO date the run was recorded
    "dataset",           # e.g. milkman-gym, product-portfolio, hewitt-megastudies
    "domain_type",       # "rank" (which-is-best) | "sign" (which-direction)
    "n_cases",           # matched cases scored
    "engine_ref",        # engine SHA / mode / "stored-blind-run" provenance
    "gated",             # yes/no — was the callable/too-tough abstention gate applied
    "primary_metric",    # name=value of the headline accuracy metric
    "tail_recall_at5",   # fraction of the true top-5 captured in the engine top-5
    "top5_capture",      # % of achievable effect in engine top-5
    "top5_random",       # % of achievable effect for a random top-5 (baseline)
    "callable_accuracy", # accuracy on the CALLABLE subset (blank if no confidence)
    "abstain_rate",      # fraction abstained (blank if gate not applied)
    "cost_per_experiment",  # $C assumed per real A/B test
    "dollars_saved",     # $ saved at the stated cost/target (blank if n/a)
    "verdict",           # gate verdict GO/CONDITIONAL/NO-GO or "rank-only"
    "scope_caveat",      # one-line honesty caveat for this row
    "source_files",      # provenance paths
]


def record_run(**fields: object) -> Path:
    """Upsert one run row keyed by run_id. Unknown keys are ignored; missing
    columns are written blank. Returns the ledger path."""
    run_id = fields.get("run_id")
    if not run_id:
        raise ValueError("record_run requires a run_id")
    rows: list[dict[str, str]] = []
    if LEDGER.exists():
        rows = [r for r in csv.DictReader(open(LEDGER)) if r.get("run_id") != run_id]
    row = {c: str(fields.get(c, "")) for c in COLUMNS}
    rows.append(row)
    rows.sort(key=lambda r: (r.get("dataset", ""), r.get("run_date", "")))
    with open(LEDGER, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    return LEDGER


if __name__ == "__main__":  # show the current ledger
    if LEDGER.exists():
        print(LEDGER.read_text())
    else:
        print("(no runs recorded yet)")
