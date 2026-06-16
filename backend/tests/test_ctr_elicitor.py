"""Tests for the §3a/#276 CTR elicitor (on-screen click, immediate, no temporal framing).

Mirrors test_conversion_elicitor.py / test_retention_elicitor.py for the CTR
sibling, which rides the shared `metric_elicitor_core`:
- the `Hypothesis` CTR validator (decision_point required; the "click" label is
  optional and defaults to the registry constant),
- the blinded single-prompt + §3e ensemble through a recording fake,
- the on-screen blinding contract (no change framing, no prior assistant turn,
  no temporal/return framing — CTR is immediate),
- the failure posture (degenerate allocation → per-agent failure).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.elicitation import MetricDecision
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.ctr_elicitor import (
    CTR_CLICK_LABEL,
    DEFAULT_CTR_CHOICE_SET,
    _ctr_user_turn,
    elicit_ctr_decision,
    elicit_ctr_ensemble,
)
from sidira_simulator.services.metric_elicitor_core import _MetricAllocation


class _RecordingChat:
    def __init__(self, json_result) -> None:
        self.json_result = json_result
        self.calls: list[dict] = []

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append({"messages": messages, "schema": schema})
        return self.json_result

    def chat(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


class _SequencedChat:
    def __init__(self, results) -> None:
        self._results = list(results)
        self.calls: list[dict] = []

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append({"messages": messages, "schema": schema})
        return self._results[len(self.calls) - 1]

    def chat(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


def _alloc(counts, **kw):
    return _MetricAllocation(action_counts=counts, **kw)


_COMPLETE = {
    CTR_CLICK_LABEL: 4,
    "keep scrolling": 3,
    "skip it": 2,
    "leave": 1,
}


# ── Hypothesis CTR validator (registry-driven required fields) ────────────────


def test_hypothesis_ctr_requires_decision_point() -> None:
    """CTR's only required template field is decision_point (the on-screen moment);
    the click label defaults to the registry constant, so it isn't required."""
    with pytest.raises(ValidationError) as exc:
        Hypothesis(capability_name="feed", prose="x", metric_name="ctr")
    assert "decision_point" in str(exc.value)


def test_hypothesis_ctr_valid_with_decision_point() -> None:
    h = Hypothesis(
        capability_name="feed",
        prose="x",
        metric_name="ctr",
        decision_point="the new banner is on your home feed",
    )
    assert h.metric_name == "ctr"


# ── click-label semantics on MetricDecision ───────────────────────────────────


def test_p_metric_is_the_click_share() -> None:
    d = MetricDecision(action_counts=dict(_COMPLETE), target_label=CTR_CLICK_LABEL)
    # 4 / (4+3+2+1) = 0.4
    assert d.p_metric == pytest.approx(0.4)


# ── prompt assembly: on-screen framing, blinded ──────────────────────────────


def test_user_turn_uses_onscreen_framing_and_tags_click() -> None:
    options = [CTR_CLICK_LABEL, "keep scrolling", "leave"]
    turn = _ctr_user_turn(
        capability_name="Feed",
        click_label=CTR_CLICK_LABEL,
        decision_point="the new banner is on your home feed",
        options=options,
    )
    assert "Feed" in turn
    assert "the new banner is on your home feed" in turn
    assert "<- the target outcome" in turn
    assert f'"{CTR_CLICK_LABEL}"' in turn
    assert "10 separate times" in turn
    # JSON contract is well-formed (one "<label>": <int> per option)
    assert f'"{CTR_CLICK_LABEL}": <int>' in turn


def test_user_turn_carries_no_change_framing() -> None:
    """Blinding: no language that signals an intervention is under test or presumes
    a prior reaction."""
    options = [CTR_CLICK_LABEL, "keep scrolling"]
    turn = _ctr_user_turn(
        capability_name="Feed",
        click_label=CTR_CLICK_LABEL,
        decision_point="the new banner is on your home feed",
        options=options,
    ).lower()
    for banned in (
        "you just saw",
        "the change",
        "proposed change",
        "what's changing",
        "as described",
        "the team is considering",
    ):
        assert banned not in turn, f"change framing leaked: {banned!r}"


def test_user_turn_has_no_temporal_return_framing() -> None:
    """CTR is on-screen and immediate, NOT a future-return event (unlike retention):
    the question must never frame the decision as days/weeks out."""
    options = [CTR_CLICK_LABEL, "keep scrolling"]
    turn = _ctr_user_turn(
        capability_name="Feed",
        click_label=CTR_CLICK_LABEL,
        decision_point="the new banner is on your home feed",
        options=options,
    ).lower()
    for banned in ("next week", "come back", "the next few days", "over time", "return next"):
        assert banned not in turn, f"temporal/return framing leaked: {banned!r}"


# ── elicit_ctr_decision (single prompt) ───────────────────────────────────────


