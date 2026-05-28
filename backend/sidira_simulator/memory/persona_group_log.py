"""Persona-group turn log — append-only JSONL per persona group (#54 T4).

Layout (mirrors AgentMemory's per-agent layout):
    customers/<customer_id>/simulations/<sim_id>/persona_groups/<persona_id>/
        turns.jsonl                                  ← single-arm sim (default)
        treatment/turns.jsonl                        ← A/B treatment arm  (#98)
        control/turns.jsonl                          ← A/B control arm    (#98)

Each line is a PersonaGroupTurn. Two roles appear:
  - `pm`: the PM's question
  - `synthesis`: the one-sentence summary + the full per_agent payload that
    produced it (so the audit trail can be replayed without re-fanning out)

The synthesis is NOT mirrored to any individual agent's conversation log —
the agents' individual logs already contain the PM/agent turn pair for the
same exchange (via AgentChatService.send_message). The synthesis is meta;
the per-agent record is the source of truth for "what each agent said".

Phase 5 #98: in A/B sims the persona-group chat splits into two arm-scoped
rooms. The log path encodes the arm so transcripts are physically isolated --
a thumbs-up on a treatment-room turn can't bleed into the control room, and
re-reading the treatment log doesn't fetch control turns just to throw them
away. `arm=None` keeps the pre-#98 path (single-arm sims, zero regression).
"""

from __future__ import annotations

from typing import Literal

from sidira_simulator.adapters.r2 import ArtifactStore
from sidira_simulator.schemas.persona_group import PersonaGroupTurn

Arm = Literal["treatment", "control"]


class PersonaGroupLog:
    """Append-only log of PM messages + syntheses for one persona group."""

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    @staticmethod
    def _key(
        customer_id: str,
        simulation_id: str,
        persona_id: str,
        arm: Arm | None = None,
    ) -> str:
        base = (
            f"customers/{customer_id}"
            f"/simulations/{simulation_id}"
            f"/persona_groups/{persona_id}"
        )
        if arm is None:
            return f"{base}/turns.jsonl"
        # Phase 5 #98: arm-scoped sub-path keeps the two A/B transcripts
        # physically separate. Arm values are constrained at the API layer
        # to "treatment" | "control"; no path-traversal concern.
        return f"{base}/{arm}/turns.jsonl"

    def append(
        self,
        *,
        customer_id: str,
        simulation_id: str,
        persona_id: str,
        turn: PersonaGroupTurn,
        arm: Arm | None = None,
    ) -> None:
        self._store.append_line(
            self._key(customer_id, simulation_id, persona_id, arm),
            turn.model_dump_json(),
        )

    def read(
        self,
        *,
        customer_id: str,
        simulation_id: str,
        persona_id: str,
        arm: Arm | None = None,
    ) -> list[PersonaGroupTurn]:
        try:
            lines = self._store.read_lines(self._key(customer_id, simulation_id, persona_id, arm))
        except FileNotFoundError:
            return []
        return [PersonaGroupTurn.model_validate_json(ln) for ln in lines if ln.strip()]
