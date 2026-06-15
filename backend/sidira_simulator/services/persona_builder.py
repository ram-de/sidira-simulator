"""Persona Builder — orchestrates Snowflake → sidira-personas library → R2.

This is the simulator-side wrapper that the UI talks to. It hides the
producer-library boundary: from the UI's point of view, you submit a build
config and get back a draft pack; under the hood, this service loads creds,
runs the Snowflake query, invokes the sidira-personas pipeline, and writes
the result to R2 + Postgres.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field

from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.feature_stores.snowflake import SnowflakeCreds, SnowflakeStore
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.adapters.repositories import PersonaBuildRepo
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


@dataclass
class PipelineOutput:
    """Canned output of the sidira-personas pipeline (the injectable seam).

    Keeps the orchestration testable: the real pipeline (encoder → cluster →
    calibrate → compile_prompts) lives in the ``sidira-personas`` library, which
    is NOT installed in this backend's env. Tests monkeypatch
    :func:`run_personas_pipeline` to return a canned instance of this.
    """

    persona_pack: dict[str, Any]
    stability_score: float
    persona_count: int
    prompts: dict[str, str] = field(default_factory=dict)


def run_personas_pipeline(
    feature_rows: list[dict[str, list[Any]]],
    column_mapping: dict[str, FeatureGroup | None],
    config: BuildConfig,
) -> PipelineOutput:
    """The single injectable seam over the ``sidira-personas`` producer library.

    ``feature_rows`` is the per-group feature view (group id → list of column
    values) the orchestrator assembled from the raw query rows + column mapping.

    The real pipeline (encoder → cluster → calibrate → compile_prompts) ships in
    the ``sidira-personas`` package, which is NOT installed in this backend's
    runtime. We import it lazily so the module loads (and tests run) without it;
    a missing install raises a clear RuntimeError. Tests monkeypatch THIS
    function to return canned :class:`PipelineOutput`, so the whole build
    orchestration is exercised without real clustering.
    """
    try:
        import sidira_personas  # type: ignore[import-not-found]  # noqa: F401
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sidira-personas not installed — the persona build pipeline is unavailable "
            "in this environment."
        ) from exc

    # When the library IS present, this is where its pipeline gets driven. Left
    # unimplemented intentionally: the producer-library integration lands with
    # the package install; until then this path is unreachable in this backend.
    raise RuntimeError(
        "sidira-personas is installed but the pipeline binding is not implemented here."
    )


class PersonaBuilderService:
    def __init__(
        self,
        store: ArtifactStore | None = None,
        build_repo: PersonaBuildRepo | None = None,
        connection_repo: Any | None = None,
    ) -> None:
        self._store = store or get_store()
        self._run_state = RunStateStore(self._store)
        self._build_repo = build_repo
        self._connection_repo = connection_repo

    async def run(
        self,
        build_id: str,
        customer_id: str,
        config: BuildConfig,
    ) -> BuildResult:
        """Execute a build end-to-end. Persists status via the build repo +
        progress via RunStateStore. The row is created (PENDING) by the route
        before this task is scheduled; this drives it RUNNING → COMPLETE/FAILED.
        """
        state = SimulationRunState(
            simulation_id=build_id,  # JobRun generalization (Phase 4.5) — same shape
            customer_id=customer_id,
            phase=RunPhase.PENDING,
            started_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        self._run_state.write_state(state)

        try:
            await self._build_repo.update_status(build_id, customer_id, "running")
            state.mark_phase(RunPhase.LOADING_PACKS)
            self._run_state.write_state(state)
            self._run_state.emit(state, "run.started")

            # 1–2. Load the connection row (customer-scoped) + decrypt creds.
            row = await self._connection_repo.get(config.connection_id, customer_id)
            if row is None:
                raise ValueError(
                    f"Feature-store connection {config.connection_id!r} not found "
                    f"for customer {customer_id!r}"
                )
            store = self._snowflake_store(row, customer_id)

            # 3. Run the source query → user rows.
            rows = store.run_query(config.source_query)
            self._run_state.emit(state, "packs.loaded", row_count=len(rows))

            # 4. Apply column_mapping → per-group feature view.
            feature_rows = self._apply_column_mapping(rows, config.column_mapping)

            # 5. Invoke the sidira-personas pipeline (injectable seam).
            state.mark_phase(RunPhase.MATERIALIZING_AGENTS)
            self._run_state.write_state(state)
            output = run_personas_pipeline(feature_rows, config.column_mapping, config)

            # 6. Stability gate. Below threshold → FAILED (no promoted pack).
            state.mark_phase(RunPhase.SCORING)
            self._run_state.write_state(state)
            self._run_state.emit(
                state,
                "score.updated",
                stability_score=output.stability_score,
                persona_count=output.persona_count,
            )
            if output.stability_score < config.stability_threshold:
                msg = (
                    f"stability {output.stability_score:.3f} below threshold "
                    f"{config.stability_threshold:.3f}"
                )
                await self._fail(build_id, customer_id, state, msg)
                raise BuildStabilityError(msg)

            # 7. Write the pack to R2 (v_N auto-bumped, never overwriting).
            pack_version = self._next_version(customer_id)
            artifact_uri = self._write_pack(customer_id, pack_version, output)

            # 8. Update the build row to COMPLETE.
            completed_at = datetime.now(timezone.utc)
            await self._build_repo.update_status(
                build_id,
                customer_id,
                "complete",
                pack_version=pack_version,
                stability_score=output.stability_score,
                persona_count=output.persona_count,
                completed_at=completed_at,
            )

            # 9. Emit run.complete.
            state.mark_phase(RunPhase.COMPLETE)
            self._run_state.write_state(state)
            self._run_state.emit(
                state,
                "run.complete",
                pack_version=pack_version,
                stability_score=output.stability_score,
                persona_count=output.persona_count,
            )

            return BuildResult(
                build_id=build_id,
                pack_version=pack_version,
                stability_score=output.stability_score,
                persona_count=output.persona_count,
                artifact_uri=artifact_uri,
            )
        except BuildStabilityError:
            # Already recorded as FAILED in the gate; don't double-report.
            raise
        except Exception as exc:  # noqa: BLE001 — record any failure on the row
            await self._fail(build_id, customer_id, state, str(exc))
            raise

    async def _fail(
        self,
        build_id: str,
        customer_id: str,
        state: SimulationRunState,
        error: str,
    ) -> None:
        try:
            await self._build_repo.update_status(
                build_id,
                customer_id,
                "failed",
                error=error,
                completed_at=datetime.now(timezone.utc),
            )
        finally:
            state.mark_phase(RunPhase.FAILED)
            state.error = error
            self._run_state.write_state(state)
            self._run_state.emit(state, "run.failed", error=error)

    def _snowflake_store(self, row: dict[str, Any], customer_id: str) -> SnowflakeStore:
        """Decrypt the password blob and build a SnowflakeStore. The cleartext
        password never leaves this method's scope."""
        secrets = credentials.decrypt(
            credentials.deserialize_blob(row["password_enc"]), customer_id=customer_id
        )
        creds = SnowflakeCreds(
            account=row["account"],
            user=row["user"],
            password=secrets["password"],
            warehouse=row["warehouse"],
            role=row["role"],
            database=row["database"],
            schema=row["schema"],
        )
        return SnowflakeStore(creds)

    @staticmethod
    def _apply_column_mapping(
        rows: list[dict[str, Any]],
        column_mapping: dict[str, FeatureGroup | None],
    ) -> list[dict[str, list[Any]]]:
        """Project raw query rows onto the canonical feature groups.

        Produces one entry per row: ``{group_id: [values of columns mapped to
        that group]}``. Columns mapped to ``None`` (unmapped) are dropped.
        """
        view: list[dict[str, list[Any]]] = []
        for row in rows:
            grouped: dict[str, list[Any]] = {}
            for column, group in column_mapping.items():
                if group is None:
                    continue
                grouped.setdefault(group, []).append(row.get(column))
            view.append(grouped)
        return view

    def _write_pack(
        self,
        customer_id: str,
        pack_version: str,
        output: PipelineOutput,
    ) -> str:
        """Write the pack + manifest (+ prompts) under the versioned prefix."""
        base = f"customers/{customer_id}/personas/{pack_version}"
        pack_key = f"{base}/persona_pack.json"
        self._store.write_text(pack_key, json.dumps(output.persona_pack, indent=2))
        manifest = {
            "version": pack_version,
            "customer_id": customer_id,
            "persona_count": output.persona_count,
            "stability_score": output.stability_score,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store.write_text(f"{base}/manifest.json", json.dumps(manifest, indent=2))
        for name, prompt in output.prompts.items():
            self._store.write_text(f"{base}/prompts/{name}.md", prompt)
        return pack_key

    def _next_version(self, customer_id: str) -> str:
        """Next sequential version tag (``v_1``, ``v_2``, …).

        The :class:`ArtifactStore` Protocol has no list/glob primitive (R2 keys
        are read by exact key, persona packs are otherwise found via a ``latest``
        pointer). To stay portable across the Local + R2 + Fallback stores we
        probe sequentially: a version exists iff its ``persona_pack.json`` reads
        without raising ``FileNotFoundError``. We return ``v_<max+1>`` (the first
        gap), starting at ``v_1``.
        """
        n = 1
        while True:
            key = f"customers/{customer_id}/personas/v_{n}/persona_pack.json"
            try:
                self._store.read_text(key)
            except FileNotFoundError:
                return f"v_{n}"
            n += 1


class BuildStabilityError(RuntimeError):
    """The build's stability score fell below the configured threshold.

    Distinguishes the stability-gate failure (already recorded as FAILED) from
    any other exception so ``run`` doesn't double-report the failure.
    """
