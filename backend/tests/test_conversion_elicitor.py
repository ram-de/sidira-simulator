"""Tests for the §3a conversion elicitor + its schemas (#221).

Three layers:
- the `Hypothesis` metric validator (loud failure when a conversion metric is
  selected without its template fields),
- the `ConversionDecision` schema (p_conv normalization + degenerate-input
  guards),
- the `elicit_conversion_decision` service (prompt assembly, the chat_json
  dispatch, label remap, and the failure posture).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.elicitation import MetricDecision
from sidira_simulator.schemas.simulation import (
    DEFAULT_CONVERSION_CHOICE_SET,
    Hypothesis,
)
from sidira_simulator.services.conversion_elicitor import (
    _ConversionAllocation,
    _conversion_user_turn,
    _resolve_count,
    elicit_conversion_decision,
)

# ── recording fake ────────────────────────────────────────────────────────


class _RecordingChat:
    """Fake ChatClient: records chat_json call args, returns a canned object."""

    def __init__(self, json_result) -> None:
        self.json_result = json_result
        self.calls: list[dict] = []

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(
            {
                "messages": messages,
                "schema": schema,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "seed": seed,
            }
        )
        return self.json_result

    def chat(self, *a, **k):  # pragma: no cover - elicitor never calls chat
        raise NotImplementedError


# ── Hypothesis metric validator ─────────────────────────────────────────────


def test_hypothesis_no_metric_is_backwards_compatible() -> None:
    """Absent metric_name → the conversion fields are all unset; construction
    succeeds exactly as the historical sentiment-only contract."""
    h = Hypothesis(capability_name="reorder", prose="x")
    assert h.metric_name is None
    assert h.conversion_action is None
    assert h.conversion_action_label is None
    assert h.decision_point is None
    assert h.choice_set == []


def test_hypothesis_conversion_requires_template_fields() -> None:
    with pytest.raises(ValidationError) as exc:
        Hypothesis(capability_name="reorder", prose="x", metric_name="conversion")
    msg = str(exc.value)
    assert "conversion_action" in msg
    assert "conversion_action_label" in msg
    assert "decision_point" in msg


def test_hypothesis_conversion_rejects_blank_fields() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(
            capability_name="reorder",
            prose="x",
            metric_name="conversion",
            conversion_action="   ",
            conversion_action_label="buy",
            decision_point="at cart",
        )


def test_hypothesis_conversion_valid_with_template_fields() -> None:
    h = Hypothesis(
        capability_name="reorder",
        prose="x",
        metric_name="conversion",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="you have 2 items in your cart",
    )
    assert h.metric_name == "conversion"
    assert h.choice_set == []  # empty allowed; elicitor falls back


def test_hypothesis_rejects_unknown_metric() -> None:
    """metric_name is a closed Literal — an unknown metric fails loudly rather
    than silently degrading to sentiment."""
    with pytest.raises(ValidationError):
        Hypothesis(capability_name="reorder", prose="x", metric_name="ctr")


# ── MetricDecision schema (generic; #275) ─────────────────────────────────────


def test_metric_decision_p_metric_normalizes_by_actual_total() -> None:
    d = MetricDecision(
        action_counts={"buy": 3, "leave": 7},
        target_label="buy",
    )
    assert d.p_metric == pytest.approx(0.3)


def test_metric_decision_p_metric_robust_to_non_ten_total() -> None:
    """Spec frames it as 10 trials, but LLMs miscount; p_metric divides by the
    real total so a sum of 9 or 11 yields an honest fraction, not a >1 value."""
    d = MetricDecision(
        action_counts={"buy": 4, "leave": 5},  # sums to 9
        target_label="buy",
    )
    assert d.p_metric == pytest.approx(4 / 9)


def test_metric_decision_rejects_missing_label() -> None:
    with pytest.raises(ValidationError):
        MetricDecision(
            action_counts={"leave": 10},
            target_label="buy",
        )


def test_metric_decision_rejects_zero_total() -> None:
    with pytest.raises(ValidationError):
        MetricDecision(
            action_counts={"buy": 0, "leave": 0},
            target_label="buy",
        )


def test_metric_decision_rejects_negative_counts() -> None:
    with pytest.raises(ValidationError):
        MetricDecision(
            action_counts={"buy": -1, "leave": 11},
            target_label="buy",
        )


def test_metric_decision_confidence_bounds() -> None:
    with pytest.raises(ValidationError):
        MetricDecision(
            action_counts={"buy": 5, "leave": 5},
            target_label="buy",
            self_reported_confidence=1.5,
        )


# ── _resolve_count (key normalization) ────────────────────────────────────────


def test_resolve_count_strips_whitespace() -> None:
    out = _resolve_count({"  buy  ": 4, "leave": 6}, "buy")
    assert out["buy"] == 4


def test_resolve_count_case_insensitive_remap() -> None:
    out = _resolve_count({"BUY": 4, "leave": 6}, "buy")
    assert out["buy"] == 4
    assert "BUY" not in out


def test_resolve_count_raises_when_label_absent() -> None:
    with pytest.raises(ValueError, match="omitted the target action"):
        _resolve_count({"leave": 10}, "buy")


# ── prompt assembly ──────────────────────────────────────────────────────────


def test_user_turn_marks_conversion_option_and_lists_alternatives() -> None:
    turn = _conversion_user_turn(
        capability_name="Reorder",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="you have 2 items in your cart",
        options=["check out now", "keep browsing", "leave"],
    )
    assert "Reorder" in turn
    assert "you have 2 items in your cart" in turn
    # conversion keeps its historical tag verbatim (byte-identical prompt)
    assert "<- the conversion" in turn
    assert '"check out now"' in turn
    assert "keep browsing" in turn
    # the allocation frame (10 trials) must be present
    assert "10 separate times" in turn
    # The STRICT JSON example must be a well-formed object: one `"label": <int>`
    # entry per option (codex P2 — a bare key list renders invalid JSON).
    assert '"check out now": <int>' in turn
    assert '"keep browsing": <int>' in turn
    assert '"leave": <int>' in turn


def test_user_turn_escapes_quotes_in_option_labels() -> None:
    """A label with an embedded quote/backslash must render as valid escaped JSON
    in the example (codex P2), not a broken `"buy "premium"": <int>`."""
    turn = _conversion_user_turn(
        capability_name="C",
        conversion_action="buy",
        conversion_action_label='buy "premium"',
        decision_point="now",
        options=['buy "premium"', "leave"],
    )
    # The example carries the JSON-escaped form, and crucially the broken
    # unescaped form is absent.
    assert '"buy \\"premium\\"": <int>' in turn
    assert '"buy "premium"": <int>' not in turn


# ── elicit_conversion_decision (end-to-end through the fake) ──────────────────


def test_elicit_builds_blinded_two_message_conversation_and_returns_p_conv() -> None:
    chat = _RecordingChat(
        _ConversionAllocation(
            action_counts={"check out now": 2, "keep browsing / decide later": 8},
            primary_reason="  I rarely buy on first visit  ",
            self_reported_confidence=0.6,
        )
    )
    decision = elicit_conversion_decision(
        chat,
        system_prompt="SYSTEM",
        capability_name="Reorder",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="cart has 2 items",
        # complete allocation: every offered label present (codex P2)
        choice_set=["keep browsing / decide later"],
    )
    assert decision.p_metric == pytest.approx(0.2)
    assert decision.primary_reason == "I rarely buy on first visit"

    # BLINDED pass (§3b): the conversation is [system(blinded), user(decision)]
    # ONLY — NO assistant prior turn. The unblinded turn-1 reaction must not
    # condition the metric, or the change framing leaks back and inflates the
    # treatment arm (the bias that does not cancel in the delta).
    (call,) = chat.calls
    roles = [m["role"] for m in call["messages"]]
    assert roles == ["system", "user"]
    assert "assistant" not in roles
    assert call["messages"][0]["content"] == "SYSTEM"
    assert call["schema"] is _ConversionAllocation


def test_elicit_metric_prompt_carries_no_change_framing() -> None:
    """The decision ask must be blinded: no language that signals an intervention
    is under test or presumes a prior reaction (§3b). A regression here silently
    re-unblinds the metric and corrupts the conversion lift."""
    chat = _RecordingChat(_ConversionAllocation(action_counts={"check out now": 5, "leave": 5}))
    elicit_conversion_decision(
        chat,
        system_prompt="S",
        capability_name="Reorder",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="cart has 2 items",
        choice_set=["leave"],
    )
    user_turn = chat.calls[0]["messages"][1]["content"].lower()
    for banned in (
        "you just saw",
        "the change",
        "proposed change",
        "the team is considering",
        "what's changing",
        "as described",
    ):
        assert banned not in user_turn, f"change framing leaked into metric ask: {banned!r}"


def test_elicit_uses_default_choice_set_when_none_supplied() -> None:
    # A complete allocation over the conversion label + the full default set, so
    # the offered-options coverage check (codex P2) passes and we can assert the
    # default alternatives reached the question.
    chat = _RecordingChat(
        _ConversionAllocation(
            action_counts={
                "check out now": 4,
                "keep browsing / decide later": 2,
                "leave without doing anything": 2,
                "compare with a competitor first": 2,
            }
        )
    )
    elicit_conversion_decision(
        chat,
        system_prompt="S",
        capability_name="C",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="now",
    )
    user_turn = chat.calls[0]["messages"][1]["content"]
    for alt in DEFAULT_CONVERSION_CHOICE_SET:
        assert alt in user_turn


def test_elicit_case_insensitive_label_does_not_drop_agent() -> None:
    """A model that re-cases the conversion key still resolves to a p_conv
    rather than raising a spurious per-agent failure."""
    chat = _RecordingChat(_ConversionAllocation(action_counts={"CHECK OUT NOW": 3, "leave": 7}))
    decision = elicit_conversion_decision(
        chat,
        system_prompt="S",
        capability_name="C",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="now",
        choice_set=["leave"],
    )
    assert decision.p_metric == pytest.approx(0.3)


def test_elicit_raises_on_missing_conversion_label() -> None:
    chat = _RecordingChat(_ConversionAllocation(action_counts={"leave": 6, "keep browsing": 4}))
    with pytest.raises(ValueError):
        elicit_conversion_decision(
            chat,
            system_prompt="S",
            capability_name="C",
            conversion_action="complete checkout",
            conversion_action_label="check out now",
            decision_point="now",
        )


def test_elicit_raises_on_zero_total() -> None:
    chat = _RecordingChat(_ConversionAllocation(action_counts={"check out now": 0, "leave": 0}))
    with pytest.raises(ValueError):
        elicit_conversion_decision(
            chat,
            system_prompt="S",
            capability_name="C",
            conversion_action="complete checkout",
            conversion_action_label="check out now",
            decision_point="now",
            # complete allocation (all offered labels present) so the raise comes
            # from the zero-total guard, not the incomplete-allocation check.
            choice_set=["leave"],
        )


def test_elicit_raises_on_incomplete_allocation() -> None:
    """codex P2: a response that omits an offered non-conversion option (so the
    denominator shrinks and p_conv inflates) is a degenerate allocation → raise,
    rather than silently reporting an inflated propensity."""
    chat = _RecordingChat(_ConversionAllocation(action_counts={"check out now": 6}))
    with pytest.raises(ValueError, match="omitted offered option"):
        elicit_conversion_decision(
            chat,
            system_prompt="S",
            capability_name="C",
            conversion_action="complete checkout",
            conversion_action_label="check out now",
            decision_point="now",
            choice_set=["leave", "compare first"],
        )
