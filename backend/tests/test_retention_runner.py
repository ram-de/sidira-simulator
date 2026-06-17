"""Runner wiring for the §275 retention turn-2 elicitation (Decision B).

Mirrors test_conversion_runner.py for the retention metric, asserting the
registry routes retention end-to-end through SimulationRunner:
- a dual-arm retention Hypothesis elicits a turn-2 decision per persona arm so
  every treatment/control AgentRecord carries a metric_p, and the composed
  SimulationResult surfaces a retention lift with metric_name="retention";
- the metric pass is BLINDED (no change framing in the system prompt);
- a per-agent failure leaves metric_p=None without failing the agent or run.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.schemas.scoring import (
    RefinementOutput,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.feature_pack import ReverseFigma, Screen, Transition
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.metric_elicitor_core import _MetricAllocation
from sidira_simulator.services.retention_elicitor import RETENTION_RETURN_LABEL
from sidira_simulator.services.simulation_runner import SimulationRunner

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


class _RetentionChat:
    """Canned reaction + classifications + a complete retention allocation parsed
    from the offered labels (return = 6, first alternative = 4) → p_metric = 0.6."""

    def __init__(self) -> None:
        self.metric_calls = 0
        self.metric_system_prompts: list[str] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        return "Stubbed reaction prose."

    def _alloc(self, messages) -> _MetricAllocation:
        user_turn = next(m["content"] for m in messages if m["role"] == "user")
        labels = re.findall(r'"([^"]*)": <int>', user_turn)
        counts = {lbl: 0 for lbl in labels}
        counts[RETENTION_RETURN_LABEL] = 6
        others = [lbl for lbl in labels if lbl != RETENTION_RETURN_LABEL]
        if others:
            counts[others[0]] = 4
        else:
            counts[RETENTION_RETURN_LABEL] = 10
        return _MetricAllocation(action_counts=counts)

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is _MetricAllocation:
            self.metric_calls += 1
            self.metric_system_prompts.append(
                next(m["content"] for m in messages if m["role"] == "system")
            )
            return self._alloc(messages)
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="stub")
        if schema is SentimentClassification:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=0.8, one_line_summary="stub"
            )
        if schema is RefinementOutput:
            return RefinementOutput(suggestions=[])
        raise NotImplementedError(schema)


def _load():
    store = LocalArtifactStore(_FIXTURE_ROOT)
    persona_pack = PersonaPackLoader(store).load_latest("demo")
    feature_loader = FeaturePackLoader(store)
    feature_pack_version = feature_loader.resolve_latest_version("demo")
    capability = feature_loader.load_capability("demo", feature_pack_version, "reorder")
    return store, persona_pack, capability, feature_pack_version


def _retention_hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="retention",
        decision_point="you've just finished tonight's session",
    )


@pytest.mark.asyncio
async def test_dual_arm_retention_elicits_per_persona_arm() -> None:
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _RetentionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_retention_hypothesis(),
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    records = runner._last_run_agent_records
    persona_arm_records = [r for r in records if r.arm in ("treatment", "control")]
    assert persona_arm_records, "expected treatment/control records"
    assert all(r.metric_p == pytest.approx(0.6) for r in persona_arm_records)
    assert chat.metric_calls == len(persona_arm_records)

    result = simulation.result
    assert result.metric_name == "retention"
    assert result.metric_lift_paired_n is not None
    assert result.metric_lift_paired_n > 0
    assert result.metric_lift_pp == pytest.approx(0.0)  # identical stub → zero lift
    assert result.metric_regime == "weak_behavioral"
    assert result.metric_lift_relative is not None


@pytest.mark.asyncio
async def test_v1_pack_surfaces_variance_collapse_flag_end_to_end() -> None:
    """The `demo` pack is v1.0-class: its personas carry no per-persona
    behavioral_seeds, so every materialized agent hits `draw_identity_seed`'s
    shared-default fallback. The composed SimulationResult must then surface the
    variance-collapse honesty flag (additively) so a flat blinded metric isn't
    misread as a true null. This exercises the full materialization→reaction→
    aggregation thread, not just the aggregator in isolation."""
    store, persona_pack, capability, feature_pack_version = _load()
    # Guard the premise: the fixture is genuinely a v1.0 pack (no behavioral_seeds).
    assert all(p.behavioral_seeds is None for p in persona_pack.personas)

    chat = _RetentionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_retention_hypothesis(),
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    # Every persona-arm record carries the fallback bit (captured at the draw site).
    persona_arm_records = [
        r for r in runner._last_run_agent_records if r.arm in ("treatment", "control")
    ]
    assert persona_arm_records
    assert all(r.behavioral_seeds_fallback for r in persona_arm_records)

    result = simulation.result
    assert result.metric_lift_variance_collapsed is True
    assert result.metric_lift_variance_collapsed_persona_count > 0
    # Honesty caveat carries the explanation; the metric numbers are unchanged.
    assert "cross-persona variance is degraded" in result.metric_lift_relative
    assert result.metric_lift_pp == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_retention_metric_runs_on_blinded_prompt() -> None:
    """With a proposed_figma (a faithful standalone steady-state view exists), the
    retention metric pass runs on a BLINDED system prompt — the agent re-encounters
    the steady-state product with no change framing (Decision B)."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _RetentionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    proposed = ReverseFigma(
        screens=[Screen(id="home", name="Home"), Screen(id="feed", name="Feed")],
        transitions=[
            Transition(trigger="open the feed", from_screen="home", to_screen="feed"),
        ],
    )
    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="retention",
        decision_point="you've just finished tonight's session",
        proposed_figma=proposed,
    )
    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=hypothesis,
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    assert chat.metric_system_prompts
    for sys_prompt in chat.metric_system_prompts:
        for marker in ("## What's changing", "### Explicitly NOT changing", "## Your task"):
            assert marker not in sys_prompt, f"retention metric not blinded: {marker!r}"


@pytest.mark.asyncio
async def test_no_metric_never_elicits_retention() -> None:
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _RetentionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=Hypothesis(capability_name="reorder", prose="x"),  # no metric
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )
    assert chat.metric_calls == 0
    assert all(r.metric_p is None for r in runner._last_run_agent_records)
    assert simulation.result.metric_lift_pp is None
    assert simulation.result.metric_name is None


@pytest.mark.asyncio
async def test_retention_failure_does_not_fail_agent() -> None:
    store, persona_pack, capability, feature_pack_version = _load()

    class _BadChat(_RetentionChat):
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            if schema is _MetricAllocation:
                self.metric_calls += 1
                return _MetricAllocation(action_counts={"stop using it": 10})  # no return label
            return super().chat_json(messages, schema, max_tokens, temperature, seed)

    chat = _BadChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_retention_hypothesis(),
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )
    persona_arm_records = [
        r for r in runner._last_run_agent_records if r.arm in ("treatment", "control")
    ]
    assert persona_arm_records
    assert all(r.metric_p is None for r in persona_arm_records)
    assert simulation.result.metric_lift_pp is None
    assert simulation.result.metric_lift_elicitation_failure_drops > 0
