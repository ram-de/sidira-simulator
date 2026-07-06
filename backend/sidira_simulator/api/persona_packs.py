"""Persona pack routes — list all versions, read one, promote a draft to latest."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sidira_simulator.adapters.base import (
    ArtifactNotFound,
    ArtifactSchemaError,
    load_json_artifact,
)
from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import ArtifactStore
from sidira_simulator.adapters.repositories import PersonaBuildRepo
from sidira_simulator.api.deps import (
    current_customer_id,
    get_artifact_store,
    get_persona_build_repo,
    get_persona_loader,
)
from sidira_simulator.schemas.estimability import EstimabilityManifest
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services.grounded_predictor import estimability_manifest_key
from sidira_simulator.services.lever_card_view import (
    LeverCardManifest,
    build_lever_card_view,
)
from sidira_simulator.services.persona_pack_view import (
    PersonaPackDetail,
    build_persona_pack_detail,
)

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/persona-packs", tags=["persona-packs"])

# Sentinel pack_id that resolves to the customer's active pack via the `latest`
# pointer, so the Library can deep-link to "the current pack" without first
# fetching its version. Mirrors how the Feature Pack browse page addresses the
# latest snapshot (#207).
LATEST = "latest"


class PackStatus(str, Enum):
    DRAFT = "draft"
    PROMOTED = "promoted"
    RETIRED = "retired"


class PackSummary(BaseModel):
    """Lightweight pack metadata for list views."""

    id: str
    version: str
    status: PackStatus
    stability_score: float
    persona_count: int
    created_at: datetime
    promoted_at: datetime | None = None
    is_latest: bool = False


def _resolve_latest_version(loader: PersonaPackLoader, customer_id: str) -> str | None:
    """The version the `latest` pointer resolves to, or None if unset."""
    try:
        return loader.resolve_latest_version(customer_id)
    except ArtifactNotFound:
        return None


def _summary_from_build(row: dict, latest_version: str | None) -> PackSummary:
    """Map a COMPLETE persona_build_runs row → PackSummary.

    The pack is addressed by its `pack_version` string (e.g. "v_3"), the same
    id `GET /{pack_id}` and `POST /{pack_id}/promote` accept. The version that
    the `latest` pointer resolves to is PROMOTED + is_latest; all others DRAFT.
    """
    version = row["pack_version"]
    is_latest = latest_version is not None and version == latest_version
    return PackSummary(
        id=version,
        version=version,
        status=PackStatus.PROMOTED if is_latest else PackStatus.DRAFT,
        stability_score=row.get("stability_score") or 0.0,
        persona_count=row.get("persona_count") or 0,
        created_at=row["created_at"],
        promoted_at=row.get("completed_at") if is_latest else None,
        is_latest=is_latest,
    )


@router.get("", response_model=list[PackSummary])
async def list_packs(
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
    build_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
) -> list[PackSummary]:
    """List all pack versions for the customer, newest first.

    Each COMPLETE persona build that produced a `pack_version` is one pack
    version. The build repo already returns rows newest-first. The current
    `latest` pointer flags the matching version PROMOTED; an empty tenant
    returns `[]` (not a 404)."""
    latest_version = _resolve_latest_version(loader, customer_id)
    # Every pack version is one COMPLETE build; the default 50-row recent page
    # would hide older versions for a heavy customer. Raise the cap so the
    # Library lists all versions (smaller change than a new "list all" path; the
    # bound stays generous rather than unbounded).
    builds = await build_repo.list_recent(customer_id, limit=1000)
    return [
        _summary_from_build(row, latest_version)
        for row in builds
        if row.get("status") == "complete" and row.get("pack_version")
    ]


def _load_pack(loader: PersonaPackLoader, customer_id: str, pack_id: str) -> PersonaPack:
    """Resolve a pack id to its contents, applying the `latest`/starter rules.

    `pack_id="latest"` resolves the active pack via the `latest` pointer — the
    same in-memory starter fallback as `GET /personas` (#212): a tenant with no
    pack yet gets the generic starter pack (`is_starter=True`) so the page
    renders rather than 404-ing. An explicit version loads that exact snapshot
    and 404s if it is missing (a real not-found, not an empty tenant).
    """
    try:
        if pack_id == LATEST:
            return loader.load_latest(customer_id)
        return loader.load_at_version(customer_id, pack_id)
    except ArtifactNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"No persona pack {pack_id!r} for customer {customer_id!r}.",
        ) from exc


@router.get("/{pack_id}", response_model=PersonaPack)
async def get_pack(
    pack_id: str,
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
) -> PersonaPack:
    """Full raw pack contents — persona descriptions, weights, stability.

    The producer→consumer `PersonaPack` as-is, including the v1.1 model-input
    arrays (`centroid_full` / `feature_scale` / `sample_rows`). For the
    human-facing rendered view (the behavioral-comparison blocks, weight schemes,
    honesty flags) the Library detail page uses `/{pack_id}/detail` instead.
    """
    return _load_pack(loader, customer_id, pack_id)


@router.get("/{pack_id}/detail", response_model=PersonaPackDetail)
async def get_pack_detail(
    pack_id: str,
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
) -> PersonaPackDetail:
    """Read-only presentation view for the Library's persona-pack detail page (#25).

    Renders each persona's centroid **"How you compare"** block and per-member
    **individual-row** block through the single-sourced honesty/salience logic in
    `behavioral_profile.py`, folds the three weight schemes into per-persona
    shares (with a truthful reason when an optional scheme is unavailable), and
    surfaces the stability/honesty flags — without echoing the bulky raw v1.1
    arrays. On a v1.0 pack the individual-row block degrades to absent (honest
    empty-state), never a fabricated row. Same `latest`/starter/404 rules as the
    raw `GET /{pack_id}`.
    """
    return build_persona_pack_detail(_load_pack(loader, customer_id, pack_id))


@router.get("/{pack_id}/estimability", response_model=LeverCardManifest)
async def get_pack_estimability(
    pack_id: str,
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
    store: ArtifactStore = Depends(get_artifact_store),
) -> LeverCardManifest:
    """Reviewable "lever cards" for a pack — the estimability manifest, projected (#565).

    Surfaces the build-time estimability manifest (written beside the persona pack
    in R2 by the worker) as a list of per-(treatment→outcome) review cards: the
    direction-only verdict plus the negative-control guard evidence a human uses
    to sanity-check what the engine will and won't trust. The treatment's own
    effect MAGNITUDES are stripped in the view (direction-only product); the NC
    residuals are carried through as trust diagnostics.

    Version resolution mirrors the other pack routes: ``latest`` resolves via the
    pointer (404 when no pack exists yet), an explicit version reads that exact
    snapshot's manifest. The manifest is OPTIONAL — a pack built before the
    precompute shipped simply has none, which is a real 404 ("no lever data yet",
    the frontend's honest empty-state), not an error. A present-but-malformed
    manifest also degrades to 404 (logged) rather than 500-ing the page: this read
    is never allowed to break the detail surface.
    """
    if pack_id == LATEST:
        version = _resolve_latest_version(loader, customer_id)
        if version is None:
            raise HTTPException(
                status_code=404,
                detail=f"No persona pack for customer {customer_id!r}.",
            )
    else:
        version = pack_id

    key = estimability_manifest_key(customer_id, version)
    try:
        manifest = load_json_artifact(store, key, EstimabilityManifest)
    except ArtifactNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"No estimability manifest for pack {version!r} (customer {customer_id!r}).",
        ) from exc
    except ArtifactSchemaError as exc:
        # A corrupt/incompatible artifact must not 500 the detail page — degrade
        # to the same empty-state as "absent", but log loudly so it's caught.
        log.warning(
            "persona_packs.estimability_manifest_malformed",
            customer_id=customer_id,
            pack_version=version,
            error=str(exc),
        )
        raise HTTPException(
            status_code=404,
            detail=f"Estimability manifest for pack {version!r} is unreadable.",
        ) from exc

    return build_lever_card_view(manifest)


@router.post("/{pack_id}/promote", response_model=PackSummary)
async def promote_pack(
    pack_id: str,
    customer_id: str = Depends(current_customer_id),
    loader: PersonaPackLoader = Depends(get_persona_loader),
    build_repo: PersonaBuildRepo = Depends(get_persona_build_repo),
) -> PackSummary:
    """Atomically update the customer's `latest` pointer to this pack version.

    `pack_id` is a concrete version string (e.g. "v_3"); the `LATEST` sentinel
    is a read-only convenience for GET, not a promote target. The version must
    exist for this customer — a COMPLETE build with that `pack_version`, or a
    snapshot that `load_at_version` can read — otherwise 404. Promotion is a
    single pointer write through the loader (one key, shared with the read
    path), after which `load_latest` resolves to this version.
    """
    if pack_id == LATEST:
        raise HTTPException(
            status_code=400, detail="Promote a concrete pack version, not the 'latest' sentinel."
        )

    # Direct (customer, version) lookup with no recent-page cap, so promoting an
    # older complete version still resolves its build row (correct PackSummary
    # metadata) for customers with >50 builds.
    match = await build_repo.get_by_pack_version(customer_id, pack_id)
    if match is None:
        # No build row, but the snapshot may still exist in R2 — accept it iff
        # the versioned pack is readable; otherwise it is a genuine not-found.
        try:
            loader.load_at_version(customer_id, pack_id)
        except ArtifactNotFound as exc:
            raise HTTPException(
                status_code=404,
                detail=f"No persona pack version {pack_id!r} for customer {customer_id!r}.",
            ) from exc

    loader.promote(customer_id, pack_id)

    if match is not None:
        return _summary_from_build(match, pack_id)
    return PackSummary(
        id=pack_id,
        version=pack_id,
        status=PackStatus.PROMOTED,
        stability_score=0.0,
        persona_count=0,
        created_at=datetime.now(timezone.utc),
        is_latest=True,
    )
