"""Persona build routes — kick off a build, fetch status, list runs."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sidira_simulator.services.persona_builder import BuildConfig

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


@router.post("", response_model=BuildSummary, status_code=202)
async def create_build(payload: BuildConfig) -> BuildSummary:
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — insert persona_build_runs row, submit JobRunner task, return 202 + build_id",
    )


@router.get("/{build_id}", response_model=BuildSummary)
async def get_build(build_id: str) -> BuildSummary:
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — read row from Postgres + state.json from R2",
    )


@router.get("", response_model=list[BuildSummary])
async def list_builds() -> list[BuildSummary]:
    raise HTTPException(status_code=501, detail="Phase 4.5 — list builds scoped to customer")
