# Model-comparison probe — does a stronger model break the Upworthy rank-ceiling? (#342)

**Pre-registered** (`PREREG_MODELCMP.json`, integrity
`892264577323889f…`, case-set hash `f9db8c1fb90c68b1`) before the run.
Light, blinded, order-randomized clickability elicitation on the **identical 60
cases** as the committed Groq confirming run. Controlled *light-elicitation* arm
— NOT the heavy 200-agent persona panel — so it isolates the model effect cheaply
(actual cost ≈ $1). Scored through the G0–G11 gate. Date: 2026-06-17.

## Result

| model · arm | Spearman ρ | balanced SMR (90% LB) | 3-class MCC (90% LB) | Brier-skill | verdict |
|---|---|---|---|---|---|
| groq · panel (k=8) | +0.010 | 0.493 (0.396) | −0.014 | −0.010 | NO-GO |
| groq · no-persona | +0.005 | 0.475 (0.380) | −0.050 | −0.041 | NO-GO |
| **sonnet · panel (k=8)** | **+0.187** | **0.663 (0.561)** | **+0.328 (+0.134)** | **+0.072** | NO-GO |
| sonnet · no-persona | +0.041 | 0.487 (0.396) | −0.029 | −0.078 | NO-GO |

## Findings

1. **Groq replicates the null under light elicitation** (panel ρ +0.010,
   no-persona +0.005). The earlier heavy-panel null was not an artifact of the
   200-agent architecture — Groq `llama-3.3-70b` simply does not rank Upworthy
   CTR above chance, heavy or light.

2. **Sonnet partially breaks the ceiling — on direction and classification, not
   rank.** Sonnet · panel:
   - balanced SMR **0.663, Wilson 90% LB 0.561 > 0.5** → direction accuracy is
     significantly above chance.
   - 3-class MCC **+0.328, bootstrap 90% LB +0.134 > 0** → **G5 passes**: it
     classifies pos/flat/neg above the best non-LLM baseline with a CI clear of
     zero, and Brier-skill is **positive** (+0.072) → it genuinely discriminates.
   - But Kendall τ_b +0.089 (LB crosses 0), ΔU 90% LB −12, tail-winner recall
     0.17 → it fails the decision-grade bars. Correct verdict: **NO-GO**.

3. **Personas matter — but only for the capable model.** Sonnet · panel (SMR
   0.663, MCC +0.328) vastly outperforms Sonnet · no-persona (SMR 0.487, MCC
   −0.029, at chance). For Groq, personas don't help (both arms ≈ chance). This
   is direct G11-style evidence that the persona panel adds predictive value —
   conditional on a model strong enough to use it.

4. **Pre-registration held.** Predicted vs observed Spearman: groq_panel
   +0.00→+0.010, groq_no_persona +0.00→+0.005, sonnet_panel +0.10→**+0.187**
   (signal stronger than predicted), sonnet_no_persona +0.05→+0.041. H1 (Sonnet
   panel > Groq panel) confirmed.

## Decision (per the pre-registered rule)

Sonnet · panel **exceeds Groq · panel** and shows a real **direction** signal
(SMR LB > 0.5) and **classification** signal (MCC LB > 0) — but it is
**under-powered at n=60** (G0 needs ≥100 for the SMR gate, ≥150 for MCC) and
fails the rank / decision bars. This is exactly the "worth a larger pass" outcome
the prereg anticipated.

**Next (cheap, local, pre-registered):** re-run Sonnet · panel + Groq control on
a larger **fresh, disjoint** slice (~150 representable cases) to tighten the CIs
and see how many gates clear at credible-n. The expensive heavy 200-agent Sonnet
pass (~$275, prod box) is **not yet justified** — the light probe already shows
the signal is real but sub-decision-grade; spend the $275 only if the larger
light pass holds SMR ≥ ~0.66 with a tight CI and the heavy architecture is the
specific hypothesis under test.

## Honest caveats

- Light elicitation ≠ the production heavy panel; this isolates the model/persona
  effect, it does not certify the product pipeline.
- Upworthy is the text/headline best-case regime; a signal here does not transfer
  to SaaS feature decisions (the gate keeps those "uncalibrated").
- n=60 is the hard floor, not the credible-n. No GO is claimed for any arm.
