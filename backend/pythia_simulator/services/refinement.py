"""Refinement service — proposes 1-3 hypothesis refinements based on weaknesses.

Single LLM call returning JSON. Independent of ScoringService — takes a typed
`RefinementInput` so it's unit-testable without driving the full simulation.

Karpathy AutoResearch pattern from the Pythia roadmap: one specialized agent,
one job (rewrite the hypothesis based on diagnosed weakness), one output.
"""

from __future__ import annotations

import logging

from pythia_simulator.adapters.llm import ChatClient, JSONRepairError, get_chat_client
from pythia_simulator.schemas.scoring import RefinementInput, RefinementOutput

log = logging.getLogger(__name__)


_REFINEMENT_SYSTEM = """You are an experimentation expert proposing concrete refinements to a product
hypothesis that scored poorly in a behavioral simulation.

You will receive:
- The original hypothesis prose
- Its current confidence score (0-100)
- The top diagnosed weaknesses (with categories and frequencies)
- 3-5 representative user reactions

Your job: propose 1-3 SPECIFIC, ACTIONABLE refinements that would address the diagnosed weaknesses.

Each refinement must be:
- Concrete enough that a PM could re-submit it as a refined hypothesis tomorrow
- Targeted at one specific weakness (not generic "make it better")
- Plausibly testable (narrower cohort, sharper metric, different mechanism)

Do NOT propose more than 3 refinements. Do NOT include hedging or filler.

Return STRICT JSON: {"suggestions": ["<refinement 1>", "<refinement 2>", ...]}."""


class RefinementService:
    def __init__(self, chat_client: ChatClient | None = None) -> None:
        self._chat_explicit = chat_client

    @property
    def _chat(self) -> ChatClient:
        if self._chat_explicit is None:
            self._chat_explicit = get_chat_client()
        return self._chat_explicit

    async def suggest(self, payload: RefinementInput) -> list[str]:
        """Return 1-3 refinement suggestions. Empty list on LLM failure."""
        user_prompt = self._render(payload)
        try:
            output: RefinementOutput = await _to_thread(
                self._chat.chat_json,
                [
                    {"role": "system", "content": _REFINEMENT_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
                RefinementOutput,
            )
        except (JSONRepairError, Exception) as exc:  # noqa: BLE001 — degrade gracefully
            log.warning("refinement failed: %s", exc)
            return []
        # Cap at 3 even if the LLM returned more.
        return output.suggestions[:3]

    @staticmethod
    def _render(payload: RefinementInput) -> str:
        lines = [
            f"Capability: {payload.capability_name}",
            f"Current confidence: {payload.confidence_score:.1f}/100",
            "",
            "Original hypothesis:",
            payload.hypothesis_prose,
            "",
            "Top weaknesses diagnosed:",
        ]
        if payload.top_weaknesses:
            for w in payload.top_weaknesses:
                lines.append(f"- {w.category}: {w.summary}")
        else:
            lines.append("- (none diagnosed; reactions were mixed but not categorizable)")

        if payload.sample_reactions:
            lines.append("")
            lines.append("Sample user reactions:")
            for i, reaction in enumerate(payload.sample_reactions[:5], 1):
                trimmed = reaction.strip().replace("\n", " ")[:400]
                lines.append(f'{i}. "{trimmed}"')
        return "\n".join(lines)


async def _to_thread(func, *args, **kwargs):
    """Async wrapper since chat_json is sync."""
    import asyncio

    return await asyncio.to_thread(func, *args, **kwargs)
