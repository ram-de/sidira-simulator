"""Unit tests for services.persona_group_collective.

Pin the service contract independently from the API tests:
  - Never raises into the route (LLM exception → deterministic fallback).
  - References resolve only LLM-cited labels that exist in the input.
  - Hallucinated labels appear in content but NOT references.
  - Empty replies / empty agents are handled defensively.
  - Multi-turn: prior_conversation passes through into the LLM input.

The API tests already cover route behaviour; these tests pin the SERVICE
layer so future refactors don't drift.
"""

from __future__ import annotations

from pythia_simulator.services.persona_group_collective import (
    CollectiveAgentContext,
    PersonaGroupCollectiveService,
    build_identity_seed_summary,
)


class _ScriptedChat:
    """Returns canned strings in order; an entry typed as Exception is raised."""

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


def _ctx(label: str, agent_id: str = "") -> CollectiveAgentContext:
    return CollectiveAgentContext(
        agent_id=agent_id or f"id-{label}",
        agent_label=label,
        persona_name="Late-night premium",
        identity_seed_summary="age 25-34; urban; tenure 1-3y",
        initial_reaction="I'd give it a shot.",
    )


# ───────────────────────────────────────────────────────────────────────
# Reference resolution
# ───────────────────────────────────────────────────────────────────────


def test_resolves_every_cited_label_in_input() -> None:
    """Every `[label]` in the prose that matches an input agent gets a
    canonical agent_id in references."""
    chat = _ScriptedChat(
        ["Two pushed back — [maya_a] said X, [maya_b] said Y. [maya_c] was fine."]
    )
    svc = PersonaGroupCollectiveService(chat_client=chat)
    content, refs = svc.collective_reply(
        persona_name="Late-night premium",
        pm_question="Who reacted negatively?",
        agents=[
            _ctx("maya_a", agent_id="uuid-a"),
            _ctx("maya_b", agent_id="uuid-b"),
            _ctx("maya_c", agent_id="uuid-c"),
        ],
        prior_conversation=[],
    )
    assert "[maya_a]" in content
    assert {r.agent_label for r in refs} == {"maya_a", "maya_b", "maya_c"}
    assert {r.agent_id for r in refs} == {"uuid-a", "uuid-b", "uuid-c"}


def test_hallucinated_label_appears_in_content_but_not_references() -> None:
    """If the LLM cites a name not in the input, it survives in the prose
    (we don't post-process the LLM output) but does NOT get a reference,
    so the frontend renders it as plain text — no broken link."""
    chat = _ScriptedChat(
        ["[maya_a] said X. [made_up_name] said something we never told the model."]
    )
    svc = PersonaGroupCollectiveService(chat_client=chat)
    content, refs = svc.collective_reply(
        persona_name="Late-night premium",
        pm_question="?",
        agents=[_ctx("maya_a")],
        prior_conversation=[],
    )
    assert "[made_up_name]" in content
    assert [r.agent_label for r in refs] == ["maya_a"]


def test_repeated_label_dedupes_in_references() -> None:
    """A label cited twice in the prose appears once in references."""
    chat = _ScriptedChat(["[maya_a] said X. [maya_a] also said Y."])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    _, refs = svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[_ctx("maya_a")],
        prior_conversation=[],
    )
    assert len(refs) == 1
    assert refs[0].agent_label == "maya_a"


def test_no_citations_returns_empty_references() -> None:
    """An LLM reply with no `[label]` tokens produces empty references."""
    chat = _ScriptedChat(["We're all on the same page about this change."])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    content, refs = svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[_ctx("a"), _ctx("b")],
        prior_conversation=[],
    )
    assert refs == []
    assert content.startswith("We're all on the same page")


def test_malformed_citation_tokens_are_not_resolved() -> None:
    """Tokens that don't match the `\\[\\w\\-+\\]` shape (e.g. `[the second agent]`
    with whitespace) are ignored — only proper labels resolve. Prevents
    the LLM from accidentally inventing a "linkable" name by wrapping
    English prose in brackets."""
    chat = _ScriptedChat(
        ["[maya_a] said X. [the second agent] said Y. [a label with spaces] said Z."]
    )
    svc = PersonaGroupCollectiveService(chat_client=chat)
    _, refs = svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[_ctx("maya_a")],
        prior_conversation=[],
    )
    # Only the well-formed token resolves
    assert [r.agent_label for r in refs] == ["maya_a"]


# ───────────────────────────────────────────────────────────────────────
# Never-raises contract
# ───────────────────────────────────────────────────────────────────────


