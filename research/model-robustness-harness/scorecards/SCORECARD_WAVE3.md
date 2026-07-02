# Method Bake-Off Wave 3 — Scorecard: AUTO-DISCOVERY of the effect-modifier

Sealed predictions sha256 `789317d6aeeee1bb…` (frozen before any run; nothing tuned to match).

Q: discover WHICH covariate the effect concentrates/flips on, WITHOUT being told — and stay silent on null.
True modifier = USAGE axis {plays_28d, watch_minutes_28d, avg_session_min, completion_rate, titles_started_28d}; plan_tier = null axis. Floor rule: discovered iff stat>95th-pct(placebo) AND ratio≥1.5.

## 1. Modifier-discovery scoreboard

Cell = top-ranked covariate · discovered?(floor) · ✓/✗ vs ground truth.

| dataset | role | CATEvar-ratio | X-learner CATE importance | transformed-outcome honest tree | BLP linear |
|---|---|---|---|---|---|
| v2/dataset_06 | hetero | 24.047 | plays_28d · DISC · ✓ | plays_28d · DISC · ✓ | plays_28d · DISC · ✓ |
| v3/dataset_09 | hetero | 18.356 | plays_28d · DISC · ✓ | plays_28d · DISC · ✓ | plays_28d · none · ✗ |
| v2/dataset_06 [+confounding on tenure_days] | hetero_stress | 14.869 | plays_28d · DISC · ✓ | watch_minutes_28d · DISC · ✓ | plays_28d · DISC · ✓ |
| v2/dataset_03 | constant_specificity | 1.718 | none · ✓none | DISC(watch_minutes_28d) · ✗invented(watch_minutes_28d) | none · ✓none |
| v2/dataset_08 | constant_specificity | 0.69 | none · ✓none | none · ✓none | none · ✓none |
| v2/dataset_01 | constant_specificity | 0.664 | none · ✓none | none · ✓none | none · ✓none |
| tn_01 | true_null | 2.142 | none · ✓none | DISC(x3) · ✗invented(x3) | none · ✓none |
| tn_03 | true_null | 1.454 | DISC(x0) · ✗invented(x0) | DISC(x3) · ✗invented(x3) | none · ✓none |
| tn_05 | true_null | 0.983 | none · ✓none | none · ✓none | none · ✓none |
| tn_07 | true_null | 1.152 | none · ✓none | DISC(x3) · ✗invented(x3) | none · ✓none |

**Sensitivity (clean hetero):** X-learner CATE importance 2/2 · transformed-outcome honest tree 2/2 · BLP linear 1/2
**Sensitivity under confounding stress:** X-learner CATE importance 1/1 · transformed-outcome honest tree 1/1 · BLP linear 1/1
**Specificity (no false discovery on null/constant):** X-learner CATE importance 6/7 · transformed-outcome honest tree 3/7 · BLP linear 7/7

## 2. Downstream sign recovery after AUTO-discovery

After auto-picking the modifier, split at its median; low-usage should be + , high-usage − (matches the Wave-2 told-the-modifier result casual=+/power=−).

| dataset | method | auto-modifier | low-usage CATE | high-usage CATE | both signs ✓? |
|---|---|---|---|---|---|
| v2/dataset_06 (hetero) | X-learner CATE importance | plays_28d | +1.1687 (pos) | -0.2415 (neg) | ✓ |
| v2/dataset_06 (hetero) | transformed-outcome honest tree | plays_28d | +1.1687 (pos) | -0.2415 (neg) | ✓ |
| v2/dataset_06 (hetero) | BLP linear | plays_28d | +1.1687 (pos) | -0.2415 (neg) | ✓ |
| v3/dataset_09 (hetero) | X-learner CATE importance | plays_28d | +1.1540 (pos) | -0.2561 (neg) | ✓ |
| v3/dataset_09 (hetero) | transformed-outcome honest tree | plays_28d | +1.1540 (pos) | -0.2561 (neg) | ✓ |
| v3/dataset_09 (hetero) | BLP linear | plays_28d | +1.1540 (pos) | -0.2561 (neg) | ✓ |
| v2/dataset_06 [+confounding on tenure_days] (hetero_stress) | X-learner CATE importance | plays_28d | +1.3793 (pos) | +0.0037 (pos) | ✗ |
| v2/dataset_06 [+confounding on tenure_days] (hetero_stress) | transformed-outcome honest tree | watch_minutes_28d | +1.2783 (pos) | +0.1264 (pos) | ✗ |
| v2/dataset_06 [+confounding on tenure_days] (hetero_stress) | BLP linear | plays_28d | +1.3793 (pos) | +0.0037 (pos) | ✗ |

**Downstream both-signs recovery (clean hetero):** X-learner CATE importance 2/2 · transformed-outcome honest tree 2/2 · BLP linear 2/2
**Downstream under confounding stress:** X-learner CATE importance 0/1 · transformed-outcome honest tree 0/1 · BLP linear 0/1 — discovery survives but the high-usage NEGATIVE segment washes to ~0 under injected selection.
Wave-2 baseline (handed the composite modifier): X-learner recovered both per-segment signs on both clean datasets — auto-discovery REPRODUCES that on clean data.
