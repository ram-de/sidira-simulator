"""Tests for the §3a/§275 retention elicitor (Decision B — temporal framing).

Mirrors test_conversion_elicitor.py for the retention sibling, which rides the
shared `metric_elicitor_core`:
- the `Hypothesis` retention validator (decision_point required; the "return"
  label is optional and defaults to the registry constant),
- the blinded single-prompt + §3e ensemble through a recording fake,
- the temporal blinding contract (no change framing, no prior assistant turn),
- the failure posture (degenerate allocation → per-agent failure).
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.elicitation import MetricDecision
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.metric_elicitor_core import _MetricAllocation
from sidira_simulator.services.retention_elicitor import (
    DEFAULT_RETENTION_CHOICE_SET,
    RETENTION_RETURN_LABEL,
    _retention_user_turn,
    elicit_retention_decision,
    elicit_retention_ensemble,
)


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
    RETENTION_RETURN_LABEL: 4,
    "return but less often": 3,
    "stop using it": 2,
    "switch to an alternative": 1,
}


# ── Hypothesis retention validator (registry-driven required fields) ──────────


def test_hypothesis_retention_requires_decision_point() -> None:
    """Retention's only required template field is decision_point (Decision B);
    the return label defaults to the registry constant, so it isn't required."""
    with pytest.raises(ValidationError) as exc:
        Hypothesis(capability_name="feed", prose="x", metric_name="retention")
    assert "decision_point" in str(exc.value)


def test_hypothesis_retention_valid_with_decision_point() -> None:
    h = Hypothesis(
        capability_name="feed",
        prose="x",
        metric_name="retention",
        decision_point="you've just finished tonight's session",
    )
    assert h.metric_name == "retention"


# ── return-label semantics on MetricDecision ──────────────────────────────────


def test_p_metric_is_the_return_share() -> None:
    d = MetricDecision(action_counts=dict(_COMPLETE), target_label=RETENTION_RETURN_LABEL)
    # 4 / (4+3+2+1) = 0.4
    assert d.p_metric == pytest.approx(0.4)


# ── prompt assembly: temporal framing, blinded ───────────────────────────────


def test_user_turn_uses_temporal_framing_and_tags_return() -> None:
    options = [RETENTION_RETURN_LABEL, "stop using it", "switch to an alternative"]
    turn = _retention_user_turn(
        capability_name="Feed",
        decision_point="you've just finished tonight's session",
        return_label=RETENTION_RETURN_LABEL,
        options=options,
    )
    assert "Feed" in turn
    assert "you've just finished tonight's session" in turn
    assert "<- the target outcome" in turn
    assert f'"{RETENTION_RETURN_LABEL}"' in turn
    assert "10 separate times" in turn
    # JSON contract is well-formed (one "<label>": <int> per option)
    assert f'"{RETENTION_RETURN_LABEL}": <int>' in turn


