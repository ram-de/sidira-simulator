"""Ingestion store (#19) — the ADD-only write path for imported experiments.

The existing archive read interface (``experiment_archive.seed_experiments`` +
the similarity / chat / dedup pipeline) is being extended by another builder in
parallel, so we do NOT touch it. Instead, imported records accumulate here, in a
per-customer in-memory store. This keeps the PR migration-free; a future PR can
swap this for a Postgres-backed repo (mirroring the ``feature_stores`` pattern:
``credentials.encrypt`` + an Alembic migration) once a real customer arrives,
without changing the connector/import API surface.

Records are stored as copies and returned as copies, so a caller mutating a
returned Experiment can never corrupt the store (same discipline as
``seed_experiments``).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from uuid import uuid4

from sidira_simulator.schemas.connector import ConnectorKind, ImportSummary
from sidira_simulator.schemas.experiment_memory import Experiment


class IngestionStore:
    """Per-customer accumulation of imported experiments + an import log."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # customer_id -> list of imported experiments
        self._archive: dict[str, list[Experiment]] = {}
        # customer_id -> list of import summaries
        self._imports: dict[str, list[ImportSummary]] = {}

    def record_import(
        self, customer_id: str, kind: ConnectorKind, experiments: list[Experiment]
    ) -> ImportSummary:
        """Append imported experiments and log the import. Returns its summary."""
        summary = ImportSummary(
            id=f"imp-{uuid4().hex[:12]}",
            kind=kind,
            imported=len(experiments),
            at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._archive.setdefault(customer_id, []).extend(
                e.model_copy(deep=True) for e in experiments
            )
            self._imports.setdefault(customer_id, []).append(summary)
        return summary

    def archive_for(self, customer_id: str) -> list[Experiment]:
        """Return a fresh copy of the customer's ingested experiments."""
        with self._lock:
            return [e.model_copy(deep=True) for e in self._archive.get(customer_id, [])]

    def imports_for(self, customer_id: str) -> list[ImportSummary]:
        """Return the customer's import log (newest last)."""
        with self._lock:
            return list(self._imports.get(customer_id, []))

    def clear(self) -> None:
        """Reset all state — for the test suite only."""
        with self._lock:
            self._archive.clear()
            self._imports.clear()


_STORE = IngestionStore()


def get_ingestion_store() -> IngestionStore:
    """Process-wide singleton (mirrors the in-memory repo accessors in deps.py)."""
    return _STORE
