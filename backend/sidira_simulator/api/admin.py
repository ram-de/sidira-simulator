"""Admin-console summary (#49) — one admin-gated, customer-scoped aggregation.

The admin console (v1: Members & roles + Data sources) needs the current state
of a workspace's *pipes* in a single read, instead of the frontend stitching
five route families (experiment-sources, feature-stores, crawls, crawl-setups,
persona-builds) by hand. This router is that one read:

    GET /admin/summary

RBAC: ``require_admin`` (council "configuration = admin"). The console as a whole
is an admin surface; the summary is its landing read, so it is admin-only. A
member who lands here gets a 403 (the frontend gates the nav entry + route too,
so a member never normally reaches it). Customer-scoped via ``current_customer_id``
exactly like every other route — a tenant only ever sees its OWN aggregate.

SECRETS: this endpoint returns COUNTS / STATUS / METADATA only. It NEVER touches
a credential blob, never decrypts anything, never echoes a host/password — it
reads the same sanitized repo rows the per-family list routes already return and
reduces them to counts + last-status. (#488 write-only-secret invariant: there
is nothing to leak here because we never read the secret columns.)

NO admin "view all conversations" backdoor: this summary deliberately does NOT
aggregate conversations / threads / `/memory` (those are per-user-private, #42).
Admin-over-org is not admin-over-person — the console must never add a cross-user
conversation view, so the aggregate stops at the workspace pipes.

PURE AGGREGATION: no new table, no migration. It calls the existing repos'
read methods and counts.
"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from sidira_simulator.adapters.repositories import (
    CrawlConfigRepo,
    CrawlRunRepo,
    ExperimentConnectionRepo,
    FeatureStoreConnectionRepo,
    PersonaBuildRepo,
)
from sidira_simulator.api.deps import (
    current_customer_id,
    get_crawl_config_repo,
    get_crawl_run_repo,
    get_experiment_connection_repo,
    get_feature_store_connection_repo,
    get_persona_build_repo,
    require_admin,
)

router = APIRouter(prefix="/admin", tags=["admin"])


class ExperimentSourcesSummary(BaseModel):
    """Counts + last-import status across the workspace's saved experiment
    sources (#46). No name → no credential, just aggregate health."""

    total: int = 0
    connected: int = 0
    error: int = 0
    last_import_at: datetime | None = None


class FeatureStoresSummary(BaseModel):
    """Counts + last-test health across saved feature-store connections.
    Health words are the same sanitized fields the list route returns."""

    total: int = 0
    ok: int = 0
    failed: int = 0
    untested: int = 0
    last_tested_at: datetime | None = None


class CrawlSummary(BaseModel):
    """Crawl setup presence + last run. ``configured`` is whether ANY crawl
    setup exists; ``last_run_status`` / ``last_run_at`` come from the most
    recent run row (None when never run)."""

    configured: bool = False
    setup_count: int = 0
    last_run_status: str | None = None
    last_run_at: datetime | None = None


class PersonasSummary(BaseModel):
    """Latest *completed* persona pack version + last build attempt. The
    pack version is provenance the console surfaces (council §reproducibility);
    ``last_build_status`` is the most recent attempt regardless of outcome."""

    pack_version: str | None = None
    persona_count: int | None = None
    last_build_status: str | None = None
    last_build_at: datetime | None = None
    total_builds: int = 0


class ConsoleSummary(BaseModel):
    """The admin-console landing aggregate. Counts / status / metadata only —
    no secrets, no per-user conversation data."""

    customer_id: str
    experiment_sources: ExperimentSourcesSummary
    feature_stores: FeatureStoresSummary
    crawl: CrawlSummary
    personas: PersonasSummary


def _max_dt(current: datetime | None, candidate: datetime | None) -> datetime | None:
    """Newest of two optional timestamps (tz-naive/aware are not mixed here:
    every repo stamps tz-aware UTC, the in-memory repos likewise)."""
    if candidate is None:
        return current
    if current is None:
        return candidate
    return max(current, candidate)


@router.get(
    "/summary",
    response_model=ConsoleSummary,
    dependencies=[Depends(require_admin)],  # #49: admin-console landing read
)
async def get_console_summary(
    customer_id: str = Depends(current_customer_id),
    experiment_repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
    feature_repo: FeatureStoreConnectionRepo = Depends(get_feature_store_connection_repo),
    crawl_config_repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
    crawl_run_repo: CrawlRunRepo = Depends(get_crawl_run_repo),
    persona_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
) -> ConsoleSummary:
    """Aggregate the workspace's current pipe-state into one read. Admin-only,
    customer-scoped, secret-free. Every repo call below is read-only and already
    customer-scoped; we only COUNT and pick the newest timestamp — no secret
    column is ever touched."""

    # ── Experiment sources (#46) ────────────────────────────────────────────
    exp_rows = await experiment_repo.list_for_customer(customer_id)
    exp = ExperimentSourcesSummary(total=len(exp_rows))
    for row in exp_rows:
        status = row.get("status")
        if status == "connected":
            exp.connected += 1
        elif status == "error":
            exp.error += 1
        exp.last_import_at = _max_dt(exp.last_import_at, row.get("last_import_at"))

    # ── Feature stores ──────────────────────────────────────────────────────
    fs_rows = await feature_repo.list_for_customer(customer_id)
    fs = FeatureStoresSummary(total=len(fs_rows))
    for row in fs_rows:
        status = row.get("last_test_status")
        if status == "ok":
            fs.ok += 1
        elif status == "failed":
            fs.failed += 1
        else:
            fs.untested += 1
        fs.last_tested_at = _max_dt(fs.last_tested_at, row.get("last_tested_at"))

    # ── Crawl (setup presence + last run) ───────────────────────────────────
    crawl_setups = await crawl_config_repo.list(customer_id)
    crawl_runs = await crawl_run_repo.list_for_customer(customer_id, limit=1)
    last_run = crawl_runs[0] if crawl_runs else None
    crawl = CrawlSummary(
        configured=len(crawl_setups) > 0,
        setup_count=len(crawl_setups),
        last_run_status=(last_run.get("status") if last_run else None),
        last_run_at=(last_run.get("created_at") if last_run else None),
    )

    # ── Personas (latest completed pack + last attempt) ─────────────────────
    builds = await persona_repo.list_recent(customer_id, limit=50)
    personas = PersonasSummary(total_builds=len(builds))
    if builds:
        # list_recent is newest-first → builds[0] is the most recent attempt.
        latest = builds[0]
        personas.last_build_status = latest.get("status")
        personas.last_build_at = latest.get("created_at")
        # The current pack is the newest COMPLETED build's version, which may not
        # be the most recent attempt (a later build can be running/failed).
        for row in builds:
            if row.get("status") == "complete" and row.get("pack_version"):
                personas.pack_version = row.get("pack_version")
                personas.persona_count = row.get("persona_count")
                break

    return ConsoleSummary(
        customer_id=customer_id,
        experiment_sources=exp,
        feature_stores=fs,
        crawl=crawl,
        personas=personas,
    )
