# End-to-end flag-ON validation — comparative wiring confirmed through the full runner (#342)

The comparative-delta primitive (0.12→1.00 direction through the engine) and the
aggregation delegation (unit-tested) were proven separately. This validates the
whole chain through the **real `SimulationRunner.run`** with the production flag on.

## Setup
Real `SimulationRunner.run` (real Sonnet client, LocalArtifactStore), Hillstrom
panel, the Mens-E-Mail → visit case, **A/B mode (treatment_fraction=0.5)**,
population_size=8, `SIDIRA_ELICITATION_MODE=forecaster`,
`SIDIRA_METRIC_COMPARATIVE=1`. Engine hypothesis built like the benchmark harness
(`metric_name="visit"` + arm-neutral `decision_point`, re-validated).

## Result

| check | result |
|---|---|
| (a) treatment records with `metric_comparative_delta` set | **8 / 8** (deltas 0.08–0.12) |
| (b) production `aggregate_metric_lift` delegated to comparative aggregator | **True** |
| lift | **+10.0pp, 90% CI (8.5, 11.5), paired_n=8** |
| RCT truth (Mens email on visits) | positive (~+7 to +13pp) |

The full run loop elicited the comparative delta for every treatment agent, the
production aggregation correctly delegated, and the lift is **positive with a CI
clear of zero, matching the real experiment's direction and rough magnitude**. The
through-engine benchmark is GREEN end-to-end on direction.

## Setup bug found and fixed (not a wiring bug)
The first attempt showed 0/8 deltas. Cause: `build_hillstrom_case(metric_name=…)`
sets the *ground-truth* metric, not the engine task — the case's hypothesis carries
`metric_name=None`, so the engine correctly skipped the metric pass entirely (and
thus the comparative branch). Setting `metric_name`/`decision_point` on the engine
hypothesis (as `benchmark_runner` does) fixed it. This actually confirms the gate is
correct: no metric requested → no comparative elicitation.

## Honest limits
- **n=8, one case, one model.** Direction is green; this is not a powered run.
- **Heterogeneity not validated through the engine.** The deltas are clustered
  (0.08–0.12), so the who-responds-more ranking is not yet shown end-to-end (thin
  GMM personas — the richer-audience lever is still open).
- **Flag stays default-OFF.** This proves it WORKS when on; it does not flip the
  production default. Enabling it should follow a powered run + the heterogeneity
  check, and is a deliberate production-default decision.

## Status
The comparative-delta fix is: built → validated at the elicitation layer (1.00) →
unit-tested at the aggregation layer → wired into the production runner (flag-gated)
→ **now validated end-to-end through the real runner (flag on): +10pp, CI clear of
zero, matching the RCT.** The internal through-engine milestone is met for direction.
Remaining toward sellable: powered + heterogeneity through the engine, then the
customer backtest pilot.
