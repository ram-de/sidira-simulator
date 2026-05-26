"""Persona-group collective reply (#54 collective mode).

Single LLM call that answers in the voice of the persona group as a whole.
Used when the PM asks meta questions ("what's the consensus?", "who reacted
negatively?") that don't make sense to fan out to individual agents (each
individual can't honestly characterize a group from their own POV).

Design (`docs/agent-chat-ui-spec.md` Surface 2 § Two modes):
  - One LLM call per turn regardless of N.
  - The model receives the persona description + every agent's identity_seed
    + every agent's initial_reaction + the prior collective conversation log.
  - The model is instructed to cite individuals with `[agent_label]` tokens
    when making claims attributable to them. The route resolves those tokens
    to `agent_id`s so the frontend can render them as drill-down links.
  - Service contract: NEVER raises into the route. LLM exceptions degrade
    to a deterministic fallback line; reference-resolution issues degrade to
    content-only (no broken links).

The collective surface is downstream of any per-agent state — failures here
must never invite a client retry that re-runs upstream work. Same lesson as
the #54 codex P1 fix on the synthesis service.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from pythia_simulator.adapters.llm import ChatClient, get_chat_client
from pythia_simulator.schemas.persona_group import AgentReference

log = structlog.get_logger()


@dataclass(frozen=True)
class CollectiveAgentContext:
    """One agent's frozen context the collective LLM sees as input.

    `agent_label` is the inline-citation token the LLM is instructed to use
    when referencing this specific agent. `agent_id` is the canonical id the
    route uses to resolve references for the frontend.
    """

    agent_id: str
    agent_label: str
    persona_name: str
    identity_seed_summary: str  # short prose (age / locale / tenure / current / gripe)
    initial_reaction: str  # verbatim from the simulation


# Allowed forms for the `[label]` citation token. We anchor on word chars,
# digits, underscore, and dash so persona-id-derived labels (rivka_001,
# maya_a, dom-restaurant) all match. NO whitespace, NO punctuation, so a
# malformed prose like "[the second agent]" cannot be resolved (which is
# correct — only proper labels become links).
_CITATION_RE = re.compile(r"\[([\w\-]+)\]")


_SYSTEM_PROMPT = """You speak in the voice of a PERSONA GROUP — a collective of {n} agents who all match the same persona definition. The product manager has been asking the simulation about a hypothesis. Now they're asking the group a question.

