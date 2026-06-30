# PREREG — LaLonde fix diagnostic: is the guard's failure collinearity, and is it fixable?

Sealed before run. The LaLonde promotion test (NULL) identified the mechanism: the NC `re74` is
adjusted on `re75`, its near-collinear one-year-apart twin, which deflates the placebo residual
(−$17,333 raw → −$406 adjusted) so the guard under-trips on real confounding. This diagnostic tests
that mechanism AND a principled candidate fix — ONE shot, frozen now.

## Candidate fix (principled, specified before running)
Recompute the guard's negative-control residual with **`re75` REMOVED from the NC's adjustment set**
(re75 stays in the main outcome/propensity model). Rule: *do not adjust the negative control on a
covariate near-collinear with it.* Re-evaluate the trip decision on all three conditions A/B/C.
(Also report a stricter variant: NC adjusted on **no covariates** = the raw placebo, as the upper
bound on sensitivity.)

## Pre-registered predictions (sealed)
1. **Detection restored (B,C):** with re75 out of the NC adjustment, the NC residual on PSID and CPS
   exceeds the 0.05 floor → guard **TRIPS → abstains** on both. (Mechanistic, high confidence — re75
   was what cleaned it.) PASS if it trips on both.
2. **Specificity (A):** on experimental NSW the NC residual stays ≈ 0 (randomization) → ideally the
   guard does NOT trip from this mechanism. (The prior −0.074 small-n T-learner false-trip may persist
   for a different reason; report honestly — if A still false-trips, the small-sample issue is
   separate from the collinearity issue.)
3. **The honest limit (stated, not pass/fail):** this fix raises NC sensitivity *globally*, so it is
   validated ONLY on LaLonde and could increase false-positives on cases where the NC is legitimately
   correlated with a benign observed covariate. Therefore even a clean PASS = a **candidate fix / LEAD
   direction**, NOT a solved guard — promotion still needs synthetic re-validation (with NC-collinear
   covariates added to the DGP) + the other real RCTs.

## Verdict mapping
- If P1 PASS → the failure is the **collinearity mechanism, and a principled NC-aware adjustment
  restores detection on LaLonde** (candidate fix; LEAD-direction, not promotion).
- If P1 FAIL (still under-trips without re75) → the failure is **more fundamental** than collinearity,
  and the single-NC guard needs the proximal/double-NC machinery, not a covariate tweak.
- Either outcome is reported raw. No tuning beyond the single pre-specified re75-removal.
