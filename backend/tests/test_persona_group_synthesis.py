"""Tests for services.persona_group_synthesis (#54).

Two layers:

1. **Unit tests** (always run) — exercise the post-process retry/fallback
   logic with a deterministic stub LLM. These pin the SERVICE contract
   regardless of LLM quality: count-mismatch triggers retry, second mismatch
   triggers deterministic fallback, count-correct outputs pass through.

2. **Rubric eval** (gated behind `PYTHIA_RUN_LLM_EVALS=1` env var) — runs the
   real LLM against 10 fixture scenarios and asserts trait-level rubric: must
   contain "N of M" or "N agents split" or non-substantive diagnostic; must
   not hedge ("mixed", "varied", etc.); must not editorialize. Cost per run:
   ~10 calls × ~$0.005 = ~$0.05. Run pre-PR or on prompt iteration.

See `docs/54-synthesis-quality-bar.md` for the locked design.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

import pytest

from pythia_simulator.services.persona_group_synthesis import (
    AgentReply,
    PersonaGroupSynthesisService,
)

# Phrases the synthesis MUST NOT use. Global blocklist; every fixture
# enforces it. Mirrors the negative templates in prompt_composer (#77).
_BANNED_PHRASES = [
    "mixed feelings",
    "overall",
    "somewhat",
    "generally",
    "this suggests",
    "indicates",
    "notably",
    "interestingly",
    "it appears",
    "the majority",
    "most agents",
    "some agents",
    "a few",
    "varied",
]


# ───────────────────────────────────────────────────────────────────────
# Layer 1 — unit tests on the service contract (stub LLM, always run)
# ───────────────────────────────────────────────────────────────────────


class _ScriptedChat:
    """Returns canned replies in order; an entry typed as Exception is raised
    instead of returned. Records each call's messages."""

    def __init__(self, replies: list[str | Exception]) -> None:
        self._replies = list(replies)
        self.calls: list[list[dict[str, str]]] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(messages)
        if not self._replies:
            raise AssertionError("_ScriptedChat ran out of replies")
        nxt = self._replies.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def chat_json(self, *a, **kw):  # pragma: no cover - unused
        raise NotImplementedError


def _reply(label: str, content: str) -> AgentReply:
    return AgentReply(agent_label=label, content=content)


def test_count_correct_first_try_returns_immediately() -> None:
    """When the LLM nails the count on attempt 1, no retry is fired."""
    chat = _ScriptedChat(["3 of 3 said the rail removal would break Friday."])
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "Walk me through Friday.",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 of 3 said the rail removal would break Friday."
    assert len(chat.calls) == 1


