"""Persona Builder — orchestrates Snowflake → pythia-personas library → R2.

This is the simulator-side wrapper that the UI talks to. It hides the
producer-library boundary: from the UI's point of view, you submit a build
config and get back a draft pack; under the hood, this service loads creds,
runs the Snowflake query, invokes the pythia-personas pipeline, and writes
the result to R2 + Postgres.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.services.column_mapper import FeatureGroup
from sidira_simulator.services.run_state import RunPhase, RunStateStore, SimulationRunState


class BuildConfig(BaseModel):
    """User-supplied config from the wizard."""

    connection_id: str
    source_query: str = Field(description="SELECT statement returning one row per user.")
    column_mapping: dict[str, FeatureGroup | None]
    k: int | Literal["auto"] = "auto"
    stability_threshold: float = 0.65
    llm_provider: Literal["groq", "anthropic"] = "groq"
    weight_schemes: list[Literal["head_count", "order_weighted", "revenue_weighted"]] = Field(
        default_factory=lambda: ["head_count"]
    )


@dataclass
class BuildResult:
    """Outcome of a build run."""

    build_id: str
    pack_version: str
    stability_score: float
    persona_count: int
    artifact_uri: str


class PersonaBuilderService:
    def __init__(self, store: ArtifactStore | None = None) -> None:
        self._store = store or get_store()
        self._run_state = RunStateStore(self._store)

    async def run(
        self,
        customer_id: str,
        config: BuildConfig,
    ) -> BuildResult:
        """Execute a build end-to-end. Persists status via RunStateStore."""
        build_id = str(uuid.uuid4())
        pack_version = self._next_version(customer_id)

        state = SimulationRunState(
            simulation_id=build_id,  # JobRun generalization (Phase 4.5) — same shape
            customer_id=customer_id,
            phase=RunPhase.LOADING_PACKS,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._run_state.write_state(state)
        self._run_state.emit(state, "run.started", pack_version=pack_version)

        raise NotImplementedError(
            "Phase 4.5 implementation:\n"
            "1. Load encrypted creds for config.connection_id from Postgres\n"
            "2. credentials.decrypt() → SnowflakeCreds (in-memory only)\n"
            "3. SnowflakeStore.run_query(config.source_query) → list of user-row dicts\n"
            "4. Apply column_mapping → per-group feature matrices\n"
            "5. Call pythia_personas library: encoder → cluster → calibrate → compile_prompts\n"
            "6. Validate stability_score >= config.stability_threshold (else mark DRAFT_FAILED)\n"
            "7. Write to R2 at customers/<id>/personas/v_<N>/{persona_pack.json, manifest.json, prompts/*.md}\n"
            "8. Insert persona_pack_versions row (status=DRAFT) in Postgres\n"
            "9. Emit run.complete with stability + persona_count"
        )

    def _next_version(self, customer_id: str) -> str:
        """Next sequential version tag. Phase 4.5 reads max(version) from Postgres."""
        return "v_pending"
