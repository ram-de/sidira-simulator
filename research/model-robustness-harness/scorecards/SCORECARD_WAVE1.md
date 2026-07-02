# Method Bake-Off Wave 1 — Scorecard (predicted vs actual)

Sealed predictions sha256 `32b2918c99afd7e5…` (frozen before any run; nothing tuned to match).

Ground truth (measured full-RCT): Cookie Cats retention_7 = **negative**; Hillstrom visit = **positive**.

## cookie_cats / retention_7  (truth = negative)

| method | A | B_obs | B_hidden | guard A/B_obs/B_hidden | pred-hits |
|---|---|---|---|---|---|
| naive_diff_in_means | ✓ -0.0082 | ✗ +0.2176 | ✗ +0.2176 | — | 3/3 |
| t_learner | ✓ -0.0077 | ✓ -0.0031 | ✗ +0.2176 | — | 3/3 |
| ipw | ✓ -0.0057 | ✓ -0.0019 | ✗ +0.2176 | — | 3/3 |
| x_learner | ✓ -0.0078 | ✓ -0.0066 | ✗ +0.2179 | — | 3/3 |
| dr_aipw | ✓ -0.0077 | ✓ -0.0055 | ✗ +0.2176 | — | 3/3 |
| survival_hazard | ✓ -0.0031 | ✓ -0.0016 | ✗ +0.2051 | — | 3/3 |
| negative_control_guard | — | — | — | trust/trust/TRIP | 3/3 |

## hillstrom / visit  (truth = positive)

| method | A | B_obs | B_hidden | guard A/B_obs/B_hidden | pred-hits |
|---|---|---|---|---|---|
| naive_diff_in_means | ✓ +0.0452 | ✓ +0.0259 (pred✗) | ✓ +0.0259 (pred✗) | — | 1/3 |
| t_learner | ✓ +0.0454 | ✓ +0.0488 | ✓ +0.0383 (pred✗) | — | 2/3 |
| ipw | ✓ +0.0454 | ✓ +0.0481 | ✓ +0.0395 (pred✗) | — | 2/3 |
| x_learner | ✓ +0.0454 | ✓ +0.0475 | ✓ +0.0393 (pred✗) | — | 2/3 |
| dr_aipw | ✓ +0.0454 | ✓ +0.0479 | ✓ +0.0385 (pred✗) | — | 2/3 |
| discrete_choice_logit | ✓ +0.0454 | ✓ +0.0483 | ✓ +0.0382 (pred✗) | — | 2/3 |
| negative_control_guard | — | — | — | trust/trust/TRIP | 3/3 |

**Prediction accuracy: 35 hits / 42 cells.**

### Where predictions missed
- Hillstrom *visit* has a large true effect (+4.52pp). The injected selection (beta=1.5) only ATTENUATED it; it never flipped sign, so naive (B_obs/B_hidden) and the causal methods (B_hidden) all kept the correct sign where I had predicted a flip. Hillstrom was effectively un-stressable at this confounding strength — Cookie Cats (tiny -0.82pp true effect) is the discriminating dataset and behaved exactly as predicted.
- The guard still TRIPS on Hillstrom B_hidden (NC residual ~-0.21 > floor) even though the point estimate stayed correct: a CONSERVATIVE (false) abstention — the cost the guard's docstring names. It is driven entirely by the strongly-coupled constructed control `nc_trait`; the weakly-coupled native controls (mens/womens, residual ~0.001) would have missed it — the documented 'needs one strongly-coupled control' limit.
