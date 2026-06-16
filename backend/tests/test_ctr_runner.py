"""Runner wiring for the #276 CTR turn-2 elicitation (on-screen click).

Mirrors test_conversion_runner.py / test_retention_runner.py for the CTR metric,
asserting the registry routes CTR end-to-end through SimulationRunner:
- a dual-arm CTR Hypothesis elicits a turn-2 decision per persona arm so every
  treatment/control AgentRecord carries a metric_p, and the composed
  SimulationResult surfaces a CTR lift with metric_name="ctr";
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
from sidira_simulator.services.ctr_elicitor import CTR_CLICK_LABEL
from sidira_simulator.services.metric_elicitor_core import _MetricAllocation
from sidira_simulator.services.simulation_runner import SimulationRunner

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


class _CtrChat:
    """Canned reaction + classifications + a complete CTR allocation parsed from
    the offered labels (click = 6, first alternative = 4) → p_metric = 0.6."""

    def __init__(self) -> None:
        self.metric_calls = 0
        self.metric_system_prompts: list[str] = []
        self.metric_user_turns: list[str] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        return "Stubbed reaction prose."

    def _alloc(self, messages) -> _MetricAllocation:
        user_turn = next(m["content"] for m in messages if m["role"] == "user")
        labels = re.findall(r'"([^"]*)": <int>', user_turn)
        counts = {lbl: 0 for lbl in labels}
        counts[CTR_CLICK_LABEL] = 6
        others = [lbl for lbl in labels if lbl != CTR_CLICK_LABEL]
        if others:
            counts[others[0]] = 4
        else:
            counts[CTR_CLICK_LABEL] = 10
        return _MetricAllocation(action_counts=counts)

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is _MetricAllocation:
            self.metric_calls += 1
            self.metric_system_prompts.append(
                next(m["content"] for m in messages if m["role"] == "system")
            )
            self.metric_user_turns.append(
                next(m["content"] for m in messages if m["role"] == "user")
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


def _ctr_hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="ctr",
        decision_point="the reorder button is on your home tab",
    )


@pytest.mark.asyncio
async def test_dual_arm_ctr_elicits_per_persona_arm() -> None:
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CtrChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_ctr_hypothesis(),
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
    assert result.metric_name == "ctr"
    assert result.metric_lift_paired_n is not None
    assert result.metric_lift_paired_n > 0
    assert result.metric_lift_pp == pytest.approx(0.0)  # identical stub → zero lift
    assert result.metric_regime == "strong_behavioral"
    assert result.metric_lift_relative is not None


@pytest.mark.asyncio
async def test_ctr_metric_runs_on_blinded_prompt() -> None:
    """With a proposed_figma (a faithful standalone view exists), the CTR metric
    pass runs on a BLINDED system prompt — the agent encounters the standalone
    screen with no change framing."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CtrChat()
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
        metric_name="ctr",
        decision_point="the reorder button is on your home tab",
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
            assert marker not in sys_prompt, f"CTR metric not blinded: {marker!r}"


@pytest.mark.asyncio
async def test_named_target_click_trigger_filtered_but_competing_clicks_survive() -> None:
    """CTR mirrors conversion's target filtering (codex P2): the grounded transition
    whose trigger IS the PM-named click target (conversion_action_label) is dropped
    from the alternatives — the elicitor prepends that canonical label, so keeping
    the twin would split p_metric and understate CTR. But OTHER clickable actions
    reachable at the same decision point ("tap search", "open menu") are LEGITIMATE
    competing-click alternatives and must SURVIVE — filtering them would deny them
    any allocation share and inflate the reported CTR."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CtrChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    proposed = ReverseFigma(
        screens=[
            Screen(id="home", name="Home"),
            Screen(id="article", name="Article"),
            Screen(id="search", name="Search"),
            Screen(id="menu", name="Menu"),
        ],
        transitions=[
            # trigger EQUALS the PM-named click target below → filtered
            Transition(trigger="tap the banner", from_screen="home", to_screen="article"),
            # OTHER clickable actions → legitimate competing clicks, must survive
            Transition(trigger="tap search", from_screen="home", to_screen="search"),
            Transition(trigger="open menu", from_screen="home", to_screen="menu"),
        ],
    )
    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Surface a headline banner on the home tab.",
        metric_name="ctr",
        conversion_action_label="tap the banner",  # the click target element
        decision_point="home",
        proposed_figma=proposed,
    )
    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=hypothesis,
        population_size=2,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    assert chat.metric_user_turns
    for turn in chat.metric_user_turns:
        # canonical target click option present exactly once (prepended by elicitor)
        assert '"tap the banner": <int>' in turn
        assert turn.count('"tap the banner": <int>') == 1
        # competing clicks SURVIVE as their own allocation keys (not over-filtered)
        assert '"tap search": <int>' in turn
        assert '"open menu": <int>' in turn


@pytest.mark.asyncio
async def test_no_metric_never_elicits_ctr() -> None:
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CtrChat()
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
async def test_ctr_failure_does_not_fail_agent() -> None:
    store, persona_pack, capability, feature_pack_version = _load()

    class _BadChat(_CtrChat):
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            if schema is _MetricAllocation:
                self.metric_calls += 1
                return _MetricAllocation(action_counts={"keep scrolling": 10})  # no click label
            return super().chat_json(messages, schema, max_tokens, temperature, seed)

    chat = _BadChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_ctr_hypothesis(),
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
