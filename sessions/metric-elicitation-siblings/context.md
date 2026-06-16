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

## Codex review (round 1) — triage

- **P1 "retention can run unblinded via fallback"** — NOT a bug. Decision B
  mandates retention reuse conversion's §3b unblindable-fallback posture
  verbatim: when no faithful standalone view exists the metric runs unblinded
  and the result is flagged low-confidence (`metric_lift_unblinded_fallback`).
  Identical to conversion; changing it would diverge from the spec. No change.
- **P2 conversion prompt not byte-identical** — FIXED. `option_bullets` now
  takes a `target_tag`; conversion passes its historical `"   <- the conversion"`
  so the default conversion prompt is byte-for-byte unchanged. Retention uses
  the generic `"   <- the target outcome"`.
- **P2 runner dispatch not fail-loud** — FIXED. The runner now gates on
  `hypothesis.metric_name is not None` and dispatches through `get_metric`
  directly (raises KeyError on registry/Literal drift) instead of
  `is_registered(...)`-then-skip. `is_registered` import dropped from the runner.
- **P2 stale test asserts `retention` unknown** — FIXED. The unknown-metric test
  now uses `"ctr"` (genuinely unregistered) instead of `"retention"`.
- **Note: `_REGISTRY` mutable** — FIXED. Wrapped in `MappingProxyType` so the
  registry is genuinely read-only (true thread-safe concurrent reads).

## Status

Code + tests COMPLETE; all real codex P1/P2 addressed (round 1). Rebased onto
latest `origin/main` (benchmark #277 landed there; clean rebase — our
`MetricLiftResult` rename and upstream's `BenchmarkRunResult` coexist in
scoring.py). Full backend suite green (1007 passed, 11 skipped) except the known
pre-existing `test_deploy_config` (ProductHome). ruff + black clean. Conversion
behaviorally byte-identical (renames + verbatim prompt). Dormant in prod (no
frontend sets metric_name). No Alembic migration. Next: re-review → PR for #275
(DO NOT MERGE).

## #276 CTR metric (feat/276-ctr-metric)

Third descriptor, mirrors conversion (on-screen click, immediate, NO temporal
framing — unlike retention). Registered `ctr` in the #275 registry; zero runner
changes (registry-driven dispatch + extract_choice_set grounding inherited for
free). New `services/ctr_elicitor.py` (CTR_CLICK_LABEL="click it",
DEFAULT_CTR_CHOICE_SET=("keep scrolling","skip it","leave"), 3 §3e paraphrases,
blinded, decision_point required / click label optional like retention).
`aggregate_ctr_lift` wrapper + `_ctr_honesty` (native "clicks through" wording).
Regime: `strong_behavioral` (§5 — CTR correlates r≈0.7–0.9 vs the weak-behavioral
modality cliff; uncalibrated caveat still applies pre-#222). Literal += "ctr".
Tests: test_ctr_elicitor/lift/runner + extended test_metric_registry. Full suite
green (1055 passed, 11 skipped) except pre-existing test_deploy_config(ProductHome).
ruff + black clean. Conversion + retention byte-identical/unperturbed. PR OPEN,
DO NOT MERGE.

### #276 codex convergence

4 codex rounds → CLEAN. Fixes: (P2) CTR honesty caveat now matches its strong
regime (parameterized signal_strength_clause; siblings byte-identical); (P1)
stale test_conversion_elicitor unknown-metric test moved off "ctr" → "dwell_time";
(P2) CTR click-twin filtering — landed on the conversion-mirror: target_terms
filters only the PM-named/default click label, competing clicks ("tap search")
survive (an over-broad click-verb predicate was tried and reverted because it
dropped legitimate competing clicks → would inflate CTR). simulation_runner.py is
byte-identical to origin/main (0-line diff). Final codex: no P1/P2. Full suite
1056 passed / 11 skipped / 1 pre-existing (test_deploy_config ProductHome).

## #279 — wizard metric picker (frontend) — IN PROGRESS
Added an OPTIONAL, A/B-only metric picker (None/Conversion/Retention/CTR) to
frontend/app/simulations/new/page.tsx, mirroring metric_registry required
template fields (conversion → conversion_action + conversion_action_label +
decision_point; retention/ctr → decision_point only, label optional) + optional
choice_set (one alt per line). None = byte-identical sentiment-only payload.
api-types.ts hand-edited (gen-types needs live backend at :8000). tsc + next
build clean. PR open on feat/279-metric-picker-wizard.
