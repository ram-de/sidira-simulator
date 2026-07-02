# Method Bake-Off Wave 2 — Scorecard (predicted vs actual)

Sealed predictions sha256 `6fc83393f7ba60fb…` (frozen before any run; nothing tuned to match).

Truth: GOTV primary2006 = **positive** (+8.1pp) · Karlan gave = **positive** (small) · Orange churn = **positive/backfire** · streaming heterogeneous regime: casual=+ , power=−.

## gotv  (truth = positive)

| method | A | B_obs | B_hidden | verdict | pred-hits |
|---|---|---|---|---|---|
| naive_diff_in_means | ✓ +0.0815 | ✓ +0.1481 (pred✗) | ✓ +0.1481 (pred✗) | **LEAD** | 1/3 |
| t_learner | ✓ +0.0809 | ✓ +0.1088 | ✓ +0.1487 | **LEAD** | 3/3 |
| ipw | ✓ +0.0809 | ✓ +0.0823 | ✓ +0.1478 | **LEAD** | 3/3 |
| x_learner | ✓ +0.0795 | ✓ +0.0983 | ✓ +0.1492 | **LEAD** | 3/3 |
| dr_aipw | ✓ +0.0809 | ✓ +0.0973 | ✓ +0.1484 | **LEAD** | 3/3 |
| negative_control_guard | — | — | — (guard) | **LEAD** | 3/3 |

  guard cells A/B_obs/B_hidden = trust/trust/abstain

## karlan  (truth = positive)

| method | A | B_obs | B_hidden | verdict | pred-hits |
|---|---|---|---|---|---|
| naive_diff_in_means | ✓ +0.0042 | ✓ +0.0129 (pred✗) | ✓ +0.0129 (pred✗) | **LEAD** | 1/3 |
| t_learner | ✓ +0.0041 | ✗ -0.0080 (pred✗) | ✗ -0.0084 | **NULL** | 2/3 |
| ipw | ✓ +0.0041 | ✓ +0.0051 | ✓ +0.0050 (pred✗) | **LEAD** | 2/3 |
| x_learner | ✓ +0.0040 | ✓ +0.0008 | ✓ +0.0008 (pred✗) | **LEAD** | 2/3 |
| dr_aipw | ✓ +0.0042 | ✗ -0.0085 (pred✗) | ✗ -0.0089 | **NULL** | 2/3 |
| negative_control_guard | — | — | — (guard) | **NULL** | 1/3 |

  guard cells A/B_obs/B_hidden = abstain (pred✗)/abstain (pred✗)/abstain

## orange  (truth = positive)

| method | A | B_obs | B_hidden | verdict | pred-hits |
|---|---|---|---|---|---|
| naive_diff_in_means | ✗ -0.0028 | ✓ +0.0006 (pred✗) | ✓ +0.0006 (pred✗) | **NULL** | 1/3 |
| t_learner | ✗ -0.0024 (pred✗) | ✗ -0.0225 (pred✗) | ✗ -0.0227 | **NULL** | 1/3 |
| ipw | ✗ -0.0023 (pred✗) | ✗ -0.0093 | ✗ -0.0089 | **NULL** | 2/3 |
| x_learner | ✗ -0.0024 (pred✗) | ✗ -0.0130 (pred✗) | ✗ -0.0131 | **NULL** | 1/3 |
| dr_aipw | ✗ -0.0025 (pred✗) | ✗ -0.0250 (pred✗) | ✗ -0.0248 | **NULL** | 1/3 |
| negative_control_guard | — | — | — (guard) | **NULL** | 1/3 |

  guard cells A/B_obs/B_hidden = abstain (pred✗)/abstain (pred✗)/abstain

## Karlan match-ratio 3:1 vs 1:1  (truth = NULL)

Band |est|<0.005. All five methods call ~null: **True** (pred = recover_null). Estimates: naive=+0.0020, t=+0.0021, ipw=+0.0020, x=+0.0022, dr=+0.0021.
→ The canonical counter-intuitive NULL (bigger match ratio buys ~nothing) was **recovered**; no method imposed a positive lift.

## Heterogeneity (synthetic streaming) — the headline test

Per-segment sign: TRUE vs plain-ATE vs X-learner CATE vs T-learner CATE. **Flag = segment where plain ATE masks a flip that CATE recovers.**

### v2/dataset_06  (continuous; global naive ATE = +5.948 → positive)

| segment | n | TRUE | plain ATE | naive-within | X-learner CATE | T-learner CATE | masked-flip? |
|---|---|---|---|---|---|---|---|
| casual_low_usage | 8700 | positive | positive (✓) | positive (✓) | positive (✓) | positive (✓) | no |
| power_high_usage | 8362 | negative | positive (✗) | positive (✗) | negative (✓) | negative (✓) | **YES — ATE masks, CATE recovers** |

plan_tier negative-control segmentation (no by-construction heterogeneity): tier0=positive, tier1=positive, tier2=positive → no flip along the non-modifier axis (correct).
NC-guard on this regime: trips=False (confounding observed → trust, correct).

### v3/dataset_09  (continuous; global naive ATE = +5.919 → positive)

| segment | n | TRUE | plain ATE | naive-within | X-learner CATE | T-learner CATE | masked-flip? |
|---|---|---|---|---|---|---|---|
| casual_low_usage | 7839 | positive | positive (✓) | positive (✓) | positive (✓) | positive (✓) | no |
| power_high_usage | 7740 | negative | positive (✗) | positive (✗) | negative (✓) | negative (✓) | **YES — ATE masks, CATE recovers** |

plan_tier negative-control segmentation (no by-construction heterogeneity): tier0=positive, tier1=positive, tier2=positive → no flip along the non-modifier axis (correct).
NC-guard on this regime: trips=False (confounding observed → trust, correct).

## Streaming NC-guard sweep (all 20 datasets)

Unobserved-confounding regimes caught (abstain): **4/4**. False-alarm abstentions on observed/clean regimes: 3/16 (all on true-null or tiny sign-flip regimes — the documented 'defers sub-bias effects' cost).


**Prediction accuracy: 44 hits / 65 scored cells.**

### Honest misses (NOT re-tuned)
- **Naive 'recovered' B_obs/B_hidden on GOTV & Karlan** where I predicted a flip: the injected selection ran in the SAME direction as the true positive effect, so confounding inflated the naive estimate toward the truth instead of flipping it. A design artifact of injection direction, not naive robustness.
- **Orange backfire NOT recovered by any method, even in clean A.** My optimistic prediction (causal adjusters reveal the positive backfire) was wrong: naive is already negative (~-0.003) and every adjuster moved MORE negative. The methods imposed the intuitive 'retention outreach reduces churn' reading. The guard abstained throughout — protective (it refused to ship the confident wrong sign) but not a recovery.
- **Karlan guard over-abstains** (abstains in A & B_obs, predicted trust): the true effect (~+0.4pp) is smaller than the NC residual, so the ratio rule cannot distinguish it from confounding — the documented cost of honestly deferring sub-bias effects.
