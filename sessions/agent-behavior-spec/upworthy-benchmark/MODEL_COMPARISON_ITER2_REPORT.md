# Iter 2 — the n=60 Sonnet signal did NOT replicate. Ceiling is model-robust. (#342)

**Pre-registered** (`PREREG_MODELCMP_ITER2.json`, integrity `dd2a21fa3ec3741f…`,
case-set hash `1e54565003e5a00b`) before the run. Same light blinded elicitation
as iter 1, on a **fresh, disjoint slice of 150 representable cases** (canonical
baseline=variant-0 pairing, no overlap with the original 60-case tests), 76 pos /
74 neg. 0 dropped (every vote parsed). Date: 2026-06-17.

## Headline: replication failure

The iter-1 (n=60) Sonnet-panel result that looked like a partial signal **did not
replicate** on the larger fresh slice — it regressed past chance:

| Sonnet · panel | iter1 (n=60) | iter2 (n=150, fresh) |
|---|---|---|
| balanced SMR (Wilson 90% LB) | 0.663 (0.561) | **0.379 (0.317)** |
| 3-class MCC (90% LB) | +0.328 (+0.134) | **−0.247 (−0.376)** |
| Spearman ρ | +0.187 | **−0.038** |
| Kendall τ_b (90% LB) | +0.089 (−0.030) | −0.022 (−0.112) |
| Brier-skill | +0.072 | −0.080 |
| tail-winner recall | 0.17 | 0.13 |

## Full iter-2 panel (all NO-GO)

| model · arm | balanced SMR (LB) | Spearman ρ | MCC | verdict |
|---|---|---|---|---|
| groq · panel | 0.419 (0.356) | +0.038 | −0.162 | NO-GO |
| groq · no-persona | 0.433 (0.369) | +0.131 | −0.133 | NO-GO |
| sonnet · panel | 0.379 (0.317) | −0.038 | −0.247 | NO-GO |
| sonnet · no-persona | 0.413 (0.349) | +0.044 | −0.174 | NO-GO |

No arm's balanced-SMR Wilson 90% lower bound reaches 0.5; no MCC LB clears 0; no
Spearman ρ is distinguishable from 0. Nothing tracks real CTR.

## Interpretation

1. **The iter-1 Sonnet signal was a small-sample false positive.** This is the
   third time this exact failure mode has appeared on Upworthy (the de-attenuation
   probe ρ=+0.386 at n=20; the iter-1 Sonnet SMR 0.663 at n=60), and the third
   time **pre-registered replication on a disjoint set killed it.** n=60 is the
   hard floor precisely because point estimates there are noisy enough to look
   like signal; the credible-n bars (100 for SMR, 150 for MCC) exist for this.
2. **The rank-ceiling is model-robust at light elicitation.** A stronger model
   (Sonnet 4-6) does not lift Upworthy headline-CTR ranking above chance any more
   than Groq llama-3.3-70b does. The ceiling is not an artifact of model tier.
3. **The $275 heavy 200-agent Sonnet pass is not justified.** The cheap light
   pass already answers #342's question: model tier is not the lever. Spending
   $275 to test the heavy *architecture* would only make sense as a separate,
   explicitly-motivated hypothesis — not to chase this (now-refuted) signal.

## Bottom line for the whitepaper

On a pre-registered, replicated, disjoint backtest, an LLM behavioral simulator
**does not rank real Upworthy headline CTR above chance** — across two model tiers
and with/without a persona panel. This is exactly the regime the ratified gate is
built to handle honestly: **NO-GO → the confidence score stays "uncalibrated"**,
the system abstains, and the live experiment remains ground truth. The value of
the methodology is on display: pre-registration + credible-n + the full G0–G11
panel converted a tempting false positive into a correct null.

## Honest caveats

- Light elicitation ≠ the production heavy panel; this isolates the model/persona
  lever cleanly but does not exercise the full pipeline.
- This is the Upworthy headline-CTR estimand only. Other change classes / datasets
  (Hillstrom, CookieCats) are separate questions with their own backtests.