def test_count_mismatch_triggers_retry_then_accepts_corrected_count() -> None:
    """Codex-style P1: a wrong-count first output is recoverable via retry."""
    chat = _ScriptedChat(
        [
            "3 of 5 said the rail removal would break Friday.",  # wrong denom
            "3 of 3 said the rail removal would break Friday.",  # corrected
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "Walk me through Friday.",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 of 3 said the rail removal would break Friday."
    assert len(chat.calls) == 2
    # The retry message must include the actual count to make the constraint
    # impossible for the model to miss.
    retry_messages = chat.calls[1]
    assert any("3" in m["content"] for m in retry_messages if m["role"] == "system")


def test_double_mismatch_falls_back_to_deterministic_template(caplog) -> None:
    """If retry also hallucinates the count, fall back to a deterministic
    count-correct sentence rather than ship a fluent-but-wrong synthesis."""
    chat = _ScriptedChat(
        [
            "3 of 5 said X.",
            "2 of 7 said Y.",  # retry still wrong
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "Q?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 agents replied — see individual answers below."
    assert len(chat.calls) == 2


def test_split_form_passes_count_check() -> None:
    """The 'N agents split' shape is a valid count-claim."""
    chat = _ScriptedChat(
        ["3 agents split: a said X, b said Y, c said Z."]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert "split" in out
    assert len(chat.calls) == 1


def test_non_substantive_form_passes_count_check() -> None:
    """The diagnostic shape for evasive replies is a valid output."""
    chat = _ScriptedChat(
        ["3 agents gave non-substantive replies - re-ask with more specificity."]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "I'm not sure"), _reply("b", "no idea"), _reply("c", "maybe")],
    )
    assert "non-substantive" in out
    assert len(chat.calls) == 1


def test_zero_replies_returns_safe_default_without_llm_call() -> None:
    """Defensive: an empty fan-out should not call the LLM at all."""
    chat = _ScriptedChat([])  # would raise if asked
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize("?", [])
    assert "No agent replies" in out
    assert chat.calls == []


def test_split_form_with_wrong_count_triggers_retry() -> None:
    """'4 agents split' for n=3 must be caught by the count check."""
    chat = _ScriptedChat(
        [
            "4 agents split: a, b, c, d.",  # wrong N
            "3 agents split: a said X, b said Y, c said Z.",
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out.startswith("3 agents split:")
    assert len(chat.calls) == 2


def test_outputless_first_response_triggers_retry() -> None:
    """If the LLM dodges the counted-shape rule entirely (no 'N of M', no
    'N agents split', no 'non-substantive'), that's also a count-mismatch."""
    chat = _ScriptedChat(
        [
            "The agents had a range of opinions about the change.",  # no count
            "3 of 3 said X.",
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 of 3 said X."
    assert len(chat.calls) == 2


def test_llm_exception_on_first_call_falls_back_without_raising(caplog) -> None:
    """Codex #80 [P1]: an exception from _call_llm MUST NOT propagate. If it
    did, the route would 500 AFTER per-agent fan-out has persisted PM/agent
    turns, and a client retry would duplicate every successful agent's
    conversation. The synthesis is downstream; degrade it to the
    deterministic fallback rather than corrupt the per-agent logs."""
    chat = _ScriptedChat(
        [
            TimeoutError("synthesis LLM timed out"),
            TimeoutError("retry also timed out"),
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 agents replied — see individual answers below."
    assert len(chat.calls) == 2  # first + retry both attempted


def test_llm_exception_on_first_call_retry_succeeds() -> None:
    """First call raises, retry returns a count-correct answer → ship the retry.
    No reason to fall back further than necessary."""
    chat = _ScriptedChat(
        [
            TimeoutError("transient timeout"),
            "3 of 3 said the change matters.",
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 of 3 said the change matters."
    assert len(chat.calls) == 2


def test_llm_exception_only_on_retry_falls_back() -> None:
    """First call returns a wrong-count answer, retry raises → fall back to
    deterministic. The first wrong-count answer is still wrong; we don't want
    to ship it because we ran out of retries."""
    chat = _ScriptedChat(
        [
            "2 of 7 said X.",  # wrong denom
            RuntimeError("retry blew up"),
        ]
    )
    svc = PersonaGroupSynthesisService(chat_client=chat)
    out = svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    assert out == "3 agents replied — see individual answers below."
    assert len(chat.calls) == 2


def test_prompt_includes_negative_templates() -> None:
    """The system prompt must list banned hedges so the LLM has explicit
    targets to avoid (mirror of #77's anti-template approach)."""
    chat = _ScriptedChat(["3 of 3 said X."])
    svc = PersonaGroupSynthesisService(chat_client=chat)
    svc.synthesize(
        "?",
        [_reply("a", "x"), _reply("b", "y"), _reply("c", "z")],
    )
    system_msg = chat.calls[0][0]
    assert system_msg["role"] == "system"
    # The four global hedges that show up most often in templated LLM output
    for phrase in ["mixed", "varied", "this suggests", "interestingly"]:
        assert phrase in system_msg["content"], (
            f"system prompt missing banned-phrase guard for {phrase!r}"
        )


def test_prompt_includes_reply_count_and_labels() -> None:
    """The user message must surface N + labelled replies so the LLM has
    deterministic anchors for its 'N of M' line."""
    chat = _ScriptedChat(["2 of 2 said X."])
    svc = PersonaGroupSynthesisService(chat_client=chat)
    svc.synthesize(
        "What about Friday?",
        [_reply("rivka_001", "We always scroll together."), _reply("rivka_002", "Same.")],
    )
    user_msg = chat.calls[0][1]
    assert user_msg["role"] == "user"
    assert "N=2" in user_msg["content"]
    assert "[rivka_001]:" in user_msg["content"]
    assert "[rivka_002]:" in user_msg["content"]
    assert "What about Friday?" in user_msg["content"]


# ───────────────────────────────────────────────────────────────────────
# Layer 2 — LLM rubric eval (gated; the pre-ship gate per design doc)
# ───────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class SynthesisFixture:
    """One eval scenario: PM question + canned agent replies + rubric."""

    name: str
    pm_question: str
    replies: list[AgentReply]
    must_match_any: list[str]  # regex patterns; at least one must match
    must_contain_any: list[str]  # at least one of these substrings (case-insensitive)
    must_not_contain: list[str]  # in addition to the global banned list
    max_sentences: int = 2


# Synthetic but realistic fixtures spanning every shape we expect in
# production. Reply text is short on purpose so the LLM input stays cheap.
_FIXTURES: list[SynthesisFixture] = [
    SynthesisFixture(
        name="unanimous_negative",
        pm_question="What happens to your Friday family movie ritual if the Continue Watching rail is removed?",
        replies=[
            _reply(
                "rivka_001",
                "We always scroll the row together. If it's gone we'll just watch The Office reruns again.",
            ),
            _reply(
                "rivka_002",
                "The whole point is browsing as a family — one hero card kills that.",
            ),
            _reply(
                "rivka_003",
                "My kids pick from that row. Without it, I'd have to type and they can't read fast enough.",
            ),
        ],
        must_match_any=[r"\b3\s+of\s+3\b"],
        must_contain_any=["family", "ritual", "row", "together", "browsing"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="unanimous_positive",
        pm_question="Would a one-tap reorder banner help you?",
        replies=[
            _reply("sam_a", "Yes — I order the same lunch 3x a week. Saves 4 taps."),
            _reply("sam_b", "Huge. My weekday default is the same burrito."),
            _reply("sam_c", "Finally. Reorder is buried in profile right now."),
        ],
        must_match_any=[r"\b3\s+of\s+3\b"],
        must_contain_any=["reorder", "default", "save", "fewer taps", "tap", "weekday"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="split_with_named_causes",
        pm_question="How does the new Smart Resume hero change your home-screen experience?",
        replies=[
            _reply("a", "Faster — I just want to keep watching, not browse."),
            _reply("b", "Faster — one tap and I'm back in the episode."),
            _reply("c", "Faster but I miss discovering new things."),
            _reply("d", "Worse — I scroll Continue Watching to remember what I half-watched."),
            _reply("e", "Worse — the hero locks me into one show; I want options."),
        ],
        must_match_any=[r"\b3\s+of\s+5\b", r"\b5\s+agents\s+split\b"],
        must_contain_any=["faster", "discover", "scroll", "options"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="outlier_4_vs_1",
        pm_question="Would removing the promo banner from checkout change your behavior?",
        replies=[
            _reply("dom_a", "I don't notice the banner. No impact."),
            _reply("dom_b", "Never click it. Wouldn't miss it."),
            _reply("dom_c", "Doesn't affect me — I order from saved restaurants."),
            _reply("dom_d", "Fine by me. I find promos via push, not checkout."),
            _reply(
                "dom_e",
                "I'd order less. That banner is how I find out about the 30% Sunday promo every week.",
            ),
        ],
        must_match_any=[r"\b4\s+of\s+5\b"],
        must_contain_any=["dom_e", "promo", "Sunday", "30%", "weekly", "find"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="three_way_split",
        pm_question="What's the right default tip percentage?",
        replies=[
            _reply("a", "15%. 18-20 is for sit-down service, not delivery."),
            _reply("b", "20%. Couriers do real work in bad weather."),
            _reply("c", "0%. Tipping should be opt-in, not pre-filled at all."),
        ],
        must_match_any=[r"\b3\s+agents\s+split\b"],
        must_contain_any=["15", "20", "0", "opt-in", "default", "pre-fill"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="same_polarity_different_cause",
        pm_question="Why might you cancel your subscription this month?",
        replies=[
            _reply("a", "Price went up and nothing else changed."),
            _reply("b", "I stopped watching after they removed my shows."),
            _reply("c", "The new UI is hostile — I can't find anything."),
            _reply("d", "I'm switching to a competitor with live sports."),
        ],
        must_match_any=[r"\b4\s+agents\s+split\b", r"\b4\s+of\s+4\b"],
        must_contain_any=["price", "shows", "UI", "competitor", "live sports", "different"],
        # Must NOT collapse all four into "negative sentiment"
        must_not_contain=["all four negative", "all four said"],
    ),
    SynthesisFixture(
        name="non_substantive_replies",
        pm_question="What specifically would you change about the checkout flow?",
        replies=[
            _reply("a", "I'm not sure."),
            _reply("b", "Hmm, hard to say without thinking about it more."),
            _reply("c", "I haven't really thought about it."),
        ],
        must_match_any=[r"\b3\s+agents\s+gave\s+non-substantive"],
        must_contain_any=["non-substantive", "re-ask", "specificity"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="one_long_one_short",
        pm_question="Is the new search bar an improvement?",
        replies=[
            _reply(
                "a",
                "Yes and also it took me a while to find — the icon used to be on the left, now it's a magnifying glass in the top-right, which is fine but I clicked the avatar three times first. Once I found it, the autocomplete is faster than before and the typo handling is much better. I tried 'guacomole' and it found guacamole, which the old one didn't. So overall I think it's an improvement, especially for typos.",
            ),
            _reply("b", "Faster."),
        ],
        must_match_any=[r"\b2\s+of\s+2\b"],
        must_contain_any=["faster", "search", "improvement"],
        # Must not just paraphrase the long one and ignore the short one
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="agent_referenced_specific_flow",
        pm_question="What do you think of the new compose-then-send flow?",
        replies=[
            _reply("a", "It's fine — same number of taps."),
            _reply("b", "Better, because the draft sticks if I background the app."),
            _reply(
                "c",
                "I noticed the Send button in component `cta_primary` is now disabled until the text field is non-empty — that's the part I actually like.",
            ),
        ],
        must_match_any=[r"\b3\s+of\s+3\b", r"\b2\s+of\s+3\b"],
        # The synthesis should surface SOMETHING specific (the draft behavior,
        # or the disabled-send behavior). Pure "they liked it" loses that.
        must_contain_any=["draft", "Send", "cta_primary", "disabled", "background"],
        must_not_contain=[],
    ),
    SynthesisFixture(
        name="agent_self_contradicted",
        pm_question="Would you pay extra for priority delivery?",
        replies=[
            _reply(
                "a",
                "Yeah I'd pay. I mean — it depends. If it's more than $2 probably not. But for a couple bucks yes, especially on Fridays.",
            ),
            _reply("b", "Yes, $2-3 feels right."),
            _reply("c", "Yes, especially for groceries."),
        ],
        must_match_any=[r"\b3\s+of\s+3\b"],
        must_contain_any=["$2", "$3", "Friday", "grocer", "pay", "yes"],
        must_not_contain=[],
    ),
]


_LLM_EVAL_REASON = (
    "Set PYTHIA_RUN_LLM_EVALS=1 to run the synthesis rubric against the real "
    "LLM. Cost: ~10 calls × ~$0.005 ≈ $0.05 per run. Required pre-ship gate "
    "for #54; skip in default CI to avoid spurious failures from network or "
    "rate-limit issues."
)


@pytest.mark.skipif(
    not os.environ.get("PYTHIA_RUN_LLM_EVALS"),
    reason=_LLM_EVAL_REASON,
)
@pytest.mark.parametrize("fixture", _FIXTURES, ids=[f.name for f in _FIXTURES])
def test_synthesis_rubric(fixture: SynthesisFixture) -> None:
    """Per-fixture rubric eval against the real LLM."""
    svc = PersonaGroupSynthesisService()
    out = svc.synthesize(fixture.pm_question, fixture.replies)

    # 1. Counted shape — at least one of the allowed regex anchors matches.
    if fixture.must_match_any:
        assert any(re.search(p, out, re.IGNORECASE) for p in fixture.must_match_any), (
            f"[{fixture.name}] output {out!r} matched none of "
            f"{fixture.must_match_any}"
        )

    # 2. At least one of the expected cause-nouns appears (case-insensitive).
    if fixture.must_contain_any:
        lowered = out.lower()
        assert any(s.lower() in lowered for s in fixture.must_contain_any), (
            f"[{fixture.name}] output {out!r} contained none of "
            f"{fixture.must_contain_any} — synthesis is too generic"
        )

    # 3. Global hedge / editorial filler blocklist + per-fixture extras.
    lowered = out.lower()
    for phrase in _BANNED_PHRASES + fixture.must_not_contain:
        assert phrase.lower() not in lowered, (
            f"[{fixture.name}] output {out!r} contained banned phrase "
            f"{phrase!r}"
        )

    # 4. Length cap (proxy: at most max_sentences sentence-ending punctuation).
    sentence_count = sum(out.count(end) for end in (".", "!", "?"))
    assert sentence_count <= fixture.max_sentences, (
        f"[{fixture.name}] output {out!r} has {sentence_count} sentences; "
        f"max is {fixture.max_sentences}"
    )
