---
type: session
domain: metric-elicitation-siblings
status: active
started: 2026-06-15
owner: ram-de
---

# Metric elicitation siblings — generalize per-metric outcome elicitation

## Goal

Extend the per-metric outcome elicitation feature (agent-behavior-spec §3a,
#221) BEYOND its original conversion-only form into a metric **registry**, and
add the `retention` metric as the first sibling. The registry replaces every
inline `if metric_name == "conversion"` branch across the schema validator, the
runner, and the scorer, so a new metric routes end-to-end by registering a
descriptor — no edits to the dispatch sites.

## Tickets

- **#275 (this)** — registry + the `retention` metric.
- **#276 (next)** — CTR metric, registered the same way (not yet wired; the
  registry's closed-Literal/`is_registered` guards already reject it loudly).

## Registry design (`services/metric_registry.py`)

`get_metric(metric_name) -> MetricDescriptor`. Each descriptor bundles:

- `required_template_fields` — drives `Hypothesis._validate_metric` per metric.
- `default_choice_set` — curated fallback alternatives.
- `target_terms(hypothesis)` — lowercased term(s) naming the metric's TARGET
  action, filtered out of grounded alternatives so the question never offers two
  target-like options.
- `elicit(...)` — runs the metric's blinded §3e ensemble, returns
  `(mean_p_metric, paraphrase_unstable)`.
- `aggregator` — the paired treatment−control lift fn (mean Δ p_metric ×100 pp).
- `honesty(lift_result)` — `(regime_label, native-unit relative-statement)`.
- `calibrator_resolver()` — selects the metric's shrinkage calibrator (identity
  default for every metric pre-#222).
- `paraphrase_count` — caps the runner's K-scaled per-agent timeout.

Immutable dict built once at import → thread-safe to read across the runner's
per-agent fan-out. Unknown metric fails loud (closed `Hypothesis.metric_name`
Literal + `get_metric` KeyError).

Shared elicitation mechanics live in `services/metric_elicitor_core.py` (blinded
`elicit_one`, `resolve_count`, completeness check, `MetricDecision` validation,
`elicit_ensemble` averaging + §3e instability flag). `conversion_elicitor` and
`retention_elicitor` supply only their question paraphrases + defaults and
delegate the mechanics — so conversion stays behaviorally byte-identical.

## Decision A — generic result/record field naming (DONE, verified safe)

Exactly one `metric_name` per simulation → GENERIC fields, not parallel
per-metric ones:

- `AgentRecord` / `AgentReaction`: `conversion_p/conversion_unblinded/
  conversion_paraphrase_unstable` → `metric_p/metric_unblinded/
  metric_paraphrase_unstable`.
- `SimulationResult`: `conversion_lift_*` → `metric_lift_*`; `conversion_regime`
  → `metric_regime`; ADDED `metric_name: str | None` discriminator.
- `schemas.scoring.ConversionLiftResult` → `MetricLiftResult` (back-compat
  alias kept); `ConversionDecision` → `MetricDecision` (`p_conv` → `p_metric`,
  `conversion_action_label` → `target_label`).

VERIFIED: grep of backend + frontend found NO real (non-test) consumer of
`conversion_lift_*` / `conversion_p` / `conversion_regime` — no API serializer
reads them by name (the whole `SimulationResult` rides a JSON blob via
`model_dump` / `SimulationResult(**result_json)`), no frontend type, no DB
column. So the rename is **migration-free**: older `result_json` rows' legacy
keys are ignored on load and the renamed fields default. → did the rename.

## Decision B — retention blinded temporal framing (DONE)

- `decision_point` (default phrasing shipped): **"you've just finished tonight's
  session"**.
- Blinded `standalone_state_view` renders the steady-state product a returning
  user re-encounters (control = current; treatment = proposed standalone view).
  Agent never sees change framing. Unblindable-fallback flag works as conversion.
- 10-trial allocation over choice set **{"return next week", "return but less
  often", "stop using it", "switch to an alternative"}**.
- Return label (the metric target) = **"return next week"** (`RETENTION_RETURN_LABEL`).
- `p_metric = counts["return next week"] / total`; native unit = retention-rate
  lift in pp. Reuses §3e ensemble, #90 paired delta, §3b fallback flag verbatim.

## Change surface

- `schemas/simulation.py` — Literal `["conversion","retention"]`; registry-driven
  validator; `metric_lift_*` + `metric_name` result fields.
- `schemas/elicitation.py` — `MetricDecision` (generic, `target_label`/`p_metric`).
- `schemas/scoring.py` — `MetricLiftResult` (+ `ConversionLiftResult` alias).
- `services/metric_elicitor_core.py` (NEW) — shared blinded core + ensemble.
- `services/metric_registry.py` (NEW) — the registry.
- `services/conversion_elicitor.py` — delegates to core; public API preserved.
- `services/retention_elicitor.py` (NEW) — retention paraphrases + ensemble.
- `services/conversion_calibrator.py` — `MetricCalibrator` protocol +
  `resolve_metric_calibrator(metric_name)` (back-compat conversion wrapper).
- `services/scoring.py` — `AgentReaction.metric_*`; registry dispatch in
  `score_ab`; `metric_lift_honesty(...)` (metric-agnostic) +
  `aggregate_metric_lift` / `aggregate_conversion_lift` / `aggregate_retention_lift`.
- `services/simulation_runner.py` — `AgentRecord.metric_*`; registry-driven
  elicitation block (per-metric `target_terms` + `descriptor.elicit`).
- `services/runtime_config.py` — `resolve_conversion_paraphrases` reused for all
  metrics (one shared K knob; env name kept).
- `services/prompt_composer.py` — `compose_metric_prompt` reused unchanged.

## Tests

New: `test_retention_elicitor.py`, `test_retention_lift.py`,
`test_retention_runner.py`, `test_metric_registry.py` (unknown-metric raises).
Conversion tests updated for the renamed generic fields.

## Status

Code + tests COMPLETE. Full backend suite green except the known pre-existing
`test_deploy_config` (ProductHome). ruff + black clean. Conversion behaviorally
byte-identical (renames only). Dormant in prod (no frontend sets metric_name).
No Alembic migration. Next: codex review → PR for #275 (DO NOT MERGE).