Your job: answer as the collective. ONE voice that represents the whole group, NOT a list of individual replies (that's a different surface; the PM uses it explicitly when they want it).

You will receive:
- The persona description.
- Every agent's identity_seed (age band, locale, tenure, current state, recent gripe).
- Every agent's initial reaction to the hypothesis (verbatim from simulation time).
- The prior collective conversation (PM turns and your prior collective replies).

When you make a claim attributable to a specific individual in the group, CITE them with their `[agent_label]` token. Use ONLY the labels you were given. Don't invent labels.

Examples of good collective replies (with citation):
- "Two of us pushed back — [rivka_001] said the family browsing ritual is the point and a hero card kills it, and [rivka_002] said the kid-profile shortcut sits in that rail. [rivka_003] was OK with the change since they use voice search anyway."
- "We're split. [maya_a] and [maya_b] welcomed the late-night smart resume; [maya_c] said it made the home screen feel emptier."
- "All three of us said the same thing in different words: the deals tab is the primary attraction on Tuesday lunches. Reorder feels secondary."

Do NOT:
- Refuse the question or break character.
- Speak as a single individual ("I think...") — you're speaking AS THE GROUP.
- Invent agent labels not in the input.
- Wrap a label in quotes or add prose inside the brackets — write `[rivka_001]`, not `["rivka_001"]` or `[the rivka_001 agent]`.
- Hallucinate quotes; ground every cited claim in something the agent's identity_seed or initial_reaction supports.

If the PM asks a question the input doesn't support answering (e.g. "what did you do last weekend?" with no relevant signal), say so honestly as the group: "We don't have enough signal in our reactions to answer that — try asking about the hypothesis itself."

Keep replies tight: 2-4 sentences. The PM will follow up if they want more depth or drill into individuals."""


_AGENT_CONTEXT_TEMPLATE = """[{label}] ({persona_name})
  identity: {identity_summary}
  initial reaction: {initial_reaction}"""


_USER_TEMPLATE = """Persona: {persona_name}
N = {n}

Agents in this group:
{agents_block}

Prior collective conversation:
{prior_conversation}

PM question:
{pm_question}"""


class PersonaGroupCollectiveService:
    """Generates collective-voice replies for persona-group chat."""

    def __init__(self, chat_client: ChatClient | None = None) -> None:
        self._chat = chat_client or get_chat_client()

    def collective_reply(
        self,
        *,
        persona_name: str,
        pm_question: str,
        agents: list[CollectiveAgentContext],
        prior_conversation: list[tuple[str, str]],
    ) -> tuple[str, list[AgentReference]]:
        """Generate one collective-voice reply + resolved references.

        Args:
          persona_name: human-readable name shown in prompts.
          pm_question: the PM's latest message.
          agents: every agent in the persona group, with frozen context.
          prior_conversation: list of (role, content) tuples where role is
            either "pm" or "collective". Used to give the LLM context across
            multi-turn collective chats.

        Returns:
          `(content, references)` — content is the LLM prose (may contain
          `[label]` tokens); references resolves every label that appears
          BOTH inline AND in the agent input to its canonical agent_id.
          Tokens that don't resolve (hallucinated labels) appear in `content`
          but NOT in `references` — the frontend renders them as plain text.

        Behaviour contract:
          - NEVER raises. LLM exception → deterministic fallback line +
            empty references + structlog warn.
          - Empty agents list → safe default (route should guard, but we do
            too).
        """
        if not agents:
            return (
                "No agents available in this persona group — re-run the "
                "simulation.",
                [],
            )

        try:
            content = self._call_llm(
                persona_name=persona_name,
                pm_question=pm_question,
                agents=agents,
                prior_conversation=prior_conversation,
            )
        except Exception as exc:  # noqa: BLE001 — never raise into the route
            log.warning(
                "collective.llm_call_failed",
                persona_name=persona_name,
                n_agents=len(agents),
                exc_type=type(exc).__name__,
                error=str(exc),
            )
            return (self._deterministic_fallback(len(agents)), [])

        references = self._resolve_references(content, agents)
        return content.strip(), references

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        *,
        persona_name: str,
        pm_question: str,
        agents: list[CollectiveAgentContext],
        prior_conversation: list[tuple[str, str]],
    ) -> str:
        agents_block = "\n\n".join(
            _AGENT_CONTEXT_TEMPLATE.format(
                label=a.agent_label,
                persona_name=a.persona_name,
                identity_summary=a.identity_seed_summary,
                initial_reaction=_truncate(a.initial_reaction, 1200),
            )
            for a in agents
        )

        if prior_conversation:
            prior_block = "\n".join(
                f"{role.upper()}: {_truncate(content, 800)}"
                for role, content in prior_conversation
            )
        else:
            prior_block = "(no prior turns — this is the first collective question)"

        messages = [
            {
                "role": "system",
                "content": _SYSTEM_PROMPT.format(n=len(agents)),
            },
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(
                    persona_name=persona_name,
                    n=len(agents),
                    agents_block=agents_block,
                    prior_conversation=prior_block,
                    pm_question=pm_question.strip(),
                ),
            },
        ]
        # Slightly higher temperature than synthesis (0.1) — the collective
        # voice benefits from some warmth/specificity, but we don't want
        # it making things up. 0.3 matches the conversational temperature
        # used elsewhere in the chat path.
        return self._chat.chat(messages=messages, temperature=0.3, max_tokens=500)

    @staticmethod
    def _resolve_references(
        content: str,
        agents: list[CollectiveAgentContext],
    ) -> list[AgentReference]:
        """Walk every `[token]` in content and resolve to AgentReferences.

        Only tokens that match a real agent_label in the input are returned.
        Hallucinated labels are silently dropped (the frontend renders them
        as plain text — no broken links).

        Deduplicates: if the LLM cited the same agent twice, they appear
        once in references (the frontend linkifies both occurrences anyway).
        """
        label_to_id = {a.agent_label: a.agent_id for a in agents}
        seen: set[str] = set()
        out: list[AgentReference] = []
        for match in _CITATION_RE.finditer(content):
            label = match.group(1)
            if label in seen:
                continue
            seen.add(label)
            if label in label_to_id:
                out.append(
                    AgentReference(
                        agent_id=label_to_id[label],
                        agent_label=label,
                    )
                )
        return out

    @staticmethod
    def _deterministic_fallback(n: int) -> str:
        """Last-resort reply when the LLM raises. Count-accurate, no
        hallucination risk. Matches the synthesis-service fallback pattern."""
        return (
            f"The collective voice is unavailable right now. There are {n} "
            f"agents in this group — try asking again, or switch to "
            f"individual fan-out for per-agent replies."
        )


def _truncate(text: str, cap: int) -> str:
    """Cap a single chunk of model input so one long reaction doesn't
    blow the context window when N is large."""
    if len(text) <= cap:
        return text
    return text[: cap - 1] + "…"


def build_identity_seed_summary(
    age_band: str | None,
    locale_band: str | None,
    tenure_band: str | None,
    current_state: str | None,
    recent_gripe: str | None,
) -> str:
    """One-line prose summary of an identity_seed for the collective prompt.

    Keeps the agents_block compact. None values are omitted (rather than
    rendered as 'None') so the LLM doesn't see noise.
    """
    parts: list[str] = []
    if age_band:
        parts.append(f"age {age_band}")
    if locale_band:
        parts.append(locale_band)
    if tenure_band:
        parts.append(f"tenure {tenure_band}")
    if current_state:
        parts.append(f"currently: {current_state}")
    if recent_gripe:
        parts.append(f"recent gripe: {recent_gripe}")
    return "; ".join(parts) if parts else "(no identity seed)"
