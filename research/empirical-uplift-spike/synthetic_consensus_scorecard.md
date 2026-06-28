# Multi-NC consensus guard — Scorecard (iter4)

**Integrity:** sha256 `455cd5d3cff7b352…` — OK

> Self-blind synthetic ⇒ MECH-ONLY ceiling.

**P1 specificity (consensus does NOT trip where adjustment works):** 4/4 → PASS
**Sensitivity:** single-weak 2/4 vs **consensus 4/4** → P2 PASS

| File | Regime | Kind | main | weak trips | consensus trips | max|nc| |
|---|---|---|---|---|---|---|
| cset_01.csv | confounded_observed | specificity | +0.1010 | · | · | 0.031 |
| cset_02.csv | unobserved_no_proxy | sensitivity | +0.2610 | T | T | 0.292 |
| cset_03.csv | unobserved_with_proxy | sensitivity | +0.0627 | · | T | 0.126 |
| cset_04.csv | clean_rct | specificity | +0.1381 | · | · | 0.002 |
| cset_05.csv | confounded_observed | specificity | +0.1078 | · | · | 0.015 |
| cset_06.csv | unobserved_no_proxy | sensitivity | +0.2445 | T | T | 0.291 |
| cset_07.csv | clean_rct | specificity | +0.1364 | · | · | 0.006 |
| cset_08.csv | unobserved_with_proxy | sensitivity | +0.0448 | · | T | 0.137 |

## Verdict

LEAD (MECH-ONLY ceiling) — consensus recovers sensitivity, specificity preserved

Consensus over several negative controls trades a small added false-alarm risk (more controls = more chances to exceed the floor) for recovering the bias that a single WEAK control misses. Where it preserves specificity, it is the safer guard; the router should still prefer controls known to be strongly coupled.