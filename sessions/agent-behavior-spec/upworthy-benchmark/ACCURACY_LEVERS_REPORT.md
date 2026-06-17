# Accuracy lever found: elicitation FORMAT moves the needle (#342)

**Pre-registered** (`PREREG_LEVERS.json`, integrity `e59bb29c6e924e20…`,
case-set hash `1e54565003e5a00b` — the **same 150 fresh cases as iter2**, so the
contrast with the reader-roleplay null is on identical data). Date: 2026-06-17.

## The finding

Every prior Upworthy run asked the model to **roleplay a reader** ("would YOU
click?"). Switching Sonnet to an **expert CTR-forecaster** framing — on the same
150 cases — turns the null into a positive (if weak) rank signal:

| arm | balanced SMR (90% LB) | Spearman ρ | Kendall τ_b (90% LB) | MCC | verdict |
|---|---|---|---|---|---|
| reader-roleplay, Sonnet panel (iter2) | 0.379 | −0.038 | −0.022 (−0.112) | −0.247 | NO-GO |
| **comparative + reasoning, Sonnet** | **0.594 (0.526)** | **+0.186** | **+0.133 (+0.044)** | +0.188 | NO-GO |
| **population-share, Sonnet** | 0.533 (0.466) | +0.174 | +0.118 (**+0.031**) | +0.066 | NO-GO |
| comparative + reasoning, Groq | 0.540 (0.473) | +0.064 | +0.051 (−0.058) | +0.081 | NO-GO |
| population-share, Groq | 0.540 (0.473) | +0.109 | +0.080 (−0.019) | +0.079 | NO-GO |

## Read

1. **Elicitation format is a real lever.** On identical data, expert-forecaster
   framing moved Sonnet from Kendall τ_b −0.022 (reader-roleplay) to **+0.133,
   90% LB +0.044 > 0** — a rank signal distinguishable from zero. The
   population-share arm agrees (τ_b LB +0.031 > 0). Reader-roleplay was leaving
   signal on the table.
2. **This is not the iter-1 false-positive pattern.** It is at credible-n (150),
   it was the pre-registered H1 (predicted ρ 0.10, observed +0.186), and **two
   independent Sonnet arms agree**. iter-1 was a single arm at n=60.
3. **Model tier still matters, conditional on format.** Groq's expert-forecaster
   arms are weakly positive but their τ_b lower bounds cross 0 — not distinguishable
   from chance. The lever is format × capable-model together.
4. **Still NO-GO.** τ_b 0.13 ≪ the G6 bar (0.30); SMR 0.59 < 0.70; ΔU/tail fail.
   This is a *weak, sub-decision-grade* signal — a direction to pursue, not a win.

## Next (disciplined): confirm before believing

One positive slice is not a result — the same discipline that refuted iter-1.
**Confirmation run, pre-registered, on a FRESH disjoint 150-case slice** (no
overlap with these 150 or the original 60): does Sonnet comparative hold τ_b 90%
LB > 0 and SMR LB > 0.5? If yes → the lever is real and worth scaling (more
cases, richer comparative prompts, ensembling). If it collapses → it was this
slice's noise.

Then, regardless: the **supervised avenue** (LLM feature-extraction + cross-fit
calibration on real CTR) is the white paper's actual thesis and the most likely
path to a *decision-grade* (not just above-chance) signal, because it learns the
mapping from outcomes instead of guessing zero-shot.

## Caveats

- Weak signal; CI lower bounds barely clear 0 on Kendall (Spearman/SMR are the
  stronger reads). Confirmation pending.
- Upworthy headline-CTR regime only; no transfer claim. Still NO-GO → the product
  confidence score stays "uncalibrated" for this estimand.
