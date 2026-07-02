# Method Bake-Off — Wave 3 Pre-Registration (SEALED before scoring)

**Question:** Can a non-LLM method **auto-discover** the effect-modifier (the segment
where the treatment effect concentrates or flips) **without being told it**, and correctly
report **"no modifier"** when the effect is homogeneous / true-null?

Wave 2 showed per-segment CATE recovers per-segment signs **only when handed the modifier**.
Wave 3 removes that crutch.

**Sealed predictions JSON:** `../BAKEOFF_SEALED_PREDICTIONS_WAVE3.json`
**sha256:** `789317d6aeeee1bb444a91cc7d46e009c3d8ffa89b5d9f8ab7740e3973a854e2`

## Methods (hand-rolled; sklearn/numpy/pandas/scipy only)
1. **CATE-on-covariates importance** — X-learner per-user CATE (RF), then permutation
   importance + single-covariate variance-explained ranking of candidate modifiers.
2. **Causal tree via transformed outcome** — Y\* = T·Y/e − (1−T)·Y/(1−e) (clipped e),
   shallow **honest** regression tree (separate split/estimate samples); top split = modifier.
3. **BLP of CATE** — regress estimated CATE on standardized covariates; largest |coef| = modifier.

## Ground truth (assumed from sealed keys + Wave-2)
- **Heterogeneous (modifier exists):** v2/dataset_06, v3/dataset_09 (`heterogeneous_net_positive`).
  True modifier = **USAGE axis** (plays_28d, watch_minutes_28d, avg_session_min, completion_rate,
  titles_started_28d); casual/low-usage → **+**, power/high-usage → **−**. `plan_tier` = NULL axis.
- **Homogeneous / true-null (no modifier):** synthetic_truenull tn_01..08 (ATE=0) + constant-effect
  confounded streaming (v2 ds03, ds08, ds01).

## Noise-floor rule (analogue of NC-guard floor=0.05 + ratio=1.5)
Permute T (K=8) to build a placebo null of the method statistic. **DISCOVERED** iff
`S_real > 95th-pct(S_null)` AND `S_real / median(S_null) >= 1.5`. Supporting gate:
CATE-variance ratio `Var(CATE_real)/median(Var(CATE_null))`. Subsample ≤6000 rows;
forests n_estimators=80, leaf=120; fixed seeds; **run ONCE, no tuning to predictions**.

## Scoring axes
- **Sensitivity:** top-ranked covariate ∈ usage set AND above plan_tier (on hetero data).
- **Specificity (false-discovery):** floor rule returns "no modifier" on null/constant data.
- **Downstream sign recovery:** auto-split on the discovered modifier → per-segment CATE signs
  (low-usage +, high-usage −) vs the Wave-2 told-the-modifier result.

## Condition
Clean + one observed-confounding stress: inject selection on `tenure_days` (a NULL covariate);
does modifier discovery survive?

## Headline predictions
- m2 (honest transformed-outcome tree) = best joint sensitivity+specificity; m1 close; m3 highest FDR.
- All rank a usage covariate #1 on hetero; all stay quiet on true-null **via the floor**.
- **Honest limit:** multiple-comparisons FDR across 10 covariates + noisy K=8 floor (BLP most
  at risk); PROXY-MODIFIER caveat — the true modifier is a composite, so any single covariate is
  only a usage proxy and ranking among collinear usage covariates is partly arbitrary.

_Logged to runstore with data_type: synthetic → caps at MECH-ONLY._
