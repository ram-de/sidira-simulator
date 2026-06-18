# Through-engine powered re-benchmark — the lever does NOT yet land in the engine (#342)

The standalone forecaster probe fixed the Hillstrom sign inversion (visit direction
accuracy 0.0→1.0) and certified heterogeneity (rank-ρ +0.42, gender-match +0.75).
This run drives the **production metric-elicitation seam** (`compose_metric_prompt`
+ `visit_elicitor.elicit_visit_decision`, with the deployed forecaster flag) over
the real Hillstrom panel — and the standalone win does **not** reproduce.

## Result (4 panel personas × 2 emails = 8 cells, k=6 agents/arm, both modes)

| mode | direction accuracy | mean visit lift |
|---|---|---|
| roleplay | 0.00 (0/8 cells positive) | −0.037 |
| **forecaster** | **0.12 (1/8)** | −0.029 |

RCT truth: every email RAISES visits (lift > 0). Roleplay is uniformly backwards
(the certified ad-aversion). Forecaster is *marginally* better and never worse per
cell, but it is still mostly flat/negative — most cells show treat ≈ control
(lifts of +0.000 / −0.017). The standalone probe's clean 1.0 direction accuracy is
**not** carried through the engine.

## Diagnosis — why the standalone win didn't transfer

The lever I validated standalone was more than a system-voice swap; the engine pass
omits the parts that made it work:

1. **The engine metric pass is BLINDED (by design, #221/§3b).** The treatment arm
   renders the proposed product *state* as a structural spec — it does **not** tell
   the agent "a promotional email is being sent." My standalone probe explicitly
   said "the retailer sends a promotional email vs a no-email holdout." A forecaster
   asked to predict visits for a blinded inbox-state it can barely tell changed will
   return treat ≈ control — exactly what we see. **Blinding (which protects the
   treatment/control delta from demand effects) is in direct tension with the
   forecaster needing to know the change is an ad campaign to apply marketing
   knowledge.**
2. **Coarse /10 allocation.** The metric pass elicits "of 10 trials, how many
   visits" → 0.1 granularity with many ties (lifts pile up at 0.000). The standalone
   probe elicited a percentage-point magnitude, which resolves the small real
   uplifts (~+0.07) that /10 rounds away.
3. **Generic GMM personas.** The panel personas are unnamed clusters ("LLM naming
   unavailable"); the standalone probe used rich segment descriptions ("customers
   who bought men's merchandise…"). Less audience signal to forecast from.

## What this means

- **The forecaster framing alone, dropped into the existing blinded /10 metric
  pass, is necessary but NOT sufficient.** The certified lift came from
  framing + change-legibility + magnitude elicitation + audience richness together.
- **Keep forecaster as the deployed default anyway.** Roleplay is 0/8 and provably
  backwards; forecaster is no worse on any cell and marginally better; with no
  customers there is no reason to default to the broken framing. This is not a
  rollback trigger — it is an incompleteness to close.
- **The through-engine re-benchmark did its job:** it disconfirmed the assumption
  that the standalone win would transfer for free, and localized exactly why.

## Next work (the real path to the lift in-product)

1. **Make the treatment legible to the forecaster without breaking blinding** — e.g.
   a neutral "what changed" descriptor in the metric pass (symmetric across arms),
   or a forecaster-mode decision_point that names the change class generically. This
   is the highest-leverage fix and the crux of the blinding-vs-legibility tension.
2. **Finer-grained elicitation** than /10 (a rate or pp estimate) so small real
   uplifts aren't rounded to ties.
3. **Richer audience conditioning** (segment-descriptive persona text).
4. Re-run THIS benchmark after each — it is now the gate for "did we actually move
   the engine," not just the prompt.

## Honest status

Forecaster is live as the default (the better of the two framings), but the
certified accuracy lift is **not yet realized through the production engine**. The
standalone certification stands; the engine integration is incomplete, and we now
know precisely what to fix. Magnitudes remain uncalibrated throughout.
