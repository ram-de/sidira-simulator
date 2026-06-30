# PREREG — re-validate the NC-collinearity fix (synthetic + corpus RCTs)

Sealed before run. The LaLonde fix (rule: *do not adjust a negative control on a covariate
near-collinear with it*) restored detection on ONE real benchmark. This promotes-or-kills it:
**Part A** = the decisive synthetic test (does the fix restore detection WITHOUT wrecking
specificity, on a DGP that contains the collinearity structure?); **Part B** = breadth on real
clean RCTs (does the empirical route recover the published sign and the guard avoid false alarms?).

The fix is operationalized as a frozen rule: when computing the NC residual, drop any covariate with
**|corr(covariate, NC)| > 0.8** from the NC's adjustment set (it stays in the main outcome/propensity
model). Threshold 0.8 is fixed now and will NOT be tuned.

---

## Part A — synthetic re-validation (the decisive test)

**DGP with the LaLonde structure.** Latent confounder U. An observed covariate `X_c` and the
negative-control outcome `W` are BOTH strong proxies of U (so `corr(X_c, W)` is high — the re75/re74
twin structure). Treatment propensity = sigmoid(gamma·U). Main outcome Y has true signed effect tau
and is confounded by U, but `X_c` cleans Y's confounding only PARTIALLY (differential cleaning: X_c
proxies W better than it proxies Y's confounding path — the re74-adjacent vs re78-distal asymmetry).
Grid over the differential-cleaning strength, gamma, tau (incl. tau=0), and a **collinearity level**
(corr(X_c,W) ∈ {0.5, 0.8, 0.95}). Known ground-truth sign per cell. n≈8000, ≥20 seeds/cell.

Three guards compared on every cell: **OLD** (NC adjusted on all covariates incl. X_c) · **FIXED**
(NC adjusted on covariates except those |corr|>0.8 with NC) · **RAW** (NC unadjusted; sensitivity
upper bound).

### Pre-registered predictions (sealed)
1. **Reproduce the failure:** in the high-collinearity + confounded cells, the OLD guard
   **under-trips** (misses real confounding) materially more than the FIXED guard. Bet: PASS — this
   confirms the LaLonde mechanism reproduces synthetically (and that the synthetic suite previously
   missed it because it had no NC-collinear covariate).
2. **Fix restores detection:** in confounded cells the FIXED guard's trip rate ≥ 0.80 where the OLD
   guard missed. Bet: PASS.
3. **SPECIFICITY PRESERVED (the decisive one):** on TRUE-NULL cells (tau=0, no unobserved
   confounding) that STILL contain the collinear X_c, the FIXED guard's false-trip rate is **≤ 0.10**
   (i.e. dropping the collinear covariate from the NC adjustment does NOT manufacture false alarms
   when there is nothing to detect). Honest lean: **UNCERTAIN — this is the real risk.** If the FIXED
   guard false-trips on benign true-nulls, the fix trades too much specificity and the adjust-vs-raw
   tension wins → the single-NC guard needs the proximal/double-NC route instead of a covariate rule.

### Verdict mapping (Part A)
- **Fix → LEAD-confirmed** if 1 AND 2 AND 3 all hold (detection restored, specificity kept).
- **Fix → NULL / route-to-proximal** if 3 FAILS (specificity sacrificed) — the honest "the covariate
  rule is not enough" outcome.

---

## Part B — corpus RCT breadth (real clean RCTs)

Acquire as many of the corpus-manifest turnkey RCTs as load cleanly WITHOUT rabbit-holing (target
≥4): Hillstrom (have), Karlan-List 2007, Gerber-Green-Larimer 2008, Orange-Belgium (OpenML 45580),
Information-R, Bertrand 2010. These are RANDOMIZED → no confounding → a SPECIFICITY + sign-recovery
test. For each: run the empirical estimate + the FIXED guard with a plausible pre-treatment NC.

### Pre-registered predictions (sealed)
4. **Sign recovery:** on each clean RCT the empirical (adjusted) estimate recovers the PUBLISHED
   directional sign. Bet: PASS on the clear-effect ones; the counter-intuitive NULLs (Karlan-List
   3:1-vs-1:1) may legitimately be ~null — report sign + CI, don't force it.
5. **No false alarm:** the FIXED guard does NOT trip on these randomized datasets (NC residual ≈ 0
   because randomization balances the NC). Bet: PASS — and if the FIXED guard false-trips on a clean
   real RCT, that is direct real-data evidence against prediction 3's specificity, reported as such.

## Honesty rails
- Part A is the gate; Part B is breadth. A fix that passes A but false-trips a real RCT in B is NOT
  promoted.
- "LEAD-confirmed" here still means synthetic + LaLonde + a few RCTs — NOT a deployed instrument.
  Promotion to PROMOTED needs naturally-confounded real breadth (IHDP/ACIC + more) we don't yet have.
- One scored run each; report raw, including any refuted prediction. Threshold 0.8 frozen.
