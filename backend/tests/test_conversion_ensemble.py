"""Tests for the §3e conversion paraphrase ensemble (#221).

The ensemble runs the SAME blinded conversion pass under K hand-authored
paraphrases of the *question wording only* (the blinded system prompt and the
option set are held byte-identical), averages `p_conv` over the survivors, and
flags the agent low-confidence when its plurality action flips on wording alone.

Covered here:
- K=1 is byte-identical to `elicit_conversion_decision` (the opt-in contract),
- K>1 issues one call per paraphrase with DIFFERENT question prose but an
  IDENTICAL system prompt + option set,
- mean p_conv over the K answers,
- the flip-under-paraphrase instability flag (plurality stable vs flipped),
- the failure posture (drop a degenerate paraphrase, raise only if all fail,
  clamp K to the available paraphrase count),
- the `resolve_conversion_paraphrases` env knob.
"""

from __future__ import annotations

import pytest

from sidira_simulator.services.conversion_elicitor import (
    _QUESTION_PARAPHRASES,
    _ConversionAllocation,
    _conversion_user_turn,
    elicit_conversion_decision,
    elicit_conversion_ensemble,
)
from sidira_simulator.services.runtime_config import resolve_conversion_paraphrases


class _SequencedChat:
    """Fake ChatClient that returns a queued result per chat_json call, recording
    every call so we can assert per-paraphrase prompt assembly."""

    def __init__(self, results) -> None:
        self._results = list(results)
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
        return self._results[len(self.calls) - 1]

    def chat(self, *a, **k):  # pragma: no cover - elicitor never calls chat
        raise NotImplementedError


def _alloc(counts, **kw):
    return _ConversionAllocation(action_counts=counts, **kw)


_COMMON = dict(
    capability_name="Reorder",
    conversion_action="complete checkout",
    conversion_action_label="check out now",
    decision_point="cart has 2 items",
    choice_set=["keep browsing", "leave"],
)


# ── K=1 byte-identical to the single-prompt path ─────────────────────────────


def test_k1_is_single_call_with_canonical_wording() -> None:
    chat = _SequencedChat([_alloc({"check out now": 2, "keep browsing": 4, "leave": 4})])
    res = elicit_conversion_ensemble(chat, system_prompt="SYSTEM", paraphrases=1, **_COMMON)

    assert res.k_effective == 1
    assert res.paraphrase_unstable is False
    assert res.mean_p_conv == pytest.approx(0.2)
    # exactly one call, blinded two-message conversation
    (call,) = chat.calls
    assert [m["role"] for m in call["messages"]] == ["system", "user"]
    # the question is the CANONICAL paraphrase (index 0) verbatim
    expected_turn = _conversion_user_turn(
        capability_name="Reorder",
        conversion_action="complete checkout",
        conversion_action_label="check out now",
        decision_point="cart has 2 items",
        options=["check out now", "keep browsing", "leave"],
    )
    assert call["messages"][1]["content"] == expected_turn


def test_k1_matches_elicit_conversion_decision_p_conv() -> None:
    """At K=1 the ensemble mean equals the single-prompt decision's p_conv."""
    counts = {"check out now": 3, "keep browsing": 3, "leave": 4}
    single = elicit_conversion_decision(
        _SequencedChat([_alloc(counts)]), system_prompt="S", **_COMMON
    )
    ens = elicit_conversion_ensemble(
        _SequencedChat([_alloc(counts)]), system_prompt="S", paraphrases=1, **_COMMON
    )
    assert ens.mean_p_conv == pytest.approx(single.p_conv)


# ── K>1: different wording, identical system prompt + options, averaged p_conv ─


def test_k3_issues_three_distinct_questions_same_system_and_options() -> None:
    chat = _SequencedChat(
        [
            _alloc({"check out now": 2, "keep browsing": 4, "leave": 4}),  # 0.2
            _alloc({"check out now": 4, "keep browsing": 3, "leave": 3}),  # 0.4
            _alloc({"check out now": 6, "keep browsing": 2, "leave": 2}),  # 0.6
        ]
    )
    res = elicit_conversion_ensemble(chat, system_prompt="SYSTEM", paraphrases=3, **_COMMON)

    assert res.k_effective == 3
    assert res.mean_p_conv == pytest.approx((0.2 + 0.4 + 0.6) / 3)
    assert len(chat.calls) == 3

    user_turns = [c["messages"][1]["content"] for c in chat.calls]
    # the QUESTION wording differs across paraphrases ...
    assert len(set(user_turns)) == 3
    # ... but the blinded SYSTEM prompt is byte-identical every call (§3e: only the
    # question varies; identity + state are held constant) ...
    assert {c["messages"][0]["content"] for c in chat.calls} == {"SYSTEM"}
    # ... and the OPTION set (bullets) is byte-identical: every paraphrase offers
    # the same labels so the ensemble isolates wording, not content.
    for turn in user_turns:
        assert '"check out now"' in turn
        assert '"keep browsing"' in turn
        assert '"leave"' in turn


# ── instability-under-paraphrase flag (p_conv spread) ────────────────────────


def test_stable_when_p_conv_spread_within_threshold() -> None:
    """p_conv moves only a little (0.2 → 0.3 → 0.2, spread 0.1 ≤ 0.2) → NOT
    flagged."""
    chat = _SequencedChat(
        [
            _alloc({"check out now": 2, "keep browsing": 4, "leave": 4}),  # 0.2
            _alloc({"check out now": 3, "keep browsing": 4, "leave": 3}),  # 0.3
            _alloc({"check out now": 2, "keep browsing": 5, "leave": 3}),  # 0.2
        ]
    )
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=3, **_COMMON)
    assert res.paraphrase_unstable is False


def test_unstable_when_p_conv_swings_past_threshold() -> None:
    """Wording alone moves p_conv 0.7 → 0.2 (spread 0.5 > 0.2) → flagged
    low-confidence (§3e)."""
    chat = _SequencedChat(
        [
            _alloc({"check out now": 7, "keep browsing": 2, "leave": 1}),  # 0.7
            _alloc({"check out now": 2, "keep browsing": 1, "leave": 7}),  # 0.2
            _alloc({"check out now": 3, "keep browsing": 3, "leave": 4}),  # 0.3
        ]
    )
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=3, **_COMMON)
    assert res.paraphrase_unstable is True


def test_non_conversion_reshuffle_does_not_flag() -> None:
    """codex P2: the conversion share is identical (2/10) under both paraphrases —
    only the non-conversion plurality swaps ('keep browsing' ↔ 'leave'). Since
    downstream scoring consumes only p_conv, this must NOT be flagged unstable."""
    chat = _SequencedChat(
        [
            _alloc({"check out now": 2, "keep browsing": 5, "leave": 3}),  # 0.2
            _alloc({"check out now": 2, "keep browsing": 3, "leave": 5}),  # 0.2
        ]
    )
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=2, **_COMMON)
    assert res.mean_p_conv == pytest.approx(0.2)
    assert res.paraphrase_unstable is False


def test_p_conv_is_case_insensitive_so_recased_key_is_stable() -> None:
    """A re-cased conversion key resolves to the same p_conv (0.6) via the
    ConversionDecision normalization, so it does not register spurious spread."""
    chat = _SequencedChat(
        [
            _alloc({"check out now": 6, "keep browsing": 2, "leave": 2}),
            _alloc({"CHECK OUT NOW": 6, "keep browsing": 2, "leave": 2}),
        ]
    )
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=2, **_COMMON)
    assert res.mean_p_conv == pytest.approx(0.6)
    assert res.paraphrase_unstable is False


# ── failure posture ──────────────────────────────────────────────────────────


def test_degenerate_paraphrase_is_dropped_not_fatal() -> None:
    """One paraphrase returns an incomplete allocation (raises inside _elicit_one);
    it is dropped and the mean is taken over the survivors."""
    chat = _SequencedChat(
        [
            _alloc({"check out now": 4, "keep browsing": 3, "leave": 3}),  # 0.4 ok
            _alloc({"check out now": 6}),  # incomplete → dropped
            _alloc({"check out now": 2, "keep browsing": 4, "leave": 4}),  # 0.2 ok
        ]
    )
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=3, **_COMMON)
    assert res.k_effective == 2
    assert res.mean_p_conv == pytest.approx((0.4 + 0.2) / 2)


def test_all_paraphrases_failing_raises() -> None:
    """If EVERY paraphrase is degenerate the ensemble raises — a per-agent
    conversion failure, identical to the single-prompt path (never a silent zero)."""
    chat = _SequencedChat([_alloc({"check out now": 6}), _alloc({"check out now": 5})])
    with pytest.raises(ValueError, match="omitted offered option"):
        elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=2, **_COMMON)


def test_k_clamped_to_available_paraphrases() -> None:
    """Requesting more paraphrases than exist runs only the hand-authored set —
    no IndexError, no invented wording."""
    n = len(_QUESTION_PARAPHRASES)
    chat = _SequencedChat([_alloc({"check out now": 5, "keep browsing": 3, "leave": 2})] * (n + 5))
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=n + 5, **_COMMON)
    assert res.k_effective == n
    assert len(chat.calls) == n


def test_paraphrases_below_one_clamps_to_one() -> None:
    chat = _SequencedChat([_alloc({"check out now": 5, "keep browsing": 3, "leave": 2})])
    res = elicit_conversion_ensemble(chat, system_prompt="S", paraphrases=0, **_COMMON)
    assert res.k_effective == 1


# ── resolve_conversion_paraphrases env knob ──────────────────────────────────


def test_resolve_paraphrases_default_is_one(monkeypatch) -> None:
    monkeypatch.delenv("SIDIRA_CONVERSION_PARAPHRASES", raising=False)
    monkeypatch.delenv("PYTHIA_CONVERSION_PARAPHRASES", raising=False)
    assert resolve_conversion_paraphrases() == 1


def test_resolve_paraphrases_reads_env(monkeypatch) -> None:
    monkeypatch.setenv("SIDIRA_CONVERSION_PARAPHRASES", "3")
    assert resolve_conversion_paraphrases() == 3


def test_resolve_paraphrases_malformed_fails_open(monkeypatch) -> None:
    monkeypatch.setenv("SIDIRA_CONVERSION_PARAPHRASES", "lots")
    assert resolve_conversion_paraphrases() == 1


def test_resolve_paraphrases_clamps_below_one(monkeypatch) -> None:
    monkeypatch.setenv("SIDIRA_CONVERSION_PARAPHRASES", "0")
    assert resolve_conversion_paraphrases() == 1
