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

import json
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ValidationError

from sidira_simulator.api.deps import (
    current_customer_id,
    get_crawl_config_repo,
    get_crawl_dispatcher,
    get_crawl_run_repo,
    get_customer_repo,
    get_feature_pack_loader,
    require_admin,
)
from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.adapters.github_actions import (
    CrawlDispatchError,
    GitHubCrawlDispatcher,
    WorkflowRunState,
)
from sidira_simulator.adapters.repositories import (
    DEFAULT_SETUP_ID,
    CrawlConfigRepo,
    CrawlRunRepo,
    CustomerRepo,
)
from sidira_simulator.schemas.crawl import (
    CrawlSetup,
    CrawlSetupCreateInput,
    CrawlSetupEnvelope,
    CrawlSetupInput,
    CrawlSetupListItem,
    CrawlSetupSummary,
    is_safe_setup_id,
    make_setup_id,
)
from sidira_simulator.services.runtime_config import resolve_sidira_env

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

# The one customer that may crawl without a saved setup: the streamly-sandbox
# demo runs crawl.yml's hardcoded mock acceptance path (#206 Slice B keeps it).
# Every real tenant must configure capabilities + a sandbox URL first.
_SANDBOX_CUSTOMER = "streamly-sandbox"

# Reserved key inside config_json holding the at-rest-encrypted role→password
# map (#206 Slice C). It rides alongside the password-free CrawlSetup fields;
# CrawlSetup.model_validate ignores it on rehydration (extra keys are dropped),
# and the authenticated crawler-pull endpoint is the only reader. Shared with
# api/internal.py — keep the two in lockstep.
CREDENTIALS_ENC_KEY = "credentials_enc"

# Env suffix for the CI-only bearer that authorizes the credential pull
# (api/internal.py imports this so the two stay in lockstep). resolve_sidira_env
# applies the SIDIRA_ → PYTHIA_ fallback. The dispatch preflight checks it so a
# real tenant isn't dispatched into a crawl whose credential pull would 503.
CRAWLER_CREDENTIALS_TOKEN_SUFFIX = "CRAWLER_CREDENTIALS_TOKEN"


def _rehydrate_setup(row: dict) -> CrawlSetup:
    """Validate a persisted crawl-setup row back into a CrawlSetup.

    Field validation also runs on read, so a row saved under looser rules
    (e.g. a basic-auth URL accepted before #206 tightened ``_require_http_url``)
    would otherwise surface as an opaque 500. Convert that to a 409 telling the
    operator to re-save, instead of a server error (codex P2, #206)."""
    try:
        return CrawlSetup.model_validate(row["config_json"])
    except ValidationError as exc:
        raise HTTPException(
            status_code=409,
            detail="saved crawl setup is no longer valid — re-save it on the crawl setup window",
        ) from exc


# A dispatched run materializes on GitHub within seconds. If it still cannot
# be found after this long, the run either never got created or fell out of
# the lookup window — without a cutoff the row would report pending forever.
_MATERIALIZE_TIMEOUT = timedelta(minutes=15)


class CrawlTriggerInput(BaseModel):
    """Optional ``POST /crawls`` body. ``setup_id`` selects which saved crawl
    setup the run uses (#215/#245); it defaults to ``"default"`` so an empty
    body (or no body) is byte-identical to today's single-setup dispatch."""

    setup_id: str = DEFAULT_SETUP_ID


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
        setup=_rehydrate_setup(row),
        updated_at=row["updated_at"],
    )


def _build_stored_config(payload: CrawlSetupInput, customer_id: str) -> dict:
    """Split a write-path payload into the persisted config_json blob.

    The password-free setup persists as cleartext JSON; the role→password map is
    encrypted at rest and stashed under CREDENTIALS_ENC_KEY (#206 Slice C).
    Passwords never touch config_json in cleartext, never come back out of GET,
    and reach CI only via the authenticated crawler pull. The encryption is keyed
    on ``customer_id`` (NOT setup_id) — every setup of one org shares the org's
    key material, exactly as the single-setup path always did."""
    stored = payload.to_setup().model_dump()
    try:
        blob = credentials.encrypt(payload.credential_secrets(), customer_id=customer_id)
    except credentials.CredentialError as exc:
        # No key material configured — saving a login we cannot protect would be
        # worse than refusing. Surface a 503 instead of an opaque 500.
        raise HTTPException(
            status_code=503,
            detail="credential storage is not configured — set SIDIRA_LOCAL_CRED_KEY",
        ) from exc
    stored[CREDENTIALS_ENC_KEY] = credentials.serialize_blob(blob)
    return stored


