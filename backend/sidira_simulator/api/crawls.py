"""Crawl routes (#171) — saved crawl setup + trigger stubs.

The setup form and its saved config land ahead of the walker
(sidira-crawler #1–#3). The trigger/progress endpoints below sketch the
API shape and 501 until the walker ships — they will wrap
``run_crawl(customer_id, snapshot_version)`` via JobRunner, mirroring the
persona-builds pattern (#24). The pack stays GENERATED, NEVER AUTHORED:
nothing here reads or writes reverse-PRD / reverse-Figma content.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sidira_simulator.api.deps import (
    current_customer_id,
    get_crawl_config_repo,
    get_customer_repo,
)
from sidira_simulator.adapters.repositories import CrawlConfigRepo, CustomerRepo
from sidira_simulator.schemas.crawl import CrawlSetup, CrawlSetupEnvelope

router = APIRouter(tags=["crawls"])


class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


class CrawlSummary(BaseModel):
    id: str
    customer_id: str
    status: CrawlStatus
    snapshot_version: str | None = None
    capabilities_walked: list[str] | None = None
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


@router.get("/crawl-setup", response_model=CrawlSetupEnvelope)
async def get_crawl_setup(
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
) -> CrawlSetupEnvelope:
    row = await repo.get(customer_id)
    if row is None:
        return CrawlSetupEnvelope(customer_id=customer_id)
    return CrawlSetupEnvelope(
        customer_id=customer_id,
        setup=CrawlSetup.model_validate(row["config_json"]),
        updated_at=row["updated_at"],
    )


@router.put("/crawl-setup", response_model=CrawlSetupEnvelope)
async def save_crawl_setup(
    payload: CrawlSetup,
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
    customer_repo: CustomerRepo = Depends(get_customer_repo),
) -> CrawlSetupEnvelope:
    # Same signup-then-act guard as the simulation path: the customer row may
    # not exist yet when the first thing a tenant does is save a crawl setup.
    await customer_repo.ensure_exists(customer_id)
    row = await repo.upsert(customer_id, payload.model_dump())
    return CrawlSetupEnvelope(
        customer_id=customer_id,
        setup=CrawlSetup.model_validate(row["config_json"]),
        updated_at=row["updated_at"],
    )


@router.post("/crawls", response_model=CrawlSummary, status_code=202)
async def create_crawl(customer_id: str = Depends(current_customer_id)) -> CrawlSummary:
    raise HTTPException(
        status_code=501,
        detail=(
            "sidira-crawler #1-#3 — insert crawl run row, submit JobRunner task "
            "wrapping run_crawl(customer_id, snapshot_version), return 202 + crawl_id"
        ),
    )


@router.get("/crawls/{crawl_id}", response_model=CrawlSummary)
async def get_crawl(crawl_id: str, customer_id: str = Depends(current_customer_id)) -> CrawlSummary:
    raise HTTPException(
        status_code=501,
        detail="sidira-crawler #1-#3 — read run row + walked-capability progress from R2 state",
    )
