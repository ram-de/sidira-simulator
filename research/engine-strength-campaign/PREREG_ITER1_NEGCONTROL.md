# Pre-registration — iteration 1: negative-control guard

**Sealed before running** (sha256 of this file committed alongside).

## Motivation (from iter0)
Overlap-based confidence flagged 0 of 3 errors; the failures were unobserved-confounding
(dataset_08 large spurious +, dataset_02 proxy case) and a true-null residual (dataset_03).
Overlap can't see unobserved confounding **by construction**. A negative-control outcome
(a metric the treatment should NOT affect, but which shares the confounding) can: if the
estimator finds a non-zero "effect" on it, residual confounding is present.

## Design
Regenerate the 10-regime challenge (fresh secret seed, self-blind) with an ADDED column
`neg_control` — a binary metric with TRUE treatment effect = 0, driven by the SAME confound
signal as the real outcome (observed `activity` for observed-confounding regimes; the latent
`U` for the unobserved-confounder regimes). Predict blind as in iter0, plus estimate the
treatment→`neg_control` effect (adjusting for observed covariates). **Guard:** downgrade the
main estimate to `low/abstain` when `|neg_control effect| > 0.02`.

## Falsifiable predictions
1. **PRIMARY:** the guard trips (low/abstain) on the **unobserved-confounder regimes**
   (`unobserved_no_proxy`, `unobserved_with_proxy`) — catching errors overlap missed.
2. The guard does **NOT** trip on the clean-RCT and observed-confounding regimes (it leaves
   the cases the core gets right at high confidence) — i.e. low false-alarm rate.
3. **Honest limit predicted:** the guard does **NOT** reliably catch the `true_null_confounded`
   case (that error is estimator residual on *observed* confounding, not a hidden confounder),
   so negative controls are necessary but not a complete fix.

## Decision rule
- If P1 holds AND P2 holds (guard catches the unobserved cases without flooding false alarms):
  LEAD — negative-control guard materially improves calibration; promote to the router design
  pending a real-data replication.
- If the guard trips everywhere (kills P2) or misses the unobserved cases (kills P1): NULL —
  log and move on.
- Synthetic => ceiling verdict is MECH-ONLY regardless; real-data replication still required.