@router.put(
    "/crawl-setup",
    response_model=CrawlSetupEnvelope,
    dependencies=[Depends(require_admin)],  # #45: crawl config + encrypted login creds — admin-only
)
async def save_crawl_setup(
    payload: CrawlSetupInput,
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
    customer_repo: CustomerRepo = Depends(get_customer_repo),
) -> CrawlSetupEnvelope:
    # Same signup-then-act guard as the simulation path: the customer row may
    # not exist yet when the first thing a tenant does is save a crawl setup.
    await customer_repo.ensure_exists(customer_id)
    stored = _build_stored_config(payload, customer_id)
    row = await repo.upsert(customer_id, stored)
    return CrawlSetupEnvelope(
        customer_id=customer_id,
        setup=_rehydrate_setup(row),
        updated_at=row["updated_at"],
    )


# ── Multi-setup CRUD (#215/#245 PR 2) ──────────────────────────────────────
# These sit ALONGSIDE the singular /crawl-setup endpoints above, which keep
# operating on the "default" setup unchanged (the current frontend still calls
# them; PR 3 migrates the UI). All routes are customer-scoped via the same
# current_customer_id dependency; cross-tenant access 404s (the 404-wall
# convention), never 403. No GET on this group EVER returns a credential.


def _setup_list_item(row: dict) -> CrawlSetupListItem:
    setup = _rehydrate_setup(row)
    return CrawlSetupListItem(
        setup_id=row["setup_id"],
        name=row.get("name"),
        sandbox_url=setup.sandbox_url,
        capability_count=len(setup.capabilities),
        cadence=setup.cadence,
        updated_at=row.get("updated_at"),
    )


def _setup_summary(row: dict) -> CrawlSetupSummary:
    return CrawlSetupSummary(
        setup_id=row["setup_id"],
        name=row.get("name"),
        setup=_rehydrate_setup(row),
        updated_at=row.get("updated_at"),
    )


@router.get("/crawl-setups", response_model=list[CrawlSetupListItem])
async def list_crawl_setups(
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
) -> list[CrawlSetupListItem]:
    """List every crawl setup for the caller's org, newest-anchor first.

    Secret-free: each row carries identity + label + the non-secret config
    fields only. Passwords never leave the encrypted blob; the authenticated CI
    pull is the sole reader."""
    return [_setup_list_item(row) for row in await repo.list(customer_id)]


@router.post(
    "/crawl-setups",
    response_model=CrawlSetupSummary,
    status_code=201,
    dependencies=[Depends(require_admin)],  # #45: crawl config + encrypted login creds — admin-only
)
async def create_crawl_setup(
    payload: CrawlSetupCreateInput,
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
    customer_repo: CustomerRepo = Depends(get_customer_repo),
) -> CrawlSetupSummary:
    """Create a NEW crawl setup under a server-minted, url-safe setup_id.

    The client supplies a human ``name``; the server slugifies it and adds a
    uniqueness suffix (the client never picks the raw id). Minting can never
    collide with the reserved ``"default"`` anchor — :func:`make_setup_id`
    treats it as taken. Credentials follow the #206 pull model: re-entered on
    create, encrypted at rest, never returned. The response carries no secrets."""
    await customer_repo.ensure_exists(customer_id)
    existing = {row["setup_id"] for row in await repo.list(customer_id)}
    setup_id = make_setup_id(payload.name, existing)
    stored = _build_stored_config(payload, customer_id)
    row = await repo.upsert(customer_id, stored, setup_id=setup_id, name=payload.name)
    return _setup_summary(row)


@router.get("/crawl-setups/{setup_id}", response_model=CrawlSetupSummary)
async def get_crawl_setup_by_id(
    setup_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
) -> CrawlSetupSummary:
    """One setup by id, secret-free. 404 when it does not exist for this org
    (the same 404 a cross-tenant id gets — scope is enforced by customer_id)."""
    row = await repo.get(customer_id, setup_id)
    if row is None:
        raise HTTPException(status_code=404, detail="crawl setup not found")
    return _setup_summary(row)


