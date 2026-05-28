"""Persona-group chat synthesis (#54).

One-sentence summary line shown at the top of `/simulations/[id]/personas/[id]`,
above the fan-out per-agent replies. The synthesis exists to give the PM a
counted, cause-named first-glance summary — NOT to replace the per-agent
replies.

Design contract: see `docs/54-synthesis-quality-bar.md`. Three locked decisions:
  (A) prompt strategy — counted, names the cause, no hedges
  (B) eval rubric — fixture-based trait assertions in
      `tests/test_persona_group_synthesis.py`
  (C) contradictory replies — three named modes (consensus / split / outlier)
      plus an explicit non-substantive diagnostic; synthesis never refuses
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

from pythia_simulator.adapters.llm import ChatClient, get_chat_client

log = structlog.get_logger()


@dataclass(frozen=True)
class AgentReply:
    """One agent's reply in a persona-group fan-out."""

    agent_label: str
    content: str


_SYSTEM_PROMPT = """You are summarizing N agent replies to one PM question. Your output is ONE sentence (two only if a single agent flagged something genuinely distinct) shown to the PM at the top of the page; the full agent replies appear below.

Your synthesis MUST:
- Lead with "N of M" — exact count of agents sharing the core position. Always use both numbers (e.g. "3 of 5", not "3 agents" by itself when summarizing a majority).
- Name the SPECIFIC cause or scenario the agents pointed to — the noun, the flow, the moment — not a sentiment label.
- If the group genuinely splits with no majority, write exactly in this shape: "N agents split: [label_a] said X, [label_b] said Y, [label_c] said Z." List every position.
- If one agent flagged something distinct that the others didn't, append " — [label] also flagged [thing]" or " — [label] disagreed — [their reason]" as the second clause.

Do NOT:
- Hedge: "mixed", "varied", "overall", "somewhat", "generally".
- Editorialize: "this suggests", "indicates", "notably", "interestingly", "it appears".
- Use vague counters: "most", "some", "a few", "the majority".
- Restate the PM question.
- Invent consensus when replies are non-substantive. If every reply is evasive, off-topic, or a refusal, output EXACTLY this and nothing else: "N agents gave non-substantive replies - re-ask with more specificity." (Substitute the real N.)

Output only the synthesis sentence(s). No preface, no quotes around the sentence, no "Synthesis:" prefix."""


_USER_TEMPLATE = """PM question:
{pm_question}

Agent replies (N={n}):
{replies_block}"""


_COUNT_OF_RE = re.compile(r"\b(\d+)\s+of\s+(\d+)\b", re.IGNORECASE)
_AGENTS_SPLIT_RE = re.compile(r"\b(\d+)\s+agents?\s+split\b", re.IGNORECASE)
_NON_SUB_RE = re.compile(
    r"\b(\d+)\s+agents?\s+gave\s+non-substantive\s+replies\b",
    re.IGNORECASE,
)


class CountMismatchError(RuntimeError):
    """The synthesis output claimed a count that disagrees with len(replies)."""