def test_llm_exception_returns_deterministic_fallback(caplog) -> None:
    """The route depends on this: an LLM exception MUST NOT raise out of
    the service. Codex #80 P1 lesson — a 500 here would invite a client
    retry that doubles down on upstream work."""
    chat = _ScriptedChat([TimeoutError("simulated")])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    content, refs = svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[_ctx("a"), _ctx("b")],
        prior_conversation=[],
    )
    assert "collective voice is unavailable" in content
    assert "2 agents in this group" in content
    assert refs == []


def test_empty_agents_returns_safe_default_without_llm_call() -> None:
    """Defensive: route guards against this too, but the service must not
    call the LLM with zero context."""
    chat = _ScriptedChat([])  # would raise if asked
    svc = PersonaGroupCollectiveService(chat_client=chat)
    content, refs = svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[],
        prior_conversation=[],
    )
    assert "No agents available" in content
    assert refs == []
    assert chat.calls == []


# ───────────────────────────────────────────────────────────────────────
# Multi-turn (prior_conversation passes through)
# ───────────────────────────────────────────────────────────────────────


def test_prior_conversation_renders_into_user_message() -> None:
    """Multi-turn collective chats require the LLM to see prior PM + collective
    turns. Assert prior content appears in the user message blob."""
    chat = _ScriptedChat(["[a] said something now."])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    svc.collective_reply(
        persona_name="P",
        pm_question="What about now?",
        agents=[_ctx("a")],
        prior_conversation=[
            ("pm", "EARLIER_PM_TURN_CONTENT"),
            ("collective", "EARLIER_COLLECTIVE_REPLY_CONTENT"),
        ],
    )
    user_msg = next(m["content"] for m in chat.calls[0] if m["role"] == "user")
    assert "EARLIER_PM_TURN_CONTENT" in user_msg
    assert "EARLIER_COLLECTIVE_REPLY_CONTENT" in user_msg
    # Current turn's question is present too
    assert "What about now?" in user_msg


def test_first_turn_renders_no_prior_block() -> None:
    """When prior_conversation is empty, the user message should still be
    coherent — no 'None' or empty-block artifacts that would confuse the LLM."""
    chat = _ScriptedChat(["[a] reply."])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[_ctx("a")],
        prior_conversation=[],
    )
    user_msg = next(m["content"] for m in chat.calls[0] if m["role"] == "user")
    assert "no prior turns" in user_msg


# ───────────────────────────────────────────────────────────────────────
# Prompt shape invariants
# ───────────────────────────────────────────────────────────────────────


def test_system_prompt_instructs_collective_voice() -> None:
    """The collective system prompt must tell the model it's speaking AS
    the group, NOT as one individual. Catches regressions where the prompt
    drifts toward single-agent framing."""
    chat = _ScriptedChat(["[a] reply."])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    svc.collective_reply(
        persona_name="P",
        pm_question="?",
        agents=[_ctx("a")],
        prior_conversation=[],
    )
    system_msg = next(m["content"] for m in chat.calls[0] if m["role"] == "system")
    # Voice-of-group framing
    assert "speak in the voice of a PERSONA GROUP" in system_msg
    # Anti-individual guard
    assert "ONE voice" in system_msg
    # Citation convention is taught
    assert "[agent_label]" in system_msg


def test_user_message_includes_every_agent_label_and_identity() -> None:
    """Every agent in the input must appear in the agents_block so the LLM
    knows the full membership of the group it's speaking for."""
    chat = _ScriptedChat(["[a] [b] [c] reply."])
    svc = PersonaGroupCollectiveService(chat_client=chat)
    svc.collective_reply(
        persona_name="Late-night",
        pm_question="?",
        agents=[
            _ctx("alpha"),
            _ctx("bravo"),
            _ctx("charlie"),
        ],
        prior_conversation=[],
    )
    user_msg = next(m["content"] for m in chat.calls[0] if m["role"] == "user")
    for label in ("alpha", "bravo", "charlie"):
        assert f"[{label}]" in user_msg
    # The identity_seed summary token shows up (from the _ctx default summary)
    assert "age 25-34" in user_msg


# ───────────────────────────────────────────────────────────────────────
# build_identity_seed_summary helper
# ───────────────────────────────────────────────────────────────────────


def test_build_identity_seed_summary_omits_none_fields() -> None:
    """A persona without an identity_seed shouldn't render 'None' as noise."""
    out = build_identity_seed_summary(
        age_band="25-34",
        locale_band=None,
        tenure_band=None,
        current_state="lunch break",
        recent_gripe=None,
    )
    assert "None" not in out
    assert "age 25-34" in out
    assert "currently: lunch break" in out


def test_build_identity_seed_summary_all_none() -> None:
    out = build_identity_seed_summary(None, None, None, None, None)
    assert out == "(no identity seed)"
