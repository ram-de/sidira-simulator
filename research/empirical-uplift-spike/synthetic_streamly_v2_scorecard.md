# Negative-control guard — Scorecard (iter1)

**Integrity:** sha256 `05d6e9381dfdc711…` — OK

> Self-generated seed-blind => MECH-ONLY. Real-data replication still required.

**P1 (guard trips on unobserved-confounder regimes):** 2/2 -> PASS
**P2 (no false alarm on clean/observed cases it got right):** 4/7 clean -> FAIL
**Error reduction:** without guard 3 wrong actions; with guard (abstain on trips) 1 wrong actions remain.

| File | Regime | True | Causal | ✓ | neg_control ATE | Tripped | Conf |
|---|---|---|---|---|---|---|---|
| dataset_01.csv | clean_rct_small | positive | treatment | Y | -0.0035 | · | high |
| dataset_02.csv | unobserved_no_proxy | negative | treatment | N | +0.3000 | TRIP | low/abstain |
| dataset_03.csv | confounded_observed_moderate | positive | treatment | Y | +0.0213 | TRIP | low/abstain |
| dataset_04.csv | confounded_nonlinear | positive | treatment | Y | +0.0099 | · | high |
| dataset_05.csv | confounded_strong_poor_overlap | positive | treatment | Y | +0.0366 | TRIP | low/abstain |
| dataset_06.csv | heterogeneous_net_positive | positive | treatment | Y | +0.0196 | · | high |
| dataset_07.csv | true_null_confounded | null | treatment | N | +0.0180 | · | high |
| dataset_08.csv | clean_rct_moderate | positive | treatment | Y | -0.0012 | · | high |
| dataset_09.csv | unobserved_with_proxy | negative | treatment | N | +0.1045 | TRIP | low/abstain |
| dataset_10.csv | confounded_sign_flip | negative | control | Y | +0.0343 | TRIP | low/abstain |

## Verdict

NULL — guard did not cleanly separate (see P1/P2 below).

Honest limit (P3, predicted): the guard keys on a negative-control outcome that shares the confounding; it catches HIDDEN confounding but not pure estimator residual on a true null unless that residual also shows on the control. Negative controls are a necessary guard, not a complete certificate — and in the router they require knowing WHICH metric is a valid negative control (LLM/domain judgment).