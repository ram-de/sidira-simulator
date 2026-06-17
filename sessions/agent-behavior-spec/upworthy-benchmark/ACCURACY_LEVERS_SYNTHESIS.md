# Accuracy levers — synthesis and ceiling (#342)

What raises a behavioral simulator's directional accuracy on Upworthy
headline-CTR? We tested a ladder of avenues, each pre-registered and scored
through the G0–G11 gate, ending on the supervised cross-fit calibrator the white
paper prescribes. All on the same 300 disjoint, pre-registered cases.

## The ladder (300 cases unless noted)

| approach | balanced SMR (90% LB) | Kendall τ_b (LB) | MCC | ECE | ΔU (LB) | verdict |
|---|---|---|---|---|---|---|
| reader-roleplay panel (iter2, n=150) | 0.379 | −0.022 | −0.247 | — | <0 | NO-GO |
| structural features only (no LLM) | 0.585 (0.546) | +0.094 (+0.030) | +0.182 | 0.044 | <0 | NO-GO |
| elicited — expert-forecaster (Sonnet) | 0.622 (0.576) | +0.155 (+0.090) | +0.245 | 0.066 | + (LB>0) | NO-GO |
| **combined — features + elicited, cross-fit** | 0.610 (0.566) | **+0.184 (+0.124)** | +0.222 | **0.019** | + (LB>0) | NO-GO |

## What moved accuracy (ranked by impact)

1. **Elicitation framing — the biggest lever.** Reader-roleplay ("would YOU
   click?") was NULL; expert-CTR-forecasting ("which gets higher CTR?", with brief
   reasoning) recovered a real, replicated signal (τ_b −0.02 → +0.21 pooled).
   This was the single largest gain and it cost nothing but a prompt change.
2. **Model capability — conditional on framing.** Sonnet shows the signal
   robustly; Groq's expert-forecaster arms are only weakly/inconsistently positive.
3. **Supervised cross-fit calibration — polish, not breakthrough.** Adding
   structural features + fitting on real CTR gives the best calibration (ECE
   0.066 → 0.019), best Brier-skill, and a small rank gain (τ_b +0.155 → +0.184),
   but does not clear any new GO bar.
4. **Structural features alone carry weak signal** (τ_b LB +0.030, MCC +0.182) —
   real but not enough on their own.

## What did NOT move it

- Persona panels / reader-roleplay (the original simulator framing): null, and
  personas only helped the capable model in the n=60 fluke that didn't replicate.
- A bigger model alone, without the framing change.

## The ceiling

The best configuration (combined cross-fit) is **real, replicated, well-calibrated
(ECE 0.019), and decision-useful (ΔU > 0)** — it would improve a PM's triage over
status quo, and it passes the classification (G5), calibration (G7-ECE), decision-
value (G8), leakage (G3), and credible-n (G0) gates. But it stays **NO-GO**: SMR
0.61 < 0.70, τ_b 0.18 < 0.30, tail recall 0.40 < 0.80. **Headline text alone does
not contain enough signal to reach decision-grade directional accuracy on
Upworthy CTR.** The gate correctly keeps the product confidence "uncalibrated" /
abstaining at the strict bar, while the underlying signal is genuinely above
chance.

## Recommendations

1. **Adopt expert-forecaster elicitation over reader-roleplay** as the default
   for copy/first-impression estimands — it is the cheap, confirmed accuracy lever.
2. **Keep the fitted cross-fit calibrator** — it makes the (modest) signal honest
   (ECE 0.019) and is the only thing producing ΔU>0 with a CI clear of zero.
3. **Do not claim decision-grade on headline-only inputs.** To break the ceiling
   you need either more input (article body, image, audience priors) or a
   different estimand. The next frontier is a *different dataset* (Hillstrom /
   CookieCats, already scaffolded) where the treatment carries more signal than a
   headline swap — not more squeezing of Upworthy headlines.

## Provenance

Pre-registrations: `PREREG_LEVERS*.json`, `PREREG_SUPERVISED.json` (+ .sha256).
Results: `accuracy_levers_result.json`, `accuracy_levers_confirm_result.json`,
`levers_pooled_sonnet.json`, `supervised_calibration_result.json`. All NO-GO;
all signals above-chance-but-sub-decision-grade; honest output = abstain.