@router.put(
    "/crawl-setups/{setup_id}",
    response_model=CrawlSetupSummary,
    dependencies=[Depends(require_admin)],  # #45: crawl config + encrypted login creds — admin-only
)
async def update_crawl_setup_by_id(
    setup_id: str,
    payload: CrawlSetupInput,
    name: str | None = None,
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
) -> CrawlSetupSummary:
    """Update an existing setup's config (and optionally its ``?name=`` label).

    404 if the setup_id does not already exist for this org — PUT here updates,
    it does not create (creation is POST, which mints the id). Credentials follow
    the #206 pull model: re-entered on each save, encrypted at rest, never
    returned. The response carries no secrets."""
    if await repo.get(customer_id, setup_id) is None:
        raise HTTPException(status_code=404, detail="crawl setup not found")
    stored = _build_stored_config(payload, customer_id)
    row = await repo.upsert(customer_id, stored, setup_id=setup_id, name=name)
    return _setup_summary(row)


@router.delete(
    "/crawl-setups/{setup_id}",
    status_code=204,
    dependencies=[
        Depends(require_admin)
    ],  # #45: deletes a crawl config (+ its stored creds) — admin-only
)
async def delete_crawl_setup_by_id(
    setup_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
) -> None:
    """Delete a setup's CONFIG row only. 204 on success.

    CONFIG-ONLY by design — this NEVER touches R2: the setup's Feature-Pack
    objects stay in place, so any historical simulation that froze a pack from
    this setup still resolves (mirrors #214's integrity invariant; the
    FeaturePackLoader reads R2 by path and never consults this row).

    Refuses to delete the reserved ``"default"`` setup (409): it is the legacy
    anchor and the target of the singular /crawl-setup endpoints + the legacy R2
    prefix. 404 if the setup_id does not exist for this org."""
    if setup_id == DEFAULT_SETUP_ID:
        raise HTTPException(
            status_code=409,
            detail="the default crawl setup cannot be deleted",
        )
    if await repo.get(customer_id, setup_id) is None:
        raise HTTPException(status_code=404, detail="crawl setup not found")
    await repo.delete(customer_id, setup_id)
    return None


@router.post("/crawls", response_model=CrawlSummary, status_code=202)
async def create_crawl(
    payload: CrawlTriggerInput | None = None,
    customer_id: str = Depends(current_customer_id),
    runs: CrawlRunRepo = Depends(get_crawl_run_repo),
    customer_repo: CustomerRepo = Depends(get_customer_repo),
    config_repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
    dispatcher: GitHubCrawlDispatcher | None = Depends(get_crawl_dispatcher),
) -> CrawlSummary:
    dispatcher = _require_dispatcher(dispatcher)
    # No body (or {}) → the default setup, byte-identical to today's dispatch.
    setup_id = payload.setup_id if payload is not None else DEFAULT_SETUP_ID
    # setup_id rides to CI as product_id and becomes an R2 KEY SEGMENT there, so
    # hold it to the same safe-segment rule the prefix helper enforces — a
    # path-traversal value must never cross the dispatch boundary (codex P1).
    if not is_safe_setup_id(setup_id):
        raise HTTPException(status_code=400, detail="invalid setup_id")
    if not _CUSTOMER_RE.fullmatch(customer_id):
        raise HTTPException(
            status_code=400,
            detail="customer id is not crawlable: must match [A-Za-z0-9][A-Za-z0-9_-]*",
        )
    # The saved setup drives the production walk (#206). Resolve THAT setup's
    # config before inserting the run row so an unconfigured tenant 400s instead
    # of leaving a pending row that could never produce a pack.
    config_json = await _resolve_dispatch_config(customer_id, config_repo, setup_id)
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
            crawl_id=crawl_id,
            customer_id=customer_id,
            crawl_date=crawl_date,
            config_json=config_json,
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
            #
            # KNOWN LIMITATION (#215/#245, deferred to PR 3): this reads the
            # DEFAULT setup's `latest` pointer. The crawl_runs row does not yet
            # carry setup_id (adding it is a migration, out of this PR's scope),
            # so a NAMED-setup crawl records the wrong/default snapshot_version
            # here — a cosmetic provenance field on the run row only. It does NOT
            # affect pack resolution (the named pack is correctly written under
            # its own prefix by CI and resolves via ?setup_id=), nor the default
            # path, which stays byte-identical. PR 3 adds crawl_runs.setup_id and
            # passes it here. (codex P2)
            try:
                fields["snapshot_version"] = loader.resolve_latest_version(row["customer_id"])
            except Exception:
                log.warning("crawl.latest_pointer_unreadable", crawl_id=crawl_id)
        row = await runs.update(crawl_id, fields)
    return row, phase


