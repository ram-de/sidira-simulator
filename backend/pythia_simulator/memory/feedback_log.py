"""Append-only feedback log per simulation (#56).

Layout:
  customers/<customer_id>/simulations/<sim_id>/feedback.jsonl

Latest entry per (target_kind, target_id, turn_index) wins on read. The
log is append-only because the artifact store is append-friendly and
audit-trail history of feedback changes is valuable for Layer-3
calibration (a PM who flips 👍 → 👎 → 👍 says something different from
one who only ever flagged 👍 once).
"""

from __future__ import annotations

from pythia_simulator.adapters.r2 import ArtifactStore
from pythia_simulator.schemas.feedback import FeedbackEvent, FeedbackTargetKind


class FeedbackLog:
    """Append-only feedback log; latest-wins on read."""

    def __init__(self, store: ArtifactStore) -> None:
        self._store = store

    @staticmethod
    def _key(customer_id: str, simulation_id: str) -> str:
        return f"customers/{customer_id}/simulations/{simulation_id}/feedback.jsonl"

    def append(
        self,
        *,
        customer_id: str,
        simulation_id: str,
        event: FeedbackEvent,
    ) -> None:
        self._store.append_line(
            self._key(customer_id, simulation_id),
            event.model_dump_json(),
        )

    def read_all(
        self,
        *,
        customer_id: str,
        simulation_id: str,
    ) -> list[FeedbackEvent]:
        try:
            lines = self._store.read_lines(self._key(customer_id, simulation_id))
        except FileNotFoundError:
            return []
        return [FeedbackEvent.model_validate_json(ln) for ln in lines if ln.strip()]

    def latest_flags(
        self,
        *,
        customer_id: str,
        simulation_id: str,
        target_kind: FeedbackTargetKind,
        target_id: str,
    ) -> dict[int, bool | None]:
        """Return `{turn_index: realistic_flag}` for the given target.

        Walks the log in order and keeps the LAST event per turn_index.
        Cleared thumbs (`realistic_flag=None`) overwrite prior 👍/👎 — the
        clear is intentional and must replay as "no thumb".
        """
        out: dict[int, bool | None] = {}
        for ev in self.read_all(
            customer_id=customer_id, simulation_id=simulation_id
        ):
            if ev.target_kind != target_kind or ev.target_id != target_id:
                continue
            out[ev.turn_index] = ev.realistic_flag
        return out
