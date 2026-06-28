# Synthetic Streamly Challenge — Scorecard (iteration 0)

**Integrity:** sha256 `028888ca97da4ad3…` — OK — matches committed hash

> Self-generated with seed-blinding => **MECH-ONLY** (mechanism/integration test). Synthetic success is necessary, not sufficient; real-data validation remains the bar.

**Headline (should-work set, n=8):** causal **7/8** (88%) vs naive **6/8** (75%) directional. Magnitude MAE = 0.1228.

**True-null regime:** dataset_03.csv (true ATE +0.0000): causal said **treatment** (want null/uncertain) — naive trap: treatment

**Unobserved-confounder traps (honesty check — expected to fail):**
- dataset_08.csv (unobserved_no_proxy, true negative): causal **treatment** WRONG (expected — no proxy), confidence=high

## Per-dataset

| File | Regime | True | True ATE | Naive | ✓ | Causal | t-learner | ✓ | Conf |
|---|---|---|---|---|---|---|---|---|---|
| dataset_01.csv | confounded_strong_poor_overlap | positive | +0.1094 | treatment | Y | treatment | +0.1318 | Y | high |
| dataset_02.csv | unobserved_with_proxy | negative | -0.0578 | treatment | N | treatment | +0.0351 | N | high |
| dataset_03.csv | true_null_confounded | null | +0.0000 | treatment | N | treatment | +0.0162 | N | high |
| dataset_04.csv | heterogeneous_net_positive | positive | +0.3496 | treatment | Y | treatment | +0.9687 | Y | high |
| dataset_05.csv | confounded_nonlinear | positive | +0.6000 | treatment | Y | treatment | +0.4491 | Y | high |
| dataset_06.csv | clean_rct_moderate | positive | +0.1343 | treatment | Y | treatment | +0.1383 | Y | high |
| dataset_07.csv | confounded_sign_flip | negative | -0.0656 | treatment | N | control | -0.0378 | Y | high |
| dataset_08.csv | unobserved_no_proxy | negative | -0.0543 | treatment | N | treatment | +0.2414 | N | high |
| dataset_09.csv | clean_rct_small | positive | +0.4000 | treatment | Y | treatment | +0.4436 | Y | high |
| dataset_10.csv | confounded_observed_moderate | positive | +0.1064 | treatment | Y | treatment | +0.1282 | Y | high |

## Calibration — the finding that matters

Across all 10 datasets the estimator was **wrong on 3**, and **3 of those 3 errors carried HIGH confidence**. The overlap-based confidence signal did not flag a single one of its own mistakes — because the failures (unobserved confounding, true-null residual) leave *observed*-covariate overlap looking healthy. **Overlap is necessary but NOT sufficient.** Before any empirical estimate is trusted, the router needs guards overlap can't provide: negative-control outcomes, placebo/sensitivity (Rosenbaum-style) bounds, and a humility default that routes unobserved-confounding-risk cases to LLM/abstain.

## Verdict

Directional, should-work set: causal **7/8** vs naive **6/8** — and the entire advantage is the **sign-flip** case (where confounding inverts the naive answer); on every other should-work regime they agree. So the causal core's value-add is concentrated exactly where confounding flips the sign, as designed.
Mechanism: VALIDATED on observed-confounding regimes (MECH-ONLY). Honest limits surfaced: (1) true-null returned a false positive; (2) the unobserved-confounder cases failed **at high confidence** — the calibration gap above is the real takeaway and the next thing to fix. Traps failing is expected (LLM territory); failing *silently* is not.