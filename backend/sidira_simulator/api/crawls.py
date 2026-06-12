"""Crawl routes (#171, #193) — saved crawl setup + fire-and-watch trigger.

``POST /crawls`` dispatches the ``crawl.yml`` workflow in
ram-de/sidira-crawler via the GitHub API and returns immediately — the
crawl (~40 min) runs in that repo's CI, where the R2 and Groq secrets
live; they never touch this backend. The browser is never load-bearing:
on completion the workflow itself flips ``featurepacks/latest`` in R2,
which is the publish event the capabilities view picks up. ``GET
/crawls/{id}`` maps the CI run onto ``CrawlSummary`` for the optional
watch view. The pack stays GENERATED, NEVER AUTHORED: nothing here reads
or writes reverse-PRD / reverse-Figma content.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sidira_simulator.api.deps import (
    current_customer_id,
    get_crawl_config_repo,
    get_crawl_dispatcher,
    get_crawl_run_repo,
    get_customer_repo,
    get_feature_pack_loader,
)
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.github_actions import (
    CrawlDispatchError,
    GitHubCrawlDispatcher,
    WorkflowRunState,
)
from sidira_simulator.adapters.repositories import (
    CrawlConfigRepo,
    CrawlRunRepo,
    CustomerRepo,
)
from sidira_simulator.schemas.crawl import CrawlSetup, CrawlSetupEnvelope

log = structlog.get_logger(__name__)

router = APIRouter(tags=["crawls"])


class CrawlStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"


_TERMINAL = (CrawlStatus.COMPLETE.value, CrawlStatus.FAILED.value)

# Mirrors crawl.yml's "Validate inputs" regex — customer becomes an R2 key
# segment and the workflow's run-name in the secret-bearing crawler repo, so
# reject anything else here with a clear 400 instead of a cryptic CI failure.
# Wider than a DNS-ish slug because the production tenant key IS the Clerk
# org id (org_..., underscore + mixed case — see api/auth.py passthrough);
# still a single safe key segment: no separators, no dots, no leading dash.
_CUSTOMER_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")

# A dispatched run materializes on GitHub within seconds. If it still cannot
# be found after this long, the run either never got created or fell out of
# the lookup window — without a cutoff the row would report pending forever.
_MATERIALIZE_TIMEOUT = timedelta(minutes=15)


class CrawlSummary(BaseModel):
    id: str
    customer_id: str
    status: CrawlStatus
    # walking | synthesizing while running — derived from the CI run's jobs.
    phase: str | None = None
    snapshot_version: str | None = None
    capabilities_walked: list[str] | None = None
    run_url: str | None = None
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
async def create_crawl(
    customer_id: str = Depends(current_customer_id),
    runs: CrawlRunRepo = Depends(get_crawl_run_repo),
    customer_repo: CustomerRepo = Depends(get_customer_repo),
    dispatcher: GitHubCrawlDispatcher | None = Depends(get_crawl_dispatcher),
) -> CrawlSummary:
    dispatcher = _require_dispatcher(dispatcher)
    if not _CUSTOMER_RE.fullmatch(customer_id):
        raise HTTPException(
            status_code=400,
            detail="customer id is not crawlable: must match [A-Za-z0-9][A-Za-z0-9_-]*",
        )
    await customer_repo.ensure_exists(customer_id)
    crawl_id = f"cr-{uuid4().hex[:12]}"
    # Resolved here, passed explicitly: CI dates are UTC and "today" on the
    # runner can disagree with the moment the user clicked.
    crawl_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    row = await runs.insert(
        {"id": crawl_id, "customer_id": customer_id, "status": "pending", "crawl_date": crawl_date}
    )
    try:
        await dispatcher.dispatch(
            crawl_id=crawl_id, customer_id=customer_id, crawl_date=crawl_date
        )
    except CrawlDispatchError as exc:
        row = await runs.update(
            crawl_id,
            {
                "status": "failed",
                "error": f"dispatch failed: {exc}",
                "completed_at": datetime.now(timezone.utc),
            },
        )
        raise HTTPException(status_code=502, detail=f"crawl dispatch failed: {exc}") from exc
    return _summary(row)


@router.get("/crawls", response_model=list[CrawlSummary])
async def list_crawls(
    customer_id: str = Depends(current_customer_id),
    runs: CrawlRunRepo = Depends(get_crawl_run_repo),
) -> list[CrawlSummary]:
    """Last-known rows, newest first — no GitHub calls. The watch view uses
    this to rediscover an in-flight crawl after tab close/reopen, then polls
    the detail route for live status."""
    return [_summary(row) for row in await runs.list_for_customer(customer_id)]


@router.get("/crawls/{crawl_id}", response_model=CrawlSummary)
async def get_crawl(
    crawl_id: str,
    customer_id: str = Depends(current_customer_id),
    runs: CrawlRunRepo = Depends(get_crawl_run_repo),
    dispatcher: GitHubCrawlDispatcher | None = Depends(get_crawl_dispatcher),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
) -> CrawlSummary:
    row = await runs.get(crawl_id)
    if row is None or row["customer_id"] != customer_id:
        raise HTTPException(status_code=404, detail="crawl not found")
    if row["status"] in _TERMINAL:
        # Answered from the DB — finished crawls stay readable even when the
        # dispatch token is rotated out (dispatcher may be None here).
        return _summary(row)

    try:
        row, phase = await _refresh_from_github(row, runs, _require_dispatcher(dispatcher), loader)
    except CrawlDispatchError as exc:
        # A flaky GitHub call must not masquerade as a failed crawl — the
        # run row keeps its last-known status and the poller retries.
        raise HTTPException(status_code=502, detail=f"crawl status lookup failed: {exc}") from exc
    return _summary(row, phase=phase)


async def _refresh_from_github(
    row: dict,
    runs: CrawlRunRepo,
    dispatcher: GitHubCrawlDispatcher,
    loader: FeaturePackLoader,
) -> tuple[dict, str | None]:
    """Advance a non-terminal run row from the CI run's current state."""
    crawl_id = row["id"]
    if row["run_id"] is None:
        state = await dispatcher.find_run(crawl_id)
        if state is None:
            # Dispatch accepted but the run hasn't materialized yet — GitHub
            # takes a few seconds. Still pending, up to a cutoff: past it the
            # run either never got created or fell out of the lookup window,
            # and pending-forever would be a lie.
            if _age(row["created_at"]) > _MATERIALIZE_TIMEOUT:
                row = await runs.update(
                    crawl_id,
                    {
                        "status": CrawlStatus.FAILED.value,
                        "error": "run never materialized on GitHub — dispatch lost",
                        "completed_at": datetime.now(timezone.utc),
                    },
                )
            return row, None
        row = await runs.update(crawl_id, {"run_id": state.run_id, "run_url": state.html_url})
    else:
        state = await dispatcher.get_run(row["run_id"])

    status, error = _map_run_state(state)
    phase: str | None = None
    if status is CrawlStatus.RUNNING:
        phase = await dispatcher.get_phase(state.run_id)
        if row["status"] != CrawlStatus.RUNNING.value:
            # Guard against a slower concurrent poll regressing a row another
            # poll already finalized: re-read and never overwrite terminal.
            current = await runs.get(crawl_id)
            if current is not None and current["status"] in _TERMINAL:
                return current, None
            row = await runs.update(crawl_id, {"status": CrawlStatus.RUNNING.value})
    elif status in (CrawlStatus.COMPLETE, CrawlStatus.FAILED):
        fields: dict[str, object] = {
            "status": status.value,
            "error": error,
            "completed_at": datetime.now(timezone.utc),
        }
        if status is CrawlStatus.COMPLETE:
            # The pointer flip in CI already published; record what the
            # simulator now serves. Failure to read it is not a crawl failure.
            try:
                fields["snapshot_version"] = loader.resolve_latest_version(row["customer_id"])
            except Exception:
                log.warning("crawl.latest_pointer_unreadable", crawl_id=crawl_id)
        row = await runs.update(crawl_id, fields)
    return row, phase


def _require_dispatcher(dispatcher: GitHubCrawlDispatcher | None) -> GitHubCrawlDispatcher:
    if dispatcher is None:
        raise HTTPException(
            status_code=503,
            detail="SIDIRA_CRAWLER_DISPATCH_TOKEN is not configured — cannot dispatch crawls",
        )
    return dispatcher


def _age(created_at: datetime) -> timedelta:
    if created_at.tzinfo is None:  # in-memory rows are aware; be safe for DB drivers
        created_at = created_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - created_at


def _map_run_state(state: WorkflowRunState) -> tuple[CrawlStatus, str | None]:
    if state.status == "in_progress":
        return CrawlStatus.RUNNING, None
    if state.status != "completed":
        # queued / waiting / requested — and notably "pending", which GitHub
        # reports for a run held by a concurrency group (our own queueing
        # contract). Only "completed" is terminal; treat any status this code
        # predates as still pending rather than inventing a failure.
        return CrawlStatus.PENDING, None
    # completed — conclusion decides.
    if state.conclusion == "success":
        return CrawlStatus.COMPLETE, None
    if state.conclusion == "cancelled":
        # Per crawl.yml's queueing contract: GitHub holds one pending run per
        # customer; a newer dispatch cancels the previously queued one.
        return CrawlStatus.FAILED, "cancelled — superseded by a newer dispatch or stopped manually"
    return CrawlStatus.FAILED, f"CI run concluded: {state.conclusion}"


def _summary(row: dict, phase: str | None = None) -> CrawlSummary:
    return CrawlSummary(
        id=row["id"],
        customer_id=row["customer_id"],
        status=CrawlStatus(row["status"]),
        phase=phase,
        snapshot_version=row["snapshot_version"],
        run_url=row["run_url"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        error=row["error"],
    )
