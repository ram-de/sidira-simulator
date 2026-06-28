# Negative-control guard — Scorecard (v3)

**Integrity:** sha256 `011dcf756a94dd18…` — OK

> Self-generated seed-blind => MECH-ONLY. Real-data replication still required.

**P1 (guard trips on unobserved-confounder regimes):** 2/2 -> PASS
**P2 (no false alarm on clean/observed cases it got right):** 7/7 clean -> PASS
**Error reduction:** without guard 3 wrong actions; with guard (abstain on trips) 1 wrong actions remain.

| File | Regime | True | Causal | ✓ | neg_control ATE | Tripped | Conf |
|---|---|---|---|---|---|---|---|
| dataset_01.csv | unobserved_no_proxy | negative | treatment | N | +0.2861 | TRIP | low/abstain |
| dataset_02.csv | unobserved_with_proxy | negative | treatment | N | +0.0971 | TRIP | low/abstain |
| dataset_03.csv | true_null_confounded | null | treatment | N | +0.0271 | · | high |
| dataset_04.csv | confounded_observed_moderate | positive | treatment | Y | +0.0272 | · | high |
| dataset_05.csv | confounded_nonlinear | positive | treatment | Y | +0.0187 | · | high |
| dataset_06.csv | confounded_strong_poor_overlap | positive | treatment | Y | +0.0405 | · | high |
| dataset_07.csv | clean_rct_small | positive | treatment | Y | -0.0074 | · | high |
| dataset_08.csv | clean_rct_moderate | positive | treatment | Y | +0.0005 | · | high |
| dataset_09.csv | heterogeneous_net_positive | positive | treatment | Y | +0.0182 | · | high |
| dataset_10.csv | confounded_sign_flip | negative | control | Y | +0.0137 | · | high |

## Verdict

LEAD — negative-control guard catches the unobserved-confounder errors overlap missed, with no false alarms on clean/observed cases.

Honest limit (P3, predicted): the guard keys on a negative-control outcome that shares the confounding; it catches HIDDEN confounding but not pure estimator residual on a true null unless that residual also shows on the control. Negative controls are a necessary guard, not a complete certificate — and in the router they require knowing WHICH metric is a valid negative control (LLM/domain judgment).