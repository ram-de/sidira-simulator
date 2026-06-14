"""Tests for distribution elicitation (agent-behavior-spec Item B / ticket #221).

Two layers:
- the `ReactionDistribution` schema (normalization invariant + modal selection),
- the `elicit_reaction_distribution` service (k=1 reduces to the historical
  single `chat()` call; k>1 maps a verbalized-sampling response into a
  normalized distribution and rejects degenerate output).
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.elicitation import ReactionDistribution, ReactionSample
from sidira_simulator.services.reaction_elicitor import (
    _VerbalizedSample,
    _VerbalizedSampling,
    elicit_reaction_distribution,
)

# ── recording fakes ──────────────────────────────────────────────────────────


class _RecordingChat:
    """Fake ChatClient that records call args and returns canned output.

    `json_result` is the object `chat_json` returns; `text_result` what `chat`
    returns. Each call appends its kwargs to `calls` so a test can assert the
    elicitor dispatched the right call with the right temperature/seed.
    """

    def __init__(self, *, text_result: str = "", json_result=None) -> None:
        self.text_result = text_result
        self.json_result = json_result
        self.calls: list[dict] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(
            {
                "kind": "chat",
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "seed": seed,
            }
        )
        return self.text_result

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(
            {
                "kind": "chat_json",
                "messages": messages,
                "schema": schema,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "seed": seed,
            }
        )
        return self.json_result


def _vs(*pairs: tuple[str, float]) -> _VerbalizedSampling:
    return _VerbalizedSampling(
        reactions=[_VerbalizedSample(reaction=t, probability=p) for t, p in pairs]
    )


# ── schema: normalization + modal ────────────────────────────────────────────


def test_probabilities_are_normalized_to_sum_to_one():
    dist = ReactionDistribution(
        samples=[
            ReactionSample(text="a", probability=3.0),
            ReactionSample(text="b", probability=1.0),
        ],
        temperature=0.7,
    )
    probs = [s.probability for s in dist.samples]
    assert probs == pytest.approx([0.75, 0.25])
    assert sum(probs) == pytest.approx(1.0)


def test_already_normalized_distribution_is_left_unchanged():
    dist = ReactionDistribution(
        samples=[
            ReactionSample(text="a", probability=0.6),
            ReactionSample(text="b", probability=0.4),
        ],
        temperature=0.0,
    )
    assert [s.probability for s in dist.samples] == pytest.approx([0.6, 0.4])


def test_modal_is_highest_probability_sample():
    dist = ReactionDistribution(
        samples=[
            ReactionSample(text="low", probability=1.0),
            ReactionSample(text="high", probability=4.0),
        ],
        temperature=1.0,
    )
    assert dist.modal.text == "high"


def test_modal_breaks_ties_by_first_occurrence():
    # Two equally-likely samples → the first emitted wins, deterministically.
    dist = ReactionDistribution(
        samples=[
            ReactionSample(text="first", probability=1.0),
            ReactionSample(text="second", probability=1.0),
        ],
        temperature=1.0,
    )
    assert dist.modal.text == "first"


def test_empty_samples_is_rejected():
    with pytest.raises(ValueError):
        ReactionDistribution(samples=[], temperature=0.0)


def test_zero_probability_sample_is_rejected_at_the_sample_level():
    # gt=0 at the sample guards the sum-to-1 normalization from dividing nothing.
    with pytest.raises(ValueError):
        ReactionSample(text="x", probability=0.0)


# ── elicitor: k == 1 reduces to the historical single chat() call ─────────────


def test_single_sample_uses_plain_chat_and_yields_probability_one():
    chat = _RecordingChat(text_result="my one reaction")
    dist = elicit_reaction_distribution(
        chat,
        system_prompt="SYS",
        user_turn="react",
        samples=1,
        temperature=0.0,
    )

    assert len(chat.calls) == 1
    call = chat.calls[0]
    assert call["kind"] == "chat"  # NOT chat_json — no verbalized-sampling wrapper
    assert call["temperature"] == 0.0
    assert call["messages"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "react"},  # base user turn passed through verbatim
    ]
    assert len(dist.samples) == 1
    assert dist.samples[0].text == "my one reaction"
    assert dist.samples[0].probability == pytest.approx(1.0)
    assert dist.modal.text == "my one reaction"
    assert dist.temperature == 0.0


def test_single_sample_threads_raised_temperature_and_seed():
    chat = _RecordingChat(text_result="r")
    elicit_reaction_distribution(
        chat, system_prompt="S", user_turn="u", samples=1, temperature=1.1, seed=42
    )
    assert chat.calls[0]["temperature"] == 1.1
    assert chat.calls[0]["seed"] == 42


# ── elicitor: k > 1 verbalized sampling ───────────────────────────────────────


def test_multi_sample_uses_chat_json_and_normalizes():
    chat = _RecordingChat(json_result=_vs(("calm take", 3.0), ("annoyed take", 1.0)))
    dist = elicit_reaction_distribution(
        chat,
        system_prompt="SYS",
        user_turn="react",
        samples=2,
        temperature=0.9,
    )

    assert len(chat.calls) == 1
    call = chat.calls[0]
    assert call["kind"] == "chat_json"
    assert call["schema"] is _VerbalizedSampling
    assert call["temperature"] == 0.9
    # base user turn is preserved inside the verbalized-sampling wrapper
    assert "react" in call["messages"][1]["content"]
    assert "DISTINCT" in call["messages"][1]["content"]

    assert [s.text for s in dist.samples] == ["calm take", "annoyed take"]
    assert [s.probability for s in dist.samples] == pytest.approx([0.75, 0.25])
    assert dist.modal.text == "calm take"
    assert dist.temperature == 0.9


def test_multi_sample_filters_blank_and_nonpositive_entries():
    chat = _RecordingChat(
        json_result=_vs(("  ", 0.5), ("real", 2.0), ("zero-weight", 0.0), ("neg", -1.0))
    )
    dist = elicit_reaction_distribution(
        chat, system_prompt="S", user_turn="u", samples=4, temperature=0.8
    )
    # only the one usable reaction survives; it normalizes to probability 1.0
    assert [s.text for s in dist.samples] == ["real"]
    assert dist.samples[0].probability == pytest.approx(1.0)


def test_multi_sample_strips_whitespace_from_reactions():
    chat = _RecordingChat(json_result=_vs(("  padded  ", 1.0)))
    dist = elicit_reaction_distribution(
        chat, system_prompt="S", user_turn="u", samples=2, temperature=0.8
    )
    assert dist.samples[0].text == "padded"


def test_multi_sample_all_unusable_raises():
    chat = _RecordingChat(json_result=_vs(("", 1.0), ("   ", 2.0)))
    with pytest.raises(ValueError, match="no usable reactions"):
        elicit_reaction_distribution(
            chat, system_prompt="S", user_turn="u", samples=2, temperature=0.8
        )


def test_samples_below_one_raises():
    chat = _RecordingChat(text_result="r")
    with pytest.raises(ValueError, match="samples must be >= 1"):
        elicit_reaction_distribution(
            chat, system_prompt="S", user_turn="u", samples=0, temperature=0.0
        )
