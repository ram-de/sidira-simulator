# Portfolio V4 expansion — RESULT (rejects broad directional accuracy on counter-intuitive product changes)

**Pre-registered** (`PREREG_PORTFOLIO_V4_EXPANSION.json`, cases canonical SHA-256
`b110dce32573b4e5a0bc8591b9ea2daaeb034c979975d4b9b14df1046a886595`, sealed +
committed before the run). 10 NEW real product/UI/copy A/B cases, deduplicated
against V3/CONFIRM, winners verified from primary sources (2 fabrication-risk
cases dropped at authoring), descriptions independently leak-audited twice
(negation-asymmetry fixed; residuals WEAK + inherent only). Method: comparative-
forecaster, claude-sonnet-4-6, k=4. Blind — `real_winner` never shown.

## Result

| pile | score | role |
|---|---|---|
| **less-won (simpler option won; more-is-better predicts WRONG)** | **1/4 (0.25)** | the decisive diagnostic |
| more-won (richer option won; more-is-better predicts RIGHT) | 3/4 (0.75) | a biased guesser passes these |
| ambiguous (uncertainty axis) | 1/2 | — |
| **OVERALL direction accuracy** | **5/10 (0.500)** | **below the always-treatment baseline (0.80)** |

Per-case: apparel-hide-discount ✅; coupon-deadline ❌; referral-sender ✅;
referral-recipient ❌; time-scarcity ❌; image-zoom ❌; carousel-count ❌;
only-word ✅; dropzone-weight ✅; popularity-count ✅.

## Verdict — per the sealed decision rule

The registered "bias persists" prediction was **less_won ≤ 0.25 AND more_won ≥ 0.75**.
Observed: **0.25 and 0.75** — the REJECT branch, hit almost exactly. The pre-registered
prediction was confirmed in the un-flattering direction (the most credible kind of result).

**REJECTS a broad directional-accuracy claim on counter-intuitive product changes.**
Overall 0.500 is at chance and *below* the naive always-treatment baseline (0.80);
on the trick pile (where doing less won) the engine was wrong 3/4. This **replicates**
the earlier confirmatory negative (0.286, 4/14) on a fresh, independently-authored,
leak-audited, pre-registered set.

## Honest nuance
Not a *pure* more-is-better robot: it correctly picked the minimal storefront
(apparel) and wrongly picked the *smaller* carousel — so predictions are essentially
uncorrelated with truth on this class, of which the more-is-better lean is the most
visible symptom. The truer statement is "no reliable directional signal on
counter-intuitive product changes."

## What still stands (unchanged)
- The ONLY certified directional positive remains Hillstrom's who-responds-more
  ranking (rank-ρ +0.42). Direction on mostly-one-sided substrates (Hillstrom visit)
  is easy and strong; direction on balanced/counter-intuitive product changes is not.
- Consistent with the customer page (`/research/accuracy`): product-change = at chance,
  more-is-better bias persists, no certified signal. This test confirms, not overturns.