class PersonaGroupSynthesisService:
    """Synthesizes one-sentence summaries for persona-group chat fan-outs."""

    def __init__(
        self,
        chat_client: ChatClient | None = None,
        model_id: str | None = None,
    ) -> None:
        if chat_client is not None:
            self._chat = chat_client
        elif model_id is not None:
            self._chat = get_chat_client(model_id)
        else:
            self._chat = get_chat_client()

    def synthesize(self, pm_question: str, replies: list[AgentReply]) -> str:
        """Generate the synthesis line for `replies` to `pm_question`.

        Behaviour contract — this method NEVER raises:
          - Empty/zero replies → safe default ("No agent replies…").
          - LLM raises on first call → log `synthesis.llm_call_failed` and
            return deterministic fallback. Critical: codex #80 [P1] —
            an unhandled exception here would 500 the route AFTER the
            per-agent fan-out has already persisted PM/agent turns to
            individual logs, and a client retry would fan out the same PM
            message a second time, duplicating every successful agent's
            conversation. The synthesis is downstream of the data we care
            about; degrading it gracefully is always the right call.
          - First call returns wrong count → retry once with explicit
            corrective hint.
          - Retry raises → same swallow-and-fallback behavior.
          - Retry returns wrong count → log `synthesis.count_mismatch` and
            return deterministic fallback.
        """
        if not replies:
            # Defensive: a fan-out with zero replies shouldn't happen, but if
            # it does we don't want to ship "0 of 0 said …" to the PM.
            return "No agent replies were collected — re-run the fan-out."

        first = self._call_llm_safely(pm_question, replies, retry_hint=None, attempt="first")
        if first is not None and self._count_matches(first, len(replies)):
            return first.strip()

        # One retry with an explicit corrective hint. The original prompt
        # already requires N-of-M accuracy; the retry message names the actual
        # number to make the constraint impossible to miss.
        retry_hint = (
            (
                f"Your previous synthesis was: {first!r}. The count it claimed "
                f"does not match the actual number of replies ({len(replies)}). "
                f"Try again. There were EXACTLY {len(replies)} replies. "
                f"Your synthesis must lead with a count that uses {len(replies)} "
                f"as the denominator (e.g. 'N of {len(replies)}') or be the "
                f"split / non-substantive form using exactly {len(replies)}."
            )
            if first is not None
            else (
                f"There were EXACTLY {len(replies)} replies. Lead with a count "
                f"that uses {len(replies)} as the denominator."
            )
        )
        retry = self._call_llm_safely(pm_question, replies, retry_hint=retry_hint, attempt="retry")
        if retry is not None and self._count_matches(retry, len(replies)):
            return retry.strip()

        log.warning(
            "synthesis.count_mismatch",
            n_replies=len(replies),
            first_output=(first[:200] if first is not None else None),
            retry_output=(retry[:200] if retry is not None else None),
        )
        return self._deterministic_fallback(len(replies))

    # ------------------------------------------------------------------
    # internals
    # ------------------------------------------------------------------

    def _call_llm_safely(
        self,
        pm_question: str,
        replies: list[AgentReply],
        retry_hint: str | None,
        attempt: str,
    ) -> str | None:
        """Wrap _call_llm in exception handling — never raise out of the
        service. Codex #80 [P1]: an exception escaping into the route would
        500 AFTER per-agent fan-out has persisted PM/agent turns, and a
        client retry would duplicate those individual conversations. The
        synthesis can degrade to deterministic fallback safely; the per-agent
        replies are the source of truth and they're already persisted.

        Returns the LLM text on success, None on any exception (so the
        caller can branch between count-mismatch and llm-failure paths).
        """
        try:
            return self._call_llm(pm_question, replies, retry_hint)
        except Exception as exc:  # noqa: BLE001 — degrade to deterministic fallback
            log.warning(
                "synthesis.llm_call_failed",
                attempt=attempt,
                n_replies=len(replies),
                exc_type=type(exc).__name__,
                error=str(exc),
            )
            return None

    def _call_llm(
        self,
        pm_question: str,
        replies: list[AgentReply],
        retry_hint: str | None,
    ) -> str:
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": _USER_TEMPLATE.format(
                    pm_question=pm_question.strip(),
                    n=len(replies),
                    replies_block=_format_replies(replies),
                ),
            },
        ]
        if retry_hint is not None:
            messages.append({"role": "system", "content": retry_hint})
        # Low temperature: synthesis is a summarization task. Determinism
        # helps the rubric tests stay stable across runs.
        return self._chat.chat(messages=messages, temperature=0.1, max_tokens=200)

    @staticmethod
    def _count_matches(output: str, n: int) -> bool:
        """True if the output's claimed count is consistent with `n` replies.

        Three accepted shapes:
          - "X of N" (consensus) — denominator must equal n, numerator must
            be in [1, n].
          - "N agents split" — must use n exactly.
          - "N agents gave non-substantive replies" — must use n exactly.

        Outputs lacking any of these counted shapes do NOT match — that's the
        signal to retry with a corrective hint.
        """
        if m := _COUNT_OF_RE.search(output):
            num = int(m.group(1))
            den = int(m.group(2))
            return den == n and 1 <= num <= n
        if m := _AGENTS_SPLIT_RE.search(output):
            return int(m.group(1)) == n
        if m := _NON_SUB_RE.search(output):
            return int(m.group(1)) == n
        return False

    @staticmethod
    def _deterministic_fallback(n: int) -> str:
        """Last-resort synthesis when the LLM can't be coaxed into a correct
        count. Better to ship a boring-but-correct line than a fluent-but-wrong
        one — the PM is reading this above the actual replies."""
        return f"{n} agents replied — see individual answers below."


def _format_replies(replies: list[AgentReply]) -> str:
    return "\n".join(f"[{r.agent_label}]: {r.content.strip()}" for r in replies)
