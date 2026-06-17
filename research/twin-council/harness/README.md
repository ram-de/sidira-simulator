# Directional-correctness evaluation harness

Runnable implementation of the **G0–G11 certification gate** from the
twin-council white paper (`../WHITE-PAPER.md`, ledger `../MERGED-LEDGER.md`).
A behavioral simulator may emit a numeric confidence score only if this gate
returns **GO**.

Pure standard library — no third-party dependencies. Python 3.9+.

## Run

```bash
cd research/twin-council/harness
python3 test_directional_eval.py     # self-running, prints PASS/FAIL per test
# or, if you have pytest:
pytest test_directional_eval.py
```

## What it computes (`directional_eval.py`)

- `balanced_sign_match_rate`, `wilson_interval` — direction (G4)
- `mcc_multiclass` — 3-class pos/flat/neg classification (G5)
- `kendall_tau_b` — ranking (G6)
- `expected_calibration_error`, `brier_multiclass` / `brier_climatology` — calibration (G7)
- `decision_utility` — ΔU vs. status-quo triage, asymmetric false-red cost (G8, **primary**)
- `tail_winner_recall` — tail safety (G9)
- `aa_false_signal_rate` — A/A placebo integrity (G1)
- `label_permutation_smr` — leakage probe; pass a `predict_fn` so it regenerates
  predictions on permuted labels and actually catches leakage (G3)
- `selective_risk` / `abstention_is_monotone` — abstention quality (G10)
- `bootstrap_ci` — paired bootstrap over experiments (M15)
- `certify(exps, aa_exps, cfg)` → `GateResult` with verdict **GO / CONDITIONAL / NO-GO**

## Wiring into CI (recommended, M20)

Treat the gate as a release gate on the confidence score: a model/prompt/weekly
snapshot change cannot ship a numeric confidence unless `certify()` re-returns GO
on the customer's golden backtest set. Feed real `Experiment` records (historical
experiments with true effects and the simulator's calibrated class probabilities)
instead of the synthetic generator in the tests.

## Honest limitations

- The leakage probe is only meaningful with a `predict_fn` that re-runs on
  permuted inputs; with stored static predictions it trivially collapses to ~0.5
  and proves nothing. This is documented in the function and enforced in tests.
- `decision_utility`'s cost model (false-green / false-red ratio, slot budget) is
  customer-specific and must be elicited per customer; the default
  `false_red_cost=3.0` is a placeholder, not a recommendation.
- Thresholds (SMR ≥ 0.70, τ_b ≥ 0.30, ECE ≤ 0.08, etc.) are the council's
  committed numbers; the sample-size gate (G0) is what makes a passing score
  trustworthy. Below 50 sign-decisive experiments the correct output is
  "uncalibrated", not a number.
