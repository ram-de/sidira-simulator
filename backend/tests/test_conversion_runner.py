"""Runner wiring for the §3a conversion turn-2 elicitation (#221).

Asserts the gating contract end-to-end through SimulationRunner:
- a dual-arm run with a conversion Hypothesis elicits a turn-2 decision per
  persona arm, so every treatment/control AgentRecord carries a conversion_p,
  and the composed SimulationResult surfaces a conversion lift;
- a single-arm run (no paired control) never elicits conversion;
- a run without metric_name never elicits conversion (backwards-compat);
- a per-agent conversion failure leaves conversion_p=None without failing the
  agent or the run.
"""

from __future__ import annotations

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
from sidira_simulator.services.conversion_elicitor import _ConversionAllocation
from sidira_simulator.services.simulation_runner import SimulationRunner

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


class _ConversionChat:
    """Canned reaction + classifications + a fixed conversion allocation.

    The allocation is {convert: 6, alt: 4} → p_conv = 0.6 for every agent, so a
    paired treatment−control delta is exactly 0 (same allocation both arms) —
    which is the honest expectation for an identical-behavior stub and keeps the
    assertions about *presence* of conversion_p independent of any contrived
    arm asymmetry.
    """

    def __init__(self, *, conversion_label: str = "check out now") -> None:
        self._label = conversion_label
        self.conversion_calls = 0

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        return "Stubbed reaction prose."

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is _ConversionAllocation:
            self.conversion_calls += 1
            return _ConversionAllocation(action_counts={self._label: 6, "keep browsing": 4})
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


def _conversion_hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="conversion",
        conversion_action="tap reorder and check out",
        conversion_action_label="check out now",
        decision_point="you opened the home tab with a past order visible",
    )


def _plain_hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
    )


@pytest.mark.asyncio
async def test_dual_arm_conversion_elicits_per_persona_arm() -> None:
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _ConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_conversion_hypothesis(),
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    records = runner._last_run_agent_records
    persona_arm_records = [r for r in records if r.arm in ("treatment", "control")]
    assert persona_arm_records, "expected treatment/control records"
    # Every persona-arm record got a turn-2 conversion elicitation.
    assert all(r.conversion_p == pytest.approx(0.6) for r in persona_arm_records)
    # One conversion call per persona-arm agent.
    assert chat.conversion_calls == len(persona_arm_records)

    # End-to-end: the composed result surfaces a (zero, identical-stub) lift and
    # the weak-regime honesty label — never None, since the metric was set.
    result = simulation.result
    assert result.conversion_lift_paired_n is not None
    assert result.conversion_lift_paired_n > 0
    assert result.conversion_lift_pp == pytest.approx(0.0)
    assert result.conversion_regime == "weak_behavioral"
    assert result.conversion_lift_relative is not None


@pytest.mark.asyncio
async def test_single_arm_conversion_does_not_elicit() -> None:
    """No paired control → no conversion lift to compute, so the runner skips
    the turn-2 call entirely (it only fires for treatment/control arms)."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _ConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_conversion_hypothesis(),
        population_size=3,
        run_seed=12345,
    )

    records = runner._last_run_agent_records
    assert all(r.arm is None for r in records)
    assert all(r.conversion_p is None for r in records)
    assert chat.conversion_calls == 0


@pytest.mark.asyncio
async def test_no_metric_never_elicits_conversion() -> None:
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _ConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_plain_hypothesis(),
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    assert chat.conversion_calls == 0
    assert all(r.conversion_p is None for r in runner._last_run_agent_records)
    assert simulation.result.conversion_lift_pp is None
    assert simulation.result.conversion_lift_paired_n is None


@pytest.mark.asyncio
async def test_conversion_failure_does_not_fail_agent() -> None:
    """A degenerate allocation (missing the conversion label) must surface as a
    per-agent conversion failure (conversion_p=None) — the agent and the run
    still complete."""
    store, persona_pack, capability, feature_pack_version = _load()

    class _BadConversionChat(_ConversionChat):
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            if schema is _ConversionAllocation:
                self.conversion_calls += 1
                # No conversion-label key → elicitor raises → per-agent failure.
                return _ConversionAllocation(action_counts={"keep browsing": 10})
            return super().chat_json(messages, schema, max_tokens, temperature, seed)

    chat = _BadConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    simulation = await runner.run(
        customer_id="demo",
        persona_pack=persona_pack,
        capability=capability,
        feature_pack_version=feature_pack_version,
        hypothesis=_conversion_hypothesis(),
        population_size=4,
        run_seed=12345,
        treatment_fraction=0.5,
    )

    records = runner._last_run_agent_records
    persona_arm_records = [r for r in records if r.arm in ("treatment", "control")]
    assert persona_arm_records, "agents should still materialize"
    assert chat.conversion_calls == len(persona_arm_records)
    # Every conversion elicitation failed → conversion_p None, but agents alive.
    assert all(r.conversion_p is None for r in persona_arm_records)
    # All pairs dropped → lift not computable, surfaced honestly.
    assert simulation.result.conversion_lift_pp is None
    assert simulation.result.conversion_lift_elicitation_failure_drops > 0


class _CapturingConversionChat(_ConversionChat):
    """Captures the user-turn of every conversion elicitation so a test can
    assert which choice labels the agent was actually offered."""

    def __init__(self, *, conversion_label: str = "check out now") -> None:
        super().__init__(conversion_label=conversion_label)
        self.conversion_user_turns: list[str] = []

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if schema is _ConversionAllocation:
            user_turn = next(m["content"] for m in messages if m["role"] == "user")
            self.conversion_user_turns.append(user_turn)
        return super().chat_json(messages, schema, max_tokens, temperature, seed)


@pytest.mark.asyncio
async def test_pm_supplied_choice_set_reaches_the_question() -> None:
    """An explicit Hypothesis.choice_set is offered verbatim in the question."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CapturingConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    hypothesis = _conversion_hypothesis()
    hypothesis = hypothesis.model_copy(
        update={"choice_set": ["save it for later", "ask a colleague first"]}
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

    assert chat.conversion_user_turns
    for turn in chat.conversion_user_turns:
        assert "save it for later" in turn
        assert "ask a colleague first" in turn


@pytest.mark.asyncio
async def test_pm_supplied_choice_set_filters_conversion_action() -> None:
    """A PM-supplied alternative equal to the conversion action/label is dropped
    before reaching the elicitor (codex P2) — otherwise the prompt would offer
    two conversion-like options and undercount p_conv."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CapturingConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    hypothesis = _conversion_hypothesis().model_copy(
        update={
            # includes the conversion action verbatim + a label-case variant
            "choice_set": [
                "tap reorder and check out",
                "Check Out Now",
                "browse the menu instead",
            ]
        }
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

    assert chat.conversion_user_turns
    for turn in chat.conversion_user_turns:
        # canonical conversion option present exactly once (prepended by elicitor)
        assert '"check out now": <int>' in turn
        # the conversion action / label-variant are NOT also offered as keys
        assert '"tap reorder and check out": <int>' not in turn
        assert '"Check Out Now": <int>' not in turn
        # the genuine non-conversion alternative survives
        assert '"browse the menu instead": <int>' in turn


@pytest.mark.asyncio
async def test_choice_set_grounded_in_rendered_screen_when_absent() -> None:
    """With a proposed_figma and no PM choice_set, the question's alternatives are
    grounded in the actual reachable actions at the decision point (codex P2 —
    treatment_renderer.extract_choice_set), not the generic fallback."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CapturingConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    proposed = ReverseFigma(
        screens=[Screen(id="home", name="Home"), Screen(id="checkout", name="Checkout")],
        transitions=[
            Transition(
                trigger="tap reorder and check out",
                from_screen="home",
                to_screen="checkout",
            ),
            Transition(
                trigger="browse the full menu instead",
                from_screen="home",
                to_screen="menu",
            ),
        ],
    )
    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="conversion",
        conversion_action="tap reorder and check out",
        conversion_action_label="check out now",
        decision_point="home",  # the from_screen id the transitions leave
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

    assert chat.conversion_user_turns
    for turn in chat.conversion_user_turns:
        # The reachable on-screen action is offered (grounded), not just the
        # curated generic fallbacks.
        assert "browse the full menu instead" in turn


