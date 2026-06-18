# Fix attempt #2 — elicitation reframing FIXES the advertising-as-harm sign inversion (#342)

**Pre-registered** (`PREREG_FORECASTER.json`, integrity `91137220bbf849cd…`,
committed before the result). Ground truth computed from the real Hillstrom RCT
CSV (MineThatData 2008), not the simulator. Date: 2026-06-17.

## Background

The certified Hillstrom run (§4) found the **advertising-as-harm bias**: under
introspective reader-roleplay elicitation, the simulator predicted promotional
emails *lower* visits/conversions (direction accuracy **0.0**, all signs
inverted) where the real RCT shows they *raise* both. The report diagnosed this
as intrinsic to introspective reader-roleplay. Fix attempt #1 (affordance
rendering) was an honest null.

The Upworthy program (Benchmark 1) had independently found that **reframing
elicitation from reader-roleplay to expert forecasting** recovered directional
signal where roleplay was null. This tests that same lever on the named bug.

## Result (VISIT, powered, n=18: gender × recency-tier × email)

| predictor | direction accuracy | heterogeneity Spearman ρ (perm p) |
|---|---|---|
| reader-roleplay (certified §4) | **0.0** | −0.29 (at chance) |
| **expert-forecaster, Sonnet** | **1.000 (18/18)** | +0.374 (p = 0.13) |
| expert-forecaster, Groq | 0.667 | +0.419 (p = 0.09) |

## Read

1. **H1 (sign-fix) — CONFIRMED at power.** Sonnet expert-forecaster gets **every
   one of 18** per-segment visit directions correct, versus a *certified* 0.0
   under reader-roleplay. The advertising-as-harm sign inversion is **not
   intrinsic to the simulator** — it is an artifact of introspective reader-
   roleplay elicitation, and it is **fixed** by reframing the elicitation as
   expert forecasting. This is the report's #1 named accuracy problem, resolved
   (for the sign), pre-registered, on real RCT ground truth.
2. **H2 (heterogeneity) — not confirmed.** Visit rank correlation improved from
   certified −0.29 to **+0.374**, but the permutation p (0.13) does not clear
   significance at n=18. The "who-responds-more" ranking is now *positive-leaning*
   rather than at-chance, but is **not certified**. The exploratory probe's +0.65
   (n=6) regressed to +0.37 — small-sample optimism, caught by the powered run.
3. **Capable model required.** Groq's expert-forecaster still mis-signs a third of
   cases (dir acc 0.67); the clean fix is Sonnet-specific — consistent with the
   Upworthy finding that the lever is framing × capable-model together.

## What this establishes

The single largest accuracy lever found across both benchmarks is **how the
outcome is elicited**, not which model or how realistic the personas are.
Introspective reader-roleplay produces a systematic advertising-as-harm sign
inversion; expert-forecaster elicitation removes it (Sonnet: 0.0 → 1.0 visit
direction accuracy, certified at power). Heterogeneity ranking moves in the right
direction but needs more cases to certify.

## Honest limits

- Fresh transparent stratification (gender × recency), not the §4 clustering — a
  related, not identical, case set; the sign-fix is robust to that choice.
- Heterogeneity ranking not significant (n=18); a larger stratification is the
  next powered step before any "who-responds-more" claim.
- Visit only (the stronger signal); conversion sign was also fixed in the
  exploratory probe but is not powered here.
- This is the direction/sign claim; magnitudes remain uncalibrated (unchanged).