def test_user_turn_carries_no_change_framing() -> None:
    """Decision B blinding: no language that signals an intervention is under test
    or presumes a prior reaction."""
    options = [RETENTION_RETURN_LABEL, "stop using it"]
    turn = _retention_user_turn(
        capability_name="Feed",
        decision_point="you've just finished tonight's session",
        return_label=RETENTION_RETURN_LABEL,
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


# ── elicit_retention_decision (single prompt) ─────────────────────────────────


def test_elicit_builds_blinded_two_message_conversation_and_returns_p_metric() -> None:
    chat = _RecordingChat(
        _alloc(
            {
                RETENTION_RETURN_LABEL: 6,
                "return but less often": 2,
                "stop using it": 1,
                "switch to an alternative": 1,
            },
            primary_reason="  I always come back to this  ",
        )
    )
    decision = elicit_retention_decision(
        chat,
        system_prompt="SYSTEM",
        capability_name="Feed",
        decision_point="you've just finished tonight's session",
    )
    assert decision.p_metric == pytest.approx(0.6)
    assert decision.primary_reason == "I always come back to this"
    (call,) = chat.calls
    roles = [m["role"] for m in call["messages"]]
    assert roles == ["system", "user"]  # no prior assistant turn (§3b)
    assert call["messages"][0]["content"] == "SYSTEM"


def test_elicit_uses_default_choice_set_when_none_supplied() -> None:
    chat = _RecordingChat(_alloc(dict(_COMPLETE)))
    elicit_retention_decision(
        chat,
        system_prompt="S",
        capability_name="Feed",
        decision_point="now",
    )
    user_turn = chat.calls[0]["messages"][1]["content"]
    for alt in DEFAULT_RETENTION_CHOICE_SET:
        assert alt in user_turn
    assert RETENTION_RETURN_LABEL in user_turn


def test_elicit_raises_on_missing_return_label() -> None:
    chat = _RecordingChat(_alloc({"stop using it": 6, "switch to an alternative": 4}))
    with pytest.raises(ValueError):
        elicit_retention_decision(
            chat, system_prompt="S", capability_name="Feed", decision_point="now"
        )


def test_elicit_raises_on_incomplete_allocation() -> None:
    chat = _RecordingChat(_alloc({RETENTION_RETURN_LABEL: 10}))
    with pytest.raises(ValueError, match="omitted offered option"):
        elicit_retention_decision(
            chat, system_prompt="S", capability_name="Feed", decision_point="now"
        )


def test_pm_supplied_return_label_overrides_default() -> None:
    """A PM may name the return label via the generic label field; the elicitor
    counts that key as the retention target."""
    chat = _RecordingChat(
        _alloc({"come back tomorrow": 5, "stop using it": 3, "switch to an alternative": 2})
    )
    decision = elicit_retention_decision(
        chat,
        system_prompt="S",
        capability_name="Feed",
        return_label="come back tomorrow",
        decision_point="now",
        choice_set=["stop using it", "switch to an alternative"],
    )
    assert decision.target_label == "come back tomorrow"
    assert decision.p_metric == pytest.approx(0.5)


# ── §3e ensemble ──────────────────────────────────────────────────────────────


def test_k1_is_single_call_canonical_wording() -> None:
    chat = _SequencedChat([_alloc(dict(_COMPLETE))])
    res = elicit_retention_ensemble(
        chat,
        system_prompt="SYSTEM",
        capability_name="Feed",
        decision_point="now",
        paraphrases=1,
    )
    assert res.k_effective == 1
    assert res.mean_p_retention == pytest.approx(0.4)
    assert res.paraphrase_unstable is False
    (call,) = chat.calls


def test_k3_averages_and_flags_instability() -> None:
    chat = _SequencedChat(
        [
            _alloc({RETENTION_RETURN_LABEL: 7, "stop using it": 2, "switch to an alternative": 1}),
            _alloc({RETENTION_RETURN_LABEL: 2, "stop using it": 7, "switch to an alternative": 1}),
            _alloc({RETENTION_RETURN_LABEL: 3, "stop using it": 4, "switch to an alternative": 3}),
        ]
    )
    res = elicit_retention_ensemble(
        chat,
        system_prompt="S",
        capability_name="Feed",
        decision_point="now",
        choice_set=["stop using it", "switch to an alternative"],
        paraphrases=3,
    )
    assert res.k_effective == 3
    # mean of 0.7, 0.2, 0.3
    assert res.mean_p_retention == pytest.approx((0.7 + 0.2 + 0.3) / 3)
    # spread 0.7-0.2 = 0.5 > 0.2 → flagged
    assert res.paraphrase_unstable is True
    # different question prose, identical system + options
    user_turns = [c["messages"][1]["content"] for c in chat.calls]
    assert len(set(user_turns)) == 3
    assert {c["messages"][0]["content"] for c in chat.calls} == {"S"}


def test_ensemble_drops_degenerate_paraphrase() -> None:
    chat = _SequencedChat(
        [
            _alloc({RETENTION_RETURN_LABEL: 4, "stop using it": 4, "switch to an alternative": 2}),
            _alloc({RETENTION_RETURN_LABEL: 6}),  # incomplete → dropped
            _alloc({RETENTION_RETURN_LABEL: 2, "stop using it": 4, "switch to an alternative": 4}),
        ]
    )
    res = elicit_retention_ensemble(
        chat,
        system_prompt="S",
        capability_name="Feed",
        decision_point="now",
        choice_set=["stop using it", "switch to an alternative"],
        paraphrases=3,
    )
    assert res.k_effective == 2
    assert res.mean_p_retention == pytest.approx((0.4 + 0.2) / 2)