@pytest.mark.asyncio
async def test_renderer_fallback_does_not_inject_generic_convert_option() -> None:
    """When proposed_figma is present but the decision_point has no reachable
    transitions, the extractor's own fallback set (which includes a generic
    "convert") must NOT be forwarded — the elicitor uses its curated
    non-conversion default instead, so the prompt never offers a second,
    generic conversion option that would split p_conv (codex P2)."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CapturingConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    # A figma whose transitions leave a DIFFERENT screen → no reachable action
    # at the decision point → extract_choice_set falls back (fallback_used=True).
    proposed = ReverseFigma(
        screens=[Screen(id="home", name="Home"), Screen(id="cart", name="Cart")],
        transitions=[Transition(trigger="open cart", from_screen="cart", to_screen="checkout")],
    )
    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="conversion",
        conversion_action="tap reorder and check out",
        conversion_action_label="check out now",
        decision_point="home",  # no transition leaves "home" → fallback path
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

    assert chat.conversion_user_turns
    for turn in chat.conversion_user_turns:
        # The single real conversion option is present...
        assert '"check out now"' in turn
        # ...and the generic extractor-fallback "convert" is NOT injected as a
        # competing option.
        assert '"convert"' not in turn
        # The curated non-conversion default IS used instead.
        assert "keep browsing / decide later" in turn


@pytest.mark.asyncio
async def test_conversion_action_filtered_from_grounded_alternatives() -> None:
    """When a reachable transition's trigger IS the conversion action but the PM
    supplies a different display label, the grounded conversion transition must be
    dropped from the alternatives — the elicitor prepends the canonical label, so
    forwarding the twin would offer two conversion options and undercount p_conv
    (codex P2)."""
    store, persona_pack, capability, feature_pack_version = _load()
    chat = _CapturingConversionChat()
    runner = SimulationRunner(store=store, chat_client=chat)

    proposed = ReverseFigma(
        screens=[
            Screen(id="home", name="Home"),
            Screen(id="checkout", name="Checkout"),
            Screen(id="menu", name="Menu"),
        ],
        transitions=[
            # trigger EQUALS conversion_action below
            Transition(
                trigger="tap reorder and check out", from_screen="home", to_screen="checkout"
            ),
            Transition(trigger="browse the full menu", from_screen="home", to_screen="menu"),
        ],
    )
    hypothesis = Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="conversion",
        conversion_action="tap reorder and check out",
        conversion_action_label="check out now",
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

    assert chat.conversion_user_turns
    for turn in chat.conversion_user_turns:
        # The canonical conversion option appears exactly once, as a JSON key.
        assert '"check out now": <int>' in turn
        # The grounded conversion transition is NOT also offered as an alternative
        # allocation key (it only appears in prose, never as a competing option).
        assert '"tap reorder and check out": <int>' not in turn
        # The genuine non-conversion alternative survives the filter.
        assert '"browse the full menu": <int>' in turn
