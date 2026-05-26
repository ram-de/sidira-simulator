"""Unit tests for the top-quote derivation helper used by #51.

`_derive_top_quote` is a pure function — straightforward to pin so future
refactors don't drift the result-table quote heuristic.
"""

from __future__ import annotations

from pythia_simulator.services.simulation_runner import _derive_top_quote


def test_first_sentence_period() -> None:
    out = _derive_top_quote(
        "I'd give it a shot. The reorder banner sounds useful for premium users."
    )
    assert out == "I'd give it a shot."


def test_first_sentence_question_mark() -> None:
    out = _derive_top_quote(
        "Why would I want this? It's just one more banner I'd scroll past."
    )
    assert out == "Why would I want this?"


def test_first_sentence_exclamation() -> None:
    out = _derive_top_quote(
        "Finally! That saves me real time on Tuesday lunches.",
    )
    assert out == "Finally!"


def test_no_terminator_returns_whole_text_if_short() -> None:
    out = _derive_top_quote("Yeah I'd use it")
    assert out == "Yeah I'd use it"


def test_no_terminator_truncates_long_text_at_word_boundary() -> None:
    text = " ".join(["word"] * 80)  # ~399 chars
    out = _derive_top_quote(text)
    assert out.endswith("…")
    assert len(out) <= 120
    # Truncation should land on a word boundary, not mid-word.
    assert " " in out or out.startswith("word")
    # First char must still be from the original text.
    assert out.startswith("word")


def test_empty_string_returns_empty() -> None:
    assert _derive_top_quote("") == ""


def test_whitespace_only_returns_empty() -> None:
    assert _derive_top_quote("   \n\t  ") == ""


def test_strips_leading_and_trailing_whitespace() -> None:
    out = _derive_top_quote("   Hello world.   ")
    assert out == "Hello world."


def test_first_sentence_when_multiple_terminators_picks_earliest() -> None:
    """A period earlier than a question mark wins."""
    out = _derive_top_quote("This is fine. But why? And also!")
    assert out == "This is fine."


def test_very_long_first_sentence_is_truncated_with_ellipsis() -> None:
    sentence = "I have a lot to say about this and I'll just keep going forever because the persona prompt told me to ground my opener in something concrete from my identity_seed which means I should mention my recent gripe about the deals tab"
    out = _derive_top_quote(sentence + ".")
    assert out.endswith("…")
    assert len(out) <= 120


def test_short_reaction_returns_first_sentence_unchanged() -> None:
    out = _derive_top_quote("OK.")
    assert out == "OK."
