# Path A — expert-forecaster elicitation wired into the engine (#342)

The benchmark-validated lever (expert-forecaster vs reader-roleplay elicitation)
is now implemented in the live simulation engine, behind a default-off flag.

## The change
- `runtime_config.resolve_elicitation_mode()` → `roleplay` (default) | `forecaster`,
  from `SIDIRA_ELICITATION_MODE` (mirrors `SIDIRA_STIMULUS_AFFORDANCE`).
- `prompt_composer.compose_metric_prompt(..., elicitation_mode=None)` → resolves the
  flag; `forecaster` swaps the metric-pass framing from first-person introspective
  roleplay to an expert forecasting how the described **audience** behaves
  (3rd-person, population-grounded), bridging the /10 allocation to a population
  forecast. Blinding, option set, and the #90 paired control/treatment invariant
  are preserved — only the framing voice changes, symmetrically across arms.
- **Default OFF = byte-identical** to today (asserted by test). The env flag flips
  the LIVE runner with no call-site change (`simulation_runner` calls
  `compose_metric_prompt` without the param → reads the env).

## Verification
- 585 related tests pass; a new test asserts default == roleplay (byte-identical)
  and that forecaster reframes correctly while preserving the structural spec.
- **Through-engine smoke** (`through_engine_smoke.py`, real Sonnet client, real
  Hillstrom email case, production `elicit_visit_decision`): on the Mens-E-Mail →
  visit case (RCT truth: email RAISES visits), the flag flips the sign in the real
  pipeline — roleplay mean lift −0.00 (1/3 personas positive) → forecaster +0.033
  (2/3 positive). Small/coarse (3 personas, 0–10 allocation) so it is a *wiring
  confirmation*, not a powered measurement.

## What remains (the powered through-engine re-benchmark)
The rigorous proof of the lever is the standalone, pre-registered, powered result
(Hillstrom visit direction accuracy 0.0→1.0; who-responds-more heterogeneity
certified ρ +0.42 p=0.01, gender-match +0.75 p=0.0004; Upworthy signal recovered).
The remaining step is to re-run the **certified powered benchmark through the
engine** with `SIDIRA_ELICITATION_MODE=forecaster` (8 segment-cases × 50 agents ×
both outcomes — prod-box scale, the harness that produced the §4 certified roleplay
baseline) to quantify the product-level improvement apples-to-apples. The engine is
ready for that run; default-off means it ships safely before then.
