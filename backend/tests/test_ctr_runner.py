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
async def test_grounded_click_alternative_filtered_from_ctr_options() -> None:
    """A reachable CLICK transition must be dropped from the alternatives even when
    the PM relies on the default click label: the elicitor prepends the canonical
    "click it", so forwarding a grounded click twin ("tap to open") would offer two
    click-like options while p_metric counts only the canonical one — agents could
    split click intent into the uncounted twin and understate CTR (codex P2). A
    genuine non-click alternative ("browse the full menu") survives the filter."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CtrChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    proposed = ReverseFigma(
        screens=[
            Screen(id="home", name="Home"),
            Screen(id="article", name="Article"),
            Screen(id="menu", name="Menu"),
        ],
        transitions=[
            # a grounded CLICK action — a twin of the canonical "click it" target
            Transition(trigger="tap to open", from_screen="home", to_screen="article"),
            # a genuine non-click alternative
            Transition(trigger="browse the full menu", from_screen="home", to_screen="menu"),
        ],
    )
    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Surface a headline banner on the home tab.",
        metric_name="ctr",  # no conversion_action_label → default "click it"
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
        # canonical click option present exactly once (prepended by the elicitor)
        assert '"click it": <int>' in turn
        # the grounded click twin is NOT also offered as a competing allocation key
        assert '"tap to open": <int>' not in turn
        # the genuine non-click alternative survives
        assert '"browse the full menu": <int>' in turn


@pytest.mark.asyncio
async def test_pm_choice_set_click_twin_filtered_from_ctr_options() -> None:
    """The same target-like filter applies to a PM-supplied choice_set: an arbitrary
    click phrasing the PM lists ("click the headline") is dropped, while a genuine
    non-click alternative survives (codex P2)."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CtrChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Surface a headline banner on the home tab.",
        metric_name="ctr",  # default "click it"
        decision_point="the headline banner is on your home tab",
        choice_set=["click the headline", "keep scrolling", "leave"],
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
        assert '"click it": <int>' in turn
        # the PM's click twin is dropped (arbitrary phrasing, caught by predicate)
        assert '"click the headline": <int>' not in turn
        # genuine non-click alternatives survive
        assert '"keep scrolling": <int>' in turn


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