async def _resolve_dispatch_config(
    customer_id: str, config_repo: CrawlConfigRepo, setup_id: str = DEFAULT_SETUP_ID
) -> str | None:
    """Load the chosen crawl setup and project it to the non-secret JSON the
    dispatch carries. Returns None for the streamly-sandbox demo (no setup
    needed — it runs the mock path); 400s for any other unconfigured tenant.

    ``setup_id`` (default ``"default"``) rides the dispatch as ``product_id`` so
    CI (a) pulls THAT setup's credentials from /internal/crawl-credentials and
    (b) writes the produced pack under the matching per-setup R2 prefix. For the
    default setup product_id is ``"default"`` — byte-identical to today."""
    row = await config_repo.get(customer_id, setup_id)
    if row is None:
        if customer_id == _SANDBOX_CUSTOMER and setup_id == DEFAULT_SETUP_ID:
            return None
        raise HTTPException(
            status_code=400,
            detail=(
                "no crawl setup saved — configure capabilities and a sandbox URL "
                "before triggering a crawl"
            ),
        )
    setup = _rehydrate_setup(row)
    if customer_id != _SANDBOX_CUSTOMER:
        # Real tenants pull logins from /internal/crawl-credentials at run start.
        # Verify that pull will succeed *before* spending a ~40-min CI walk.
        _require_dispatchable_credentials(setup, row["config_json"], customer_id)
    return json.dumps(setup.dispatch_payload(product_id=setup_id), separators=(",", ":"))


def _require_dispatchable_credentials(
    setup: CrawlSetup, config_json: dict, customer_id: str
) -> None:
    """Fail closed if the run-start credential pull could not succeed.

    The crawler can only log in if (a) an encrypted blob is stored, (b) the
    pull bearer is configured, and (c) the blob actually decrypts to a login
    for every role. Anything else means CI would start a doomed, login-less
    crawl — so reject here instead (codex P2, #206 Slice C)."""
    enc = config_json.get(CREDENTIALS_ENC_KEY)
    if not enc:
        # Setup saved before Slice C (or otherwise missing the blob).
        raise HTTPException(
            status_code=400,
            detail=(
                "saved crawl setup has no stored login credentials — re-save it "
                "on the crawl setup window before triggering a crawl"
            ),
        )
    if not resolve_sidira_env(CRAWLER_CREDENTIALS_TOKEN_SUFFIX):
        # Server misconfiguration: the pull route would 503 for every customer.
        raise HTTPException(
            status_code=503,
            detail=(
                "crawler credential pull is not configured — "
                "set SIDIRA_CRAWLER_CREDENTIALS_TOKEN"
            ),
        )
    try:
        secrets = credentials.decrypt(credentials.deserialize_blob(enc), customer_id=customer_id)
    except credentials.CredentialError as exc:
        # Key rotated after the blob was written, or stored ciphertext corrupted
        # — the pull would 503. Re-saving the setup re-encrypts under the live key.
        raise HTTPException(
            status_code=503,
            detail=(
                "stored crawl credentials cannot be decrypted — re-save the crawl "
                "setup (was SIDIRA_LOCAL_CRED_KEY rotated?)"
            ),
        ) from exc
    missing = [u.role for u in setup.test_users if u.role not in secrets]
    if missing:
        # Blob decrypts but is missing a login the setup expects (e.g. a role
        # added after the last save). The pull would deliver a partial login set.
        raise HTTPException(
            status_code=400,
            detail=(
                "stored credentials are missing logins for: "
                f"{', '.join(missing)} — re-save the crawl setup"
            ),
        )


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
