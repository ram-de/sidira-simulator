# Method Bake-Off — Wave 2 Pre-Registration

**Sealed predictions:** `../BAKEOFF_SEALED_PREDICTIONS_WAVE2.json`
**sha256:** `6fc83393f7ba60fbd8c12b87cdd1d18d022cd50d73f0243a001ebe6fc652f1c3`

Frozen before any wave-2 run. Nothing below is tuned to results. Run once, no
re-tuning. Synthetic streaming results cap at `MECH-ONLY`.

## What wave 2 adds over wave 1

Wave 1 (Cookie Cats + Hillstrom) established: causal adjusters (T-learner, IPW,
X-learner, DR/AIPW) recover the true ATE sign under *observed* confounding and
flip under *hidden* confounding; the NC-guard abstains exactly on hidden
confounding; behavior-sim (survival, conditional-logit) added nothing on ATE
sign. Wave 2:

1. **Three more real RCTs**, including two counter-intuitive ones (Karlan
   match-ratio NULL, Orange retention **backfire**), scored on ATE sign in
   conditions A (clean) / B_obs (selection on an observed covariate) /
   B_hidden (same selection, confounder ablated).
2. **The heterogeneity test** (synthetic streaming): the one place behavior/CATE
   methods *should* beat plain ATE — per-segment sign recovery where the global
   ATE masks a sign flip.

## Datasets & design choices (fixed before running)

| Dataset | T (=1 vs =0) | Y | truth sign | confounder z (injection) | negative control |
|---|---|---|---|---|---|
| GOTV | Neighbors vs Control | primary2006 (voted) | **positive** (+8.1pp) | std(age) | primary2004 + constructed nc_z |
| Karlan | treatment vs control | gave | **positive** (small) | std(freq) | hpa + constructed nc_z |
| Orange-Belgium | t (outreach) | y (churn) | **positive** (backfire) | top-variance PC | constructed nc_z (no native pre-treatment NC) |

- Covariates handed to estimators: GOTV `[age, sex(male=1), hhsize]`; Karlan
  `[freq, years, dormant, female, couple, pwhite, mrm2]` (median-imputed NaN);
  Orange top-15 PCs by variance. B_hidden ablates `z` (replaced by noise).
- Selection injection reuses wave-1 `inject_selection` (BETA=1.5, SEL_SEED).
- The constructed `nc_z = Bernoulli(sigmoid(z))` mirrors wave 1 — a strongly
  z-coupled control so the guard has the documented "≥1 strongly-coupled
  control"; the guard trips on consensus (max |residual|) over the NC set.
- **Karlan match-ratio sub-test:** among the treated, T=`ratio==3` vs `ratio==1`,
  Y=gave, condition A only. Truth = **null**. Scored null if |estimate| < 0.005.
- GOTV is sub-sampled (seeded, both arms) to 50k rows for tractability; the
  +8.1pp effect is unaffected by sign.

## Predictions (summary; full machine-readable in the sealed JSON)

**Real RCTs (sign recovery A / B_obs / B_hidden):**

- **GOTV** (large +effect): naive recovers A, flips B_obs+B_hidden. Causal
  adjusters recover **all three** — the effect is too large to flip even with the
  confounder hidden (the Hillstrom "un-stressable" pattern). Guard: trust / trust
  / **abstain**.
- **Karlan** (tiny +effect): naive recovers A only. Causal adjusters recover
  A + B_obs, **flip B_hidden** (the discriminating small-effect case = Cookie
  Cats pattern). Guard: trust / trust / **abstain**. Match-ratio 3:1-vs-1:1 ⇒
  methods correctly call **~null**, do not impose a lift.
- **Orange** (backfire; naive is already *negative* in A): naive **flips in A**
  (wrong sign even clean). Optimistic call — T-learner / X-learner / DR recover
  the positive backfire in A after adjusting for PCs; IPW likeliest to fail.
  Flagged **low confidence**; the case most likely to break the optimistic story.

**Heterogeneity (streaming v2/ds06 + v3/ds09; true: casual=+, power=−):**

- Plain global ATE = **positive** → applied uniformly it predicts positive for
  **both** segments, **masking** the power-user flip.
- Naive within-segment diffs: casual +, power **+** (still masks — within-segment
  confounding biases it up).
- **X-learner and T-learner per-segment CATE: casual +, power − (RECOVER the
  flip).** ← the headline we are testing.
- `plan_tier` segmentation (negative control axis, no by-construction
  heterogeneity): **no flip** in any tier.
- Guard on the heterogeneous regime: **trust** (confounding observed); guard on
  the unobserved-confounder regimes: **abstain**.

## One honest pre-registered limit

CATE only beats plain ATE when you segment along the **true effect-modifier**
(the usage composite). The boundary here is reconstructed from generator
knowledge; an analyst segmenting on `plan_tier` (no true heterogeneity) sees
nothing and wrongly concludes homogeneity. **Finding the right modifier is the
unsolved part** — registered above as the `plan_tier` negative-control
segmentation. All streaming results are synthetic ⇒ `MECH-ONLY`.
