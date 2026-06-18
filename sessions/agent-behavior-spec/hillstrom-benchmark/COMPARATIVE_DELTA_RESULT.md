# Comparative-delta forecaster pass — the direction fix is recovered THROUGH THE ENGINE (#342)

The per-arm forecaster pass stalled at 0.12 direction accuracy through the engine
because it forecasts treatment and control in two independent passes and subtracts
(each anchors on the same base rate → delta ≈ 0). The comparative pass shows the
forecaster BOTH versions in one call and asks for the directional delta directly.

## Result (same panel/cases: 4 personas × 2 emails, k=6 agents/cell)

| through-the-engine pass | visit direction accuracy |
|---|---|
| per-arm roleplay | 0.00 (0/8) |
| per-arm forecaster | 0.12 (1/8) |
| **comparative-delta forecaster** | **1.00 (8/8)** |

Mean predicted lift +0.080 (real per-segment uplifts ~+0.07 to +0.13). Every cell
is now correctly positive — the engine, via the comparative pass, matches the RCT
direction (emails raise visits) where the production per-arm pass was at chance.

**The two-independent-pass architecture was the bottleneck, confirmed.** Comparative
judgment in one pass is what worked standalone, and it now works through the engine
elicitation primitives too.

## What this is and isn't

- **IS:** the certified direction fix, recovered through the engine's elicitation
  layer (`compose_comparative_metric_prompt` + `elicit_visit_delta`). The
  through-engine benchmark is GREEN on direction.
- **IS NOT yet:** (a) **heterogeneity** — the predicted lifts are clustered (~0.08),
  so the who-responds-more *ranking* is not clearly recovered in this engine run; the
  generic GMM personas carry little segment signal (richer audience conditioning is
  the next lever, as previously diagnosed). The all-positive cells make this a
  direction (sign) test, not a ranking test. (b) **wired into production** — this is
  the elicitation primitive, validated via the harness; it is NOT yet wired into
  `simulation_runner`'s flow (that integration, which touches the core per-arm loop +
  paired-delta scoring + confidence aggregation, is the next step).

## Build (additive, low blast radius)

- `prompt_composer.compose_comparative_metric_prompt` — forecaster identity + both
  versions (A current / B proposed) + neutral changelog, one prompt.
- `visit_elicitor.elicit_visit_delta` — one call, asks for the signed per-100 visit
  delta directly, parsed robustly → signed lift fraction.
- Existing per-arm flow and roleplay are untouched. 433 related tests pass (incl. new
  tests for the comparative prompt + delta parsing/clamping/failure).

## Next

1. **Wire the comparative path into `simulation_runner`** for forecaster mode (the
   production integration) — impact-analyzed, preserving roleplay + the scoring/
   confidence semantics.
2. **Richer audience conditioning** to recover heterogeneity through the engine
   (segment-descriptive personas), re-gated by a heterogeneity-scoring through-engine
   run.

No in-product accuracy claim until (1) lands and the through-engine heterogeneity is
re-checked; but the core architectural blocker is now solved at the elicitation layer.