def test_elicit_builds_blinded_two_message_conversation_and_returns_p_metric() -> None:
    chat = _RecordingChat(
        _alloc(
            {
                CTR_CLICK_LABEL: 6,
                "keep scrolling": 2,
                "skip it": 1,
                "leave": 1,
            },
            primary_reason="  this is exactly what I'd tap  ",
        )
    )
    decision = elicit_ctr_decision(
        chat,
        system_prompt="SYSTEM",
        capability_name="Feed",
        decision_point="the new banner is on your home feed",
    )
    assert decision.p_metric == pytest.approx(0.6)
    assert decision.primary_reason == "this is exactly what I'd tap"
    (call,) = chat.calls
    roles = [m["role"] for m in call["messages"]]
    assert roles == ["system", "user"]  # no prior assistant turn (§3b)
    assert call["messages"][0]["content"] == "SYSTEM"


def test_elicit_uses_default_choice_set_when_none_supplied() -> None:
    chat = _RecordingChat(_alloc(dict(_COMPLETE)))
    elicit_ctr_decision(
        chat,
        system_prompt="S",
        capability_name="Feed",
        decision_point="now",
    )
    user_turn = chat.calls[0]["messages"][1]["content"]
    for alt in DEFAULT_CTR_CHOICE_SET:
        assert alt in user_turn
    assert CTR_CLICK_LABEL in user_turn


def test_elicit_raises_on_missing_click_label() -> None:
    chat = _RecordingChat(_alloc({"keep scrolling": 6, "leave": 4}))
    with pytest.raises(ValueError):
        elicit_ctr_decision(chat, system_prompt="S", capability_name="Feed", decision_point="now")


def test_elicit_raises_on_incomplete_allocation() -> None:
    chat = _RecordingChat(_alloc({CTR_CLICK_LABEL: 10}))
    with pytest.raises(ValueError, match="omitted offered option"):
        elicit_ctr_decision(chat, system_prompt="S", capability_name="Feed", decision_point="now")


def test_pm_supplied_click_label_overrides_default() -> None:
    """A PM may name the click label via the generic label field; the elicitor
    counts that key as the CTR target."""
    chat = _RecordingChat(_alloc({"tap the banner": 5, "keep scrolling": 3, "leave": 2}))
    decision = elicit_ctr_decision(
        chat,
        system_prompt="S",
        capability_name="Feed",
        click_label="tap the banner",
        decision_point="now",
        choice_set=["keep scrolling", "leave"],
    )
    assert decision.target_label == "tap the banner"
    assert decision.p_metric == pytest.approx(0.5)


# ── §3e ensemble ──────────────────────────────────────────────────────────────


def test_k1_is_single_call_canonical_wording() -> None:
    chat = _SequencedChat([_alloc(dict(_COMPLETE))])
    res = elicit_ctr_ensemble(
        chat,
        system_prompt="SYSTEM",
        capability_name="Feed",
        decision_point="now",
        paraphrases=1,
    )
    assert res.k_effective == 1
    assert res.mean_p_ctr == pytest.approx(0.4)
    assert res.paraphrase_unstable is False
    (call,) = chat.calls


def test_k3_averages_and_flags_instability() -> None:
    chat = _SequencedChat(
        [
            _alloc({CTR_CLICK_LABEL: 7, "keep scrolling": 2, "leave": 1}),
            _alloc({CTR_CLICK_LABEL: 2, "keep scrolling": 7, "leave": 1}),
            _alloc({CTR_CLICK_LABEL: 3, "keep scrolling": 4, "leave": 3}),
        ]
    )
    res = elicit_ctr_ensemble(
        chat,
        system_prompt="S",
        capability_name="Feed",
        decision_point="now",
        choice_set=["keep scrolling", "leave"],
        paraphrases=3,
    )
    assert res.k_effective == 3
    # mean of 0.7, 0.2, 0.3
    assert res.mean_p_ctr == pytest.approx((0.7 + 0.2 + 0.3) / 3)
    # spread 0.7-0.2 = 0.5 > 0.2 → flagged
    assert res.paraphrase_unstable is True
    # different question prose, identical system + options
    user_turns = [c["messages"][1]["content"] for c in chat.calls]
    assert len(set(user_turns)) == 3
    assert {c["messages"][0]["content"] for c in chat.calls} == {"S"}


def test_ensemble_drops_degenerate_paraphrase() -> None:
    chat = _SequencedChat(
        [
            _alloc({CTR_CLICK_LABEL: 4, "keep scrolling": 4, "leave": 2}),
            _alloc({CTR_CLICK_LABEL: 6}),  # incomplete → dropped
            _alloc({CTR_CLICK_LABEL: 2, "keep scrolling": 4, "leave": 4}),
        ]
    )
    res = elicit_ctr_ensemble(
        chat,
        system_prompt="S",
        capability_name="Feed",
        decision_point="now",
        choice_set=["keep scrolling", "leave"],
        paraphrases=3,
    )
    assert res.k_effective == 2
    assert res.mean_p_ctr == pytest.approx((0.4 + 0.2) / 2)
