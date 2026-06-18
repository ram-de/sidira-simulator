# Legibility fix tested — necessary but NOT sufficient; the bottleneck is the two-pass architecture (#342)

Hypothesis: the standalone win didn't transfer because the blinded metric pass left
the treatment illegible to the forecaster. Fix: in forecaster mode, append a
neutral "## What is changing" descriptor (typed changelog, no valence) to the
treatment pass; `blinded` stays True; roleplay untouched.

## Result — no movement

Same through-engine benchmark (4 personas × 2 emails, k=6), before vs after the
legibility change:

| forecaster direction accuracy | mean visit lift |
|---|---|
| before legibility: 0.12 (1/8) | −0.029 |
| **after legibility: 0.12 (1/8)** | −0.031 |

Naming the change did **not** move it. Most cells are still `+0.000` (treatment
forecast == control forecast). Honest conclusion: **legibility is necessary but not
sufficient.**

## Sharpened diagnosis — the two-independent-pass architecture is the real bottleneck

The engine elicits the metric in **two separate passes** — forecast "of 10 users,
how many visit?" for the treatment state, then *independently* for the control
state — and subtracts. Each pass anchors on the same base rate, so even when the
treatment pass is told what changed, the model returns the same ~0.18 it returns
for control → the delta collapses to 0. The `+0.000` cells are this exactly.

The standalone probe (which hit 1.0 direction accuracy) did **not** do this. It
asked for the **delta directly in one comparative pass**: "by how many percentage
points does *this email* change visits versus a no-email holdout?" Comparative
judgment is answerable; two independent absolute forecasts subtracted are not (the
real ±7pp signal is smaller than the model's per-pass anchoring noise, and the /10
allocation rounds it away).

## The real lever (next, architectural)

**Comparative / delta elicitation in forecaster mode:** one pass that shows the
forecaster both the current and proposed versions and asks for the *directional
difference* (and rough magnitude), instead of two independent absolute passes
subtracted. This matches what worked standalone and is a change to the metric-pass
*flow* (simulation_runner runs per-arm passes today), not a prompt tweak — so it
warrants a designed change, not a quick edit.

The /10 allocation granularity and generic GMM personas are secondary levers once
the comparative pass exists.

## Status of the legibility change

Kept (it is conceptually correct — a forecaster should know what it forecasts —
harmless, roleplay-untouched, and a prerequisite for the comparative pass), but it
does **not** realize the lift on its own. No in-product accuracy claim. The
through-engine benchmark stays red until the comparative-delta pass lands.
