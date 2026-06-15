"""Persona build routes — kick off a build, fetch status, list runs, stream events.

A build runs as a FastAPI BackgroundTask (the same pattern as a simulation run):
POST inserts a PENDING ``persona_build_runs`` row and schedules the task, which
loads the saved feature-store connection, runs the source query, invokes the
sidira-personas pipeline, and writes the resulting pack to R2 at
``customers/<id>/personas/v_<N>/persona_pack.json``. Live progress + the JSONL
event log live alongside the artifacts in R2 (RunStateStore).
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import AsyncIterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from sidira_simulator.adapters.postgres import database_configured, get_sessionmaker
from sidira_simulator.adapters.r2 import ArtifactStore
from sidira_simulator.adapters.repositories import (
    PersonaBuildRepo,
    PostgresFeatureStoreConnectionRepo,
    PostgresPersonaBuildRepo,
    get_in_memory_feature_store_connection_repo,
    get_in_memory_persona_build_repo,
)
from sidira_simulator.api.deps import (
    current_customer_id,
    get_artifact_store,
    get_persona_build_repo,
)
from sidira_simulator.services.persona_builder import BuildConfig, PersonaBuilderService
from sidira_simulator.services.run_state import RunStateStore

router = APIRouter(prefix="/persona-builds", tags=["persona-builds"])


class BuildStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class BuildSummary(BaseModel):
    id: str
    customer_id: str
    connection_id: str
    status: BuildStatus
    pack_version: str | None = None
    stability_score: float | None = None
    persona_count: int | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


def _to_summary(row: dict) -> BuildSummary:
    return BuildSummary(
        id=row["id"],
        customer_id=row["customer_id"],
        connection_id=row["connection_id"],
        status=BuildStatus(row["status"]) if row.get("status") else BuildStatus.PENDING,
        pack_version=row.get("pack_version"),
        stability_score=row.get("stability_score"),
        persona_count=row.get("persona_count"),
        created_at=row.get("created_at") or datetime.utcnow(),
        completed_at=row.get("completed_at"),
        error=row.get("error"),
    )


async def _run_build(
    build_id: str,
    customer_id: str,
    config: BuildConfig,
    store: ArtifactStore,
) -> None:
    """BackgroundTask body. Resolves its OWN repos so it doesn't hold the
    request-scoped session past response (the simulation runner does the same):
    a fresh Postgres session when configured, the process-wide in-memory repos
    otherwise."""
    if database_configured():
        async with get_sessionmaker()() as session:
            service = PersonaBuilderService(
                store=store,
                build_repo=PostgresPersonaBuildRepo(session),
                connection_repo=PostgresFeatureStoreConnectionRepo(session),
            )
            try:
                await service.run(build_id, customer_id, config)
            except Exception:
                # The row + run-state already record the failure; swallow so the
                # BackgroundTask doesn't surface an unhandled-exception traceback.
                pass
    else:
        service = PersonaBuilderService(
            store=store,
            build_repo=get_in_memory_persona_build_repo(),
            connection_repo=get_in_memory_feature_store_connection_repo(),
        )
        try:
            await service.run(build_id, customer_id, config)
        except Exception:
            pass


@router.post("", response_model=BuildSummary, status_code=status.HTTP_202_ACCEPTED)
async def create_build(
    payload: BuildConfig,
    background_tasks: BackgroundTasks,
    customer_id: str = Depends(current_customer_id),
    build_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
    store: ArtifactStore = Depends(get_artifact_store),
) -> BuildSummary:
    """Accept a build config. Returns 202 + build_id; the build runs after the
    response is sent. customer_id comes from the auth scope, never the body."""
    build_id = str(uuid.uuid4())
    row = await build_repo.create(
        build_id=build_id, customer_id=customer_id, connection_id=payload.connection_id
    )
    background_tasks.add_task(_run_build, build_id, customer_id, payload, store)
    return _to_summary(row)


@router.get("", response_model=list[BuildSummary])
async def list_builds(
    customer_id: str = Depends(current_customer_id),
    build_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
    limit: int = 50,
) -> list[BuildSummary]:
    """Recent builds for the current customer, newest first."""
    rows = await build_repo.list_recent(customer_id, limit=limit)
    return [_to_summary(r) for r in rows]


@router.get("/{build_id}", response_model=BuildSummary)
async def get_build(
    build_id: str,
    customer_id: str = Depends(current_customer_id),
    build_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
) -> BuildSummary:
    row = await build_repo.get(build_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Persona build {build_id} not found")
    return _to_summary(row)


@router.get("/{build_id}/events")
async def get_build_events(
    build_id: str,
    customer_id: str = Depends(current_customer_id),
    build_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
    store: ArtifactStore = Depends(get_artifact_store),
) -> StreamingResponse:
    """Stream the build's JSONL event log (one event object per line), mirroring
    the simulation events stream. 404 if there's no such build."""
    row = await build_repo.get(build_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Persona build {build_id} not found")

    rs = RunStateStore(store)
    events_key = rs._events_key(customer_id, build_id)
    try:
        lines = store.read_lines(events_key)
    except FileNotFoundError:
        lines = []

    async def _stream() -> AsyncIterator[bytes]:
        for line in lines:
            if line.strip():
                yield (line.rstrip("\n") + "\n").encode("utf-8")

    return StreamingResponse(_stream(), media_type="application/x-ndjson")
