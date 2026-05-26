"""Persona-group turn log — append-only JSONL per persona group (#54 T4).

Layout (mirrors AgentMemory's per-agent layout):
    customers/<customer_id>/simulations/<sim_id>/persona_groups/<persona_id>/
        turns.jsonl

Each line is a PersonaGroupTurn. Two roles appear:
  - `pm`: the PM's question
  - `synthesis`: the one-sentence summary + the full per_agent payload that
    produced it (so the audit trail can be replayed without re-fanning out)

The synthesis is NOT mirrored to any individual agent's conversation log —
the agents' individual logs already contain the PM/agent turn pair for the
same exchange (via AgentChatService.send_message). The synthesis is meta;
the per-agent record is the source of truth for "what each agent said".
"""

from __future__ import annotations

from pythia_simulator.adapters.r2 import ArtifactStore
from pythia_simulator.schemas.persona_group import PersonaGroupTurn


class PersonaGroupLog:
    """Append-only log of PM messages + syntheses for one persona group."""

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    @staticmethod
    def _key(customer_id: str, simulation_id: str, persona_id: str) -> str:
        return (
            f"customers/{customer_id}"
            f"/simulations/{simulation_id}"
            f"/persona_groups/{persona_id}"
            f"/turns.jsonl"
        )

    def append(
        self,
        *,
        customer_id: str,
        simulation_id: str,
        persona_id: str,
        turn: PersonaGroupTurn,
    ) -> None:
        self._store.append_line(
            self._key(customer_id, simulation_id, persona_id),
            turn.model_dump_json(),
        )

    def read(
        self,
        *,
        customer_id: str,
        simulation_id: str,
        persona_id: str,
    ) -> list[PersonaGroupTurn]:
        try:
            lines = self._store.read_lines(
                self._key(customer_id, simulation_id, persona_id)
            )
        except FileNotFoundError:
            return []
        return [PersonaGroupTurn.model_validate_json(ln) for ln in lines if ln.strip()]
