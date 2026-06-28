# Pre-registration — iteration 5: the true-null guard (effect-vs-residual ratio)

**Sealed before running** (sha256 committed alongside).

## The open gap (iter0-iter4)
The negative-control guard catches HIDDEN confounding but not a **true-null** estimator residual
on *observed* confounding: when the real effect is 0 but adjustment is imperfect, the estimator
reports a small positive (e.g. iter0/iter2 dataset_03: +0.016) that crosses the null band, and
the negative control — sharing the same observed confounding — shows a similarly small residual
(below the 0.05 floor), so it does not trip. The estimate is confidently, wrongly "treatment".

## The idea under test
A negative control that shares the confounding **measures the bias magnitude**. So only trust the
main sign when the main effect is meaningfully LARGER than that revealed bias:
**trust sign iff `|main_effect| > RATIO · |neg_control_residual|`** (RATIO = 1.5), else abstain.
Intuition: if the real effect isn't bigger than the confounding bias, you genuinely cannot tell
signal from bias — abstain and route to LLM.

## Design (self-blind, fresh seed; frozen estimator)
8 datasets. Observed confounder `a` is a NONLINEAR function of the covariates, and the estimator
adjusts with the RAW (linear) covariates — so adjustment is imperfect and leaks residual (this is
what produces the true-null false positive). Negative controls share `a`, true effect 0. Regimes:
- **null** (×2): true effect 0, observed confounding → want ABSTAIN.
- **clear_real** (×3): large true effect (clean RCT and/or confounded) → want TRUST correct sign.
- **borderline** (×3): small true effect comparable to the bias → expected DEFER (see P3).

## Falsifiable predictions
1. **P1:** the ratio rule ABSTAINS on both true-null cases (fixes the open gap).
2. **P2:** the ratio rule does NOT over-abstain on clear_real cases — it trusts the correct sign
   on every large effect (a guard that abstains on obvious signal is useless).
3. **P3 (honest, pre-registered):** on borderline small-real effects the rule will DEFER (abstain).
   That is acceptable, honest behaviour (route to LLM), NOT counted as error — but measured and
   reported as the cost (an effect smaller than the confounding bias is genuinely unidentifiable).

## Decision rule
- P1 PASS and P2 PASS → **LEAD (MECH-ONLY ceiling)** — the ratio rule closes the true-null gap for
  decidable cases; borderline effects are honestly deferred to the LLM path. Add to the guard.
- P1 fails (still calls true-null "treatment") → **NULL** — ratio rule doesn't help.
- P2 fails (abstains on clear real effects) → **NULL** — too aggressive, would gut the empirical route.
- Synthetic ⇒ ceiling MECH-ONLY/LEAD; never PROMOTED without real microdata.
