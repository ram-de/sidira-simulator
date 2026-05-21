"""SimulationRunState + JSONL event log.

Adapted from mirofish's simulation_runner.py:101-193 (run state) and :482-554
(JSONL action log). See docs/mirofish-prior-art.md for the lineage.

Two-tier model:
- `SimulationRunState` lives in memory and in R2 as a single overwritable JSON.
  Frontend polls this for live progress.
- `RunEventLog` is an append-only JSONL in R2. The audit trail and the source
  of truth for replay / crash recovery.

Both files live alongside the simulation artifacts:
    customers/<id>/simulations/<sim_id>/
        state.json        ← SimulationRunState (overwritten on each update)
        events.jsonl      ← RunEventLog (append-only)
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from pythia_simulator.adapters.r2 import ArtifactStore


class RunPhase(str, Enum):
    PENDING = "pending"
    LOADING_PACKS = "loading_packs"
    MATERIALIZING_AGENTS = "materializing_agents"
    AGENTS_REACTING = "agents_reacting"
    SCORING = "scoring"
    COMPLETE = "complete"
    FAILED = "failed"


EVENT_TYPES = Literal[
    "run.started",
    "packs.loaded",
    "agent.materialized",
    "agent.reaction.started",
    "agent.reaction.completed",
    "agent.reaction.failed",
    "score.updated",
    "run.complete",
    "run.failed",
]


class RunEvent(BaseModel):
    type: EVENT_TYPES
    at: datetime
    payload: dict[str, str | int | float | None] = Field(default_factory=dict)


class SimulationRunState(BaseModel):
    """Live state of a single simulation. Overwritten on each update."""

    simulation_id: str
    customer_id: str
    phase: RunPhase = RunPhase.PENDING
    started_at: datetime
    updated_at: datetime
    agents_total: int = 0
    agents_complete: int = 0
    agents_failed: int = 0
    partial_score: float | None = None
    recent_events: list[RunEvent] = Field(
        default_factory=list,
        description="Last N events kept inline for cheap frontend polls.",
    )
    error: str | None = None

    def mark_phase(self, phase: RunPhase) -> None:
        self.phase = phase
        self.updated_at = datetime.now(timezone.utc)


class RunStateStore:
    """Owns the read/write contract for state.json + events.jsonl."""

    _RECENT_EVENT_WINDOW = 25

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    @staticmethod
    def _state_key(customer_id: str, sim_id: str) -> str:
        return f"customers/{customer_id}/simulations/{sim_id}/state.json"

    @staticmethod
    def _events_key(customer_id: str, sim_id: str) -> str:
        return f"customers/{customer_id}/simulations/{sim_id}/events.jsonl"

    def write_state(self, state: SimulationRunState) -> None:
        self._store.write_text(
            self._state_key(state.customer_id, state.simulation_id),
            state.model_dump_json(indent=2),
        )

    def read_state(self, customer_id: str, sim_id: str) -> SimulationRunState:
        raw = self._store.read_text(self._state_key(customer_id, sim_id))
        return SimulationRunState.model_validate_json(raw)

    def append_event(self, state: SimulationRunState, event: RunEvent) -> None:
        """Append to events.jsonl and update the recent_events window on state."""
        self._store.append_line(
            self._events_key(state.customer_id, state.simulation_id),
            event.model_dump_json(),
        )
        state.recent_events.append(event)
        if len(state.recent_events) > self._RECENT_EVENT_WINDOW:
            state.recent_events = state.recent_events[-self._RECENT_EVENT_WINDOW :]
        state.updated_at = event.at
        self.write_state(state)

    def emit(
        self,
        state: SimulationRunState,
        event_type: EVENT_TYPES,
        **payload: str | int | float | None,
    ) -> RunEvent:
        event = RunEvent(
            type=event_type,
            at=datetime.now(timezone.utc),
            payload=payload,
        )
        self.append_event(state, event)
        return event
