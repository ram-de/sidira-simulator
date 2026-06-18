# CERTIFIED: who-responds-more heterogeneity holds at power (#342)

**Pre-registered** (`PREREG_HETEROGENEITY.json`, integrity `7e38d59e2e498444…`,
committed before the result, with the pass/fail bar fixed in advance). Path
recommended by an independent Codex second opinion: certify the *non-trivial*
heterogeneity claim before any product/engine change, because the sign-fix
(email > no-email) is partly common-world knowledge. Ground truth from the real
Hillstrom RCT CSV. Date: 2026-06-17.

## Pre-registered bar
Heterogeneity CERTIFIED iff **VISIT Spearman ρ > 0.30 AND permutation p < 0.05.**

## Result (gender × recency × channel × email; 38 cases; both outcomes)

| model | VISIT heterogeneity ρ (perm p) | gender-match differential ρ (perm p) | CONVERSION ρ (perm p) | bar |
|---|---|---|---|---|
| **Sonnet** | **+0.420 (0.010)** | **+0.753 (0.0004)** | +0.259 (0.11) | **CERTIFIED** |
| Groq | +0.432 (0.006) | +0.347 (0.15) | +0.163 (0.33) | CERTIFIED (visit) |

(For reference: the original certified reader-roleplay run had visit heterogeneity
ρ = −0.29, at chance.)

## What is now established at power

1. **The "who-responds-more" claim holds for visits — certified, and on both
   models.** Visit heterogeneity rank correlation is +0.42 (Sonnet, p=0.010) and
   +0.43 (Groq, p=0.006). The ranking signal is not model-idiosyncratic.
2. **The non-obvious, base-rate-proof test is the strongest result.** The
   gender-match differential — does the model know that, *within the same
   audience*, the men's email beats the women's email by the right amount? —
   is **+0.753 (p=0.0004)** for Sonnet. This is the claim a sophisticated buyer
   cannot trivially guess, and it directly answers the "is it just base-rate
   knowledge?" objection: it is not. (Groq gets the overall ranking but not this
   sharper differential, p=0.15.)
3. **Direction (sign) holds** (Sonnet visit dir_acc 0.97), as in the powered
   sign-fix run.

## Honest limits (unchanged discipline)

- **Conversion heterogeneity is NOT certified** (Sonnet +0.259, p=0.11). The
  certified claim is **visit-only**; conversion is positive-leaning but not at
  significance. We narrow the claim accordingly.
- The clean *gender-match* differential is **Sonnet-specific**; Groq gets the
  coarse ranking but mis-signs more and fails the differential. Cross-model
  robustness holds for the ranking, not for the sharp differential.
- Fresh transparent stratification (gender × recency × channel), not the §4
  clustering; related, not identical.
- Magnitudes remain uncalibrated and out of scope.

## Where this leaves the program (Codex sequencing)

Heterogeneity has cleared its pre-registered bar (visit, both models; gender-match
strongly for Sonnet). Per the agreed sequencing, this is the first real
justification to consider a **product/engine change**: implement expert-forecaster
outcome-elicitation behind a flag, with personas demoted to the explanation /
interview surface, then re-run the certified benchmarks through the engine to
measure the product-level improvement. The benchmark program has now produced:
a confirmed accuracy lever (elicitation framing), a fixed sign-inversion, and a
certified who-responds-more heterogeneity claim on real RCT ground truth —
all pre-registered, all with the failures (conversion, Groq differential) shown.
