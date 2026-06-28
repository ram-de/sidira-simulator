# Pre-registration — iteration 3: negative-control guard on REAL data (Hillstrom)

**Sealed before running** (sha256 committed alongside).

## Why
iter2's LEAD is synthetic. The campaign promotion bar is real-data replication. Hillstrom is a
TRUE randomized email RCT (Womens E-Mail vs No E-Mail; true email lift ≈ +4.52pp on `visit`).
Test whether the negative-control guard behaves correctly on real data — both its **specificity**
(don't abstain on a clean experiment) and its **sensitivity** (abstain when a hidden confounder
biases the estimate).

## Design (frozen `causal_estimator`, NC_BAND=0.05 from iter2)
- **Treatment** T = Womens E-Mail. **Main outcome** Y = `visit` (binary).
- **Negative-control outcome** = `mens` — a PRE-treatment purchase flag the email cannot have
  caused, but which correlates with spend `history`. Held OUT of the adjustment set.
- **Adjustment set X** = recency, womens, newbie, channel, zip dummies (note: `history` and the
  negative control `mens` are BOTH excluded — `history` is the deliberately-hidden confounder).
- **Two conditions, same guard:**
  - **(A) CLEAN** — no injection (the real RCT as-is).
  - **(B) INJECTED+HIDDEN** — resample selecting on standardized `log_history` (email arm
    over-samples low-history; keep-prob sigmoid(∓1.5·h)), then keep `history` HIDDEN from X.
- For each condition estimate the main T→`visit` effect AND T→`mens` (the guard), adjusting for X.

## Falsifiable predictions
1. **Specificity (A):** in the clean RCT the negative-control effect is ≈ 0 (`|nc| < 0.05`) →
   guard does NOT trip → main estimate (≈ true +4.5pp) is trusted. (Randomization ⇒ T ⟂ mens.)
2. **Sensitivity (B):** with the hidden confounder, the main `visit` estimate is biased (sign or
   magnitude off vs +4.5pp) AND the negative-control effect is **materially larger than in (A)**.
3. **Decision-relevant (B):** the negative-control effect crosses the 0.05 floor → guard trips →
   correctly abstains on the biased estimate.

## Honest risk (pre-registered, NOT a post-hoc excuse)
Hillstrom's observed covariates are correlated with `history` (iter0's Hillstrom ablation already
showed they PROXY spend). So adjustment for X may absorb much of the hidden-history association,
shrinking the negative-control effect. If so, P3 may FAIL even though P2's direction holds: the
guard under-trips because proxies launder the confounder. That is itself a real, reportable
finding (negative controls weaken when strong proxies exist) — and the correct verdict would be
NULL/partial, not a fudge.

## Decision rule
- P1 PASS (specificity) AND P2 PASS AND P3 PASS → **LEAD (real-data replication of iter2)** —
  strongest result the campaign can produce short of a customer deployment.
- P1 PASS, P2 PASS, P3 FAIL (proxy absorption) → **MECH-ONLY / partial** — guard is directionally
  right on real data but the fixed 0.05 floor doesn't transfer; log the magnitudes, note proxy
  laundering, do not re-tune here.
- P1 FAIL (trips on the clean RCT) → **NULL** — guard is not specific; unusable as-is.
