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


def test_early_word_boundary_preferred_over_mid_token_slice() -> None:
    """Codex #84 round-1 P2: when the only word boundary in the truncated
    prefix is early (before the half-way mark), we MUST still use it
    rather than slice mid-word. The earlier `cut > MAX//2` gate produced
    a broken-token suffix for `Short <very-long-token>` style reactions."""
    long_token = "supercalifragilisticexpialidocious" * 5  # >120 chars
    out = _derive_top_quote("Short " + long_token + ".")
    assert out.endswith("…")
    # Must NOT contain any portion of the long token (only the early
    # word-boundary chunk plus ellipsis).
    assert long_token[:30] not in out
    assert out.startswith("Short")


def test_truncation_falls_back_to_hard_cut_when_no_spaces() -> None:
    """If the first sentence contains literally no whitespace, we have
    no boundary — hard-cut at MAX with ellipsis is the right answer."""
    no_spaces = "x" * 300
    out = _derive_top_quote(no_spaces + ".")
    assert out.endswith("…")
    assert len(out) <= 120
    assert out.rstrip("…").strip() == "x" * (len(out) - 1)
