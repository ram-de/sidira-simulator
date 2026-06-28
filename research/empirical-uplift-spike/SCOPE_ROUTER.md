# Scope — the feature-expressibility ROUTER (productizing the survivor)

## Why
The spikes settled it: the **empirical/causal route** is the only mechanism that beats
chance, validated on two real datasets (Cookie Cats, Hillstrom). LLM-prompting (persona /
no-persona / council) sits at/below chance. So the product move is not "replace the LLM"
— it's a **router** that sends each hypothesis to the engine that can actually answer it,
and labels confidence honestly. This carves out a *provably accurate, sellable slice* now.

## The decision
For a customer hypothesis + their connected data, decide EMPIRICAL vs LLM by one question:
**can the change be expressed as a measurable contrast (treatment T → outcome Y) whose
variation already exists in the data, with enough support to estimate it?**

```
hypothesis + data schema
        │
        ▼
 (1) MAP  ── LLM-assisted: hypothesis → {treatment T, contrast, outcome Y, covariates X}
        │     (LLM as TRANSLATOR, not predictor; human-confirmable)
        ▼
 (2) SUPPORT CHECK ── pure data/stats, no LLM:
        • T exists & varies in the data?        • Y measured?
        • both arms have ≥ N samples?           • covariate overlap / positivity ok?
        ▼
   supportable? ──── yes ──► EMPIRICAL: causal_estimator → ATE, sign, CI, overlap warnings
        │                                  (provably accurate; the DashPass case)
        └──── no ──► LLM ENGINE (current): directional, FLAGGED low-confidence
                                  (the novel-feature case)
```

## Build pieces
1. **`causal_estimator.py` (FOUNDATION — build first).** Route-agnostic core extracted +
   generalized from `realdata_uplift.py` / `realdata_hillstrom.py`:
   `estimate(df, treatment, outcome, covariates) -> {naive, t_learner, ipw, overlap
   diagnostics, naive_vs_adjusted_gap}` + `support_check(...) -> {supportable, reasons}`.
   Validated against both real datasets. No LLM, no customer dependency — buildable now.
2. **Hypothesis→spec mapper.** NL hypothesis + schema → {T, contrast, Y, X}. LLM-assisted,
   returns a structured, user-confirmable spec. (Reuses the existing chat client.)
3. **Router + pre-flight surface.** Glue: run mapper → support_check → route. Extends the
   existing **answerability pre-flight (epic #309)** with an "empirically estimable from
   your data?" branch + a card showing route taken, why, and confidence.
4. **Wire empirical output into the result + the #222 calibrator slot.** The empirical
   estimate is a natural ground-truth anchor for the `conversion_calibrator` (currently a
   no-op IdentityCalibrator).

## Honesty rails
- Empirical estimate ALWAYS ships with overlap/positivity diagnostics + the naive-vs-
  adjusted gap (big gap = strong confounding correction = read carefully).
- Empirical only claims the slice it can support; everything else is LLM + low-confidence
  label. Never silently treat an LLM directional guess as if it were data.
- Off-support / novel changes (spike S2): empirical must ABSTAIN, not extrapolate.

## Order
1. `causal_estimator.py` foundation (this PR). → 2. mapper → 3. router/pre-flight (extends
   #309) → 4. calibrator wiring. Pieces 2–4 are follow-on PRs into the product.
```
