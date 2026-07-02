# Method Bake-Off — Wave 1 (pre-registration)

**Sealed predictions:** `../BAKEOFF_SEALED_PREDICTIONS.json`
**sha256:** see `PREREG_WAVE1.sha256` (`32b2918c…`).
Predictions were written and hashed BEFORE any estimator was run. No estimator was
tuned to match them.

## Motivation

First wave of a non-LLM method bake-off. Question: do several hand-rolled
behavior/causal methods recover the **directionally correct** treatment-effect SIGN
on two real A/B tests with KNOWN ground truth — and does the negative-control guard
abstain exactly when an estimate is untrustworthy?

These are real public datasets, so every cell counts as **public-real** evidence
(not MECH-ONLY synthetic).

## Ground truth (measured full-RCT diff-in-means — a fact, not a prediction)

| Dataset | Treatment | Outcome (headline) | True ATE | True sign |
|---|---|---|---|---|
| Cookie Cats | gate_40 vs gate_30 | retention_7 | -0.82pp | **negative** (gate_30 wins — the counter-intuitive published result) |
| Cookie Cats | gate_40 vs gate_30 | retention_1 | -0.59pp | negative |
| Hillstrom | Womens E-Mail vs No E-Mail | visit | +4.52pp | **positive** (email wins) |
| Hillstrom | Womens E-Mail vs No E-Mail | conversion | +0.31pp | positive |

## Methods (all hand-rolled on numpy/sklearn/scipy — no econml/causalml/lifelines)

1. naive diff-in-means · 2. T-learner · 3. IPW · 4. X-learner · 5. DR/AIPW ·
6. negative_control_guard (reused from causal_estimator.py) ·
7. discrete-time survival hazard (Cookie Cats only) ·
8. conditional-logit / discrete choice (Hillstrom only).

## Conditions

- **A — clean / randomized:** data as-is; randomization holds; the ATE *is* the truth.
- **B_obs — injected confounding, confounder OBSERVED:** select units into treatment
  on a covariate that also drives the outcome (Cookie Cats: engagement; Hillstrom:
  baseline spend), then hand the method that covariate.
- **B_hidden — injected confounding, confounder UNOBSERVED:** same selection, but the
  confounder is ablated from the covariate set. The method is not told the rule.

## Decision rule

- A method earns **LEAD** if it recovers the true sign in **both A and B_obs**
  (directionally robust to *adjustable* confounding).
- **NULL** if it flips sign in B_obs without any abstention signal.
- **B_hidden** is the unobservable-confounding stress — causal adjustment *cannot*
  fix a confounder it was never given, so the WIN there belongs to the **guard
  abstaining**, not to the point estimate.
- The **negative_control_guard** is scored on calibration: trust (no trip) in A & B_obs,
  abstain (trip) in B_hidden.

## Headline predictions

- naive is the only method predicted to flip under *adjustable* (B_obs) confounding.
- NO method recovers the sign under truly unobserved (B_hidden) confounding; only the
  guard's abstention is correct there.
- Survival hazard and discrete-choice logit add NOTHING directional over the plain
  causal estimator (they reduce to the same adjusted logistic comparison).
- The NC-guard trips in B_hidden on both datasets and does not trip in A or B_obs.
