# CONFIRMED: expert-forecaster elicitation is a real accuracy lever (#342)

**Pre-registered** (`PREREG_LEVERS_CONFIRM.json`, integrity `2b2972b09e3f5477…`,
case-set hash `b225c6f8d4da25a2` — a SECOND 150-case slice, disjoint from both
slice-1 and the original 60). The lever found on slice-1 replicated — and
strengthened. Date: 2026-06-17.

## Replication (slice-1 → confirm, disjoint)

| comparative/sonnet | slice-1 (n=150) | confirm (n=150) |
|---|---|---|
| balanced SMR (Wilson 90% LB) | 0.594 (0.526) | **0.652 (0.587)** |
| Spearman ρ | +0.186 | **+0.392** |
| Kendall τ_b (90% LB) | +0.133 (+0.044) | **+0.297 (+0.193)** |
| MCC | +0.188 | +0.303 |

Both slices independently satisfy the pre-registered H1 (SMR LB > 0.5 AND τ_b
LB > 0). `popshare/sonnet` replicated too (τ_b LB +0.031 → +0.062). This is the
**opposite** of the iter-1 false positive, which collapsed on replication.

## Pooled estimate (300 disjoint, pre-registered cases)

| arm | balanced SMR (LB) | Kendall τ_b (LB) | MCC (LB) | ECE | ΔU (LB) | verdict |
|---|---|---|---|---|---|---|
| **comparative/sonnet** | **0.626 (0.580)** | **+0.208 (+0.139)** | **+0.252 (+0.160)** | 0.030 | +>0 (>0) | NO-GO |
| popshare/sonnet | 0.575 (0.533) | +0.146 (+0.081) | +0.154 (+0.061) | 0.070 | ~0 | NO-GO |

At n=300 the comparative/sonnet arm clears **11 of the gates**, including the
credible-n floors (G0: ≥150), leakage (G3), **classification (G5: MCC LB > 0)**,
**calibration (G7: ECE 0.030 ≤ 0.08)**, and the **primary decision-value gate
(G8: ΔU 90% LB > 0)**.

It remains **NO-GO** because three strict GO bars are unmet:
- G4 direction: SMR 0.626 < 0.70 (though Wilson LB 0.580 is comfortably above chance)
- G6 ranking: τ_b 0.208 < 0.30
- G9 tail safety: top-decile winner recall 0.57 < 0.80

## What this means

1. **Elicitation framing is the single biggest lever found.** Reader-roleplay
   ("would YOU click?") was NULL across every prior run. Expert-CTR-forecasting
   ("which gets higher CTR?", with brief reasoning), with a capable model,
   recovers a **real, replicated, well-calibrated, decision-useful** directional
   signal on the identical population — confirmed across 300 pre-registered
   disjoint cases with every CI lower bound clear of chance.
2. **It is decision-useful but not yet decision-grade.** ΔU > 0 means it would
   improve a PM's triage over status quo, and it is honestly calibrated (ECE
   0.03). But it does not clear the strict direction/rank/tail bars, so the gate
   correctly returns NO-GO → the product confidence score still reads
   "uncalibrated" and the system abstains rather than over-claiming.
3. **Model tier matters conditional on framing.** Groq's expert-forecaster arms
   are weakly positive (popshare/groq τ_b LB +0.084 on the confirm slice) but not
   robust; Sonnet is.

## Next avenue (toward decision-grade)

The confirmed signal sits just below the GO bars. The queued **supervised lever**
— LLM feature-extraction (curiosity gap, specificity, emotion, length, numbers,
question form) + the elicited comparative signal, fed to a **cross-fit calibrator
trained on real CTR** — is the path most likely to push SMR/τ_b/tail over the
line, because it learns the mapping from outcomes instead of relying on zero-shot
judgment alone. That is the white paper's core thesis, now with a confirmed
zero-shot signal to build on.

## Caveats

- Upworthy headline-CTR regime only; no transfer claim to other change classes.
- Still NO-GO: above chance and decision-useful (ΔU>0) ≠ decision-grade. The
  honest product output for this estimand remains "uncalibrated / abstain".
