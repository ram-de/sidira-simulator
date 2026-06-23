"""Capabilities route — lists capabilities from the customer's latest Feature Pack."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sidira_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from sidira_simulator.adapters.feature_pack_loader import (
    FeaturePackLoader,
    UnsafeSetupId,
    feature_pack_prefix,
)
from sidira_simulator.adapters.repositories import (
    DEFAULT_SETUP_ID,
    ArchivedFeaturePackRepo,
)
from sidira_simulator.api.deps import (
    current_customer_id,
    get_archived_feature_pack_repo,
    get_feature_pack_loader,
)
from sidira_simulator.schemas.feature_pack import (
    ArchiveState,
    CapabilityRecord,
    CapabilitySummary,
    FeaturePackManifest,
    FeaturePackSummary,
)


def _validate_setup_id(setup_id: str) -> None:
    """404 (the 404-wall convention) on a setup_id that is not a safe R2 key
    segment — a path-traversal attempt resolves to "no such pack", never a 500
    or a cross-tenant read (codex P1). The default setup is always safe."""
    if setup_id == DEFAULT_SETUP_ID:
        return
    try:
        feature_pack_prefix("_probe", setup_id)
    except UnsafeSetupId as exc:
        raise HTTPException(status_code=404, detail="feature pack not found") from exc


router = APIRouter(prefix="/capabilities", tags=["capabilities"])

# The archive/unarchive actions live under the pack's OWN prefix (a pack VERSION
# is the subject, not a capability), mirroring why `/feature-pack/summary` sits
# apart from `/capabilities/`. Shared with `summary_router` below.

# The pack-summary projection lives under its OWN prefix, NOT as /capabilities/summary.
# A sibling static segment under /capabilities would collide with the dynamic
# /capabilities/{capability_name} detail route for any capability literally named
# `summary` — and that name can arrive in a manifest we don't validate (the crawler
# is a separate repo; manifests are read straight from R2). A dedicated prefix makes
# the collision structurally impossible regardless of manifest provenance, so no
# slug needs reserving. (#207)
summary_router = APIRouter(prefix="/feature-pack", tags=["capabilities"])

# Archive (soft-delete / hide-from-Library) for a pack VERSION (#214). Its own
# prefix because the subject is a pack version, not a capability — and a version
# string like `2026-W21` would never be a valid capability slug anyway.
archive_router = APIRouter(prefix="/featurepacks", tags=["capabilities"])


@router.get("", response_model=FeaturePackManifest)
async def list_capabilities(
    include_archived: bool = False,
    setup_id: str = DEFAULT_SETUP_ID,
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
    archived_repo: ArchivedFeaturePackRepo = Depends(get_archived_feature_pack_repo),
) -> FeaturePackManifest:
    """Return the latest Feature Pack manifest for the authenticated customer.

    ``?setup_id=`` selects which crawl setup's packs to list (#215/#245). It
    defaults to ``"default"`` so an unparameterized call is byte-identical to
    pre-#215 prod — same R2 prefix, same pointer.

    By default the Library hides any version the customer ARCHIVED (#214): if the
    latest pack is archived, this 404s exactly as an empty tenant would, so the
    Library shows the empty-pack state rather than a version the PM chose to retire.
    Pass ``?include_archived=true`` to see it anyway (the Library's "Show archived"
    toggle). Archiving never deletes the pack: a historical simulation that froze
    this version still resolves it (FeaturePackLoader never consults this marker).
    """
    _validate_setup_id(setup_id)
    try:
        manifest = loader.load_latest_manifest(customer_id, setup_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    archived = await archived_repo.is_archived(customer_id, manifest.snapshot_version)
    if archived and not include_archived:
        raise HTTPException(
            status_code=404,
            detail=f"feature pack {manifest.snapshot_version!r} is archived",
        )
    # Report the TRUE archive state so the Library labels the version and offers
    # the right archive ⇄ unarchive action from fact, not from the toggle (#214).
    manifest.archived = archived
    return manifest


@summary_router.get("/summary", response_model=FeaturePackSummary)
async def list_capabilities_summary(
    include_archived: bool = False,
    setup_id: str = DEFAULT_SETUP_ID,
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
    archived_repo: ArchivedFeaturePackRepo = Depends(get_archived_feature_pack_repo),
) -> FeaturePackSummary:
    """Return the latest pack as lightweight `{name, roles}` rows + provenance.

    Powers the Library browse page's group-by-role view (#207): the names-only
    manifest can't carry `roles`, and shipping every full capability body just to
    read them would be wasteful, so this projects each capability to name + roles.

    Served at `/feature-pack/summary`, deliberately OUTSIDE the `/capabilities/`
    prefix: a `/capabilities/summary` sibling would shadow the dynamic
    `/capabilities/{capability_name}` detail route for a capability named `summary`,
    and that name can reach us in a manifest the crawler (a separate repo) wrote
    without passing our input validation. A separate prefix removes the collision
    structurally, so no capability slug has to be reserved.

    Same TOCTOU discipline as :func:`get_capability`: the manifest is loaded once
    and every per-capability read is pinned to `manifest.snapshot_version`, so a
    `latest`-pointer flip mid-request can't mix capabilities across snapshots.
    404 when the pack or its `latest` pointer is missing.

    Resilient per capability: a name in the manifest whose body is missing or has
    corrupt reverse-Figma is returned with `roles: []` rather than 502-ing the
    whole list — the name is manifest-guaranteed so the row still appears, and its
    detail route surfaces the real error on open.

    Cost: O(N) artifact reads per request (loads each capability fully to project
    `roles`). `domain` is now free — it rides the manifest's `capability_domains`
    map (sidira-crawler#18), no per-capability read. Fully collapsing this to a
    single manifest read still needs `roles` persisted in the manifest too (a
    `capability_roles` field, a small crawler follow-up); fine at today's pack
    size (~tens of capabilities) until then.
    """
    _validate_setup_id(setup_id)
    try:
        manifest = loader.load_latest_manifest(customer_id, setup_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    # Mirror the manifest route's archive filter (#214): a retired latest pack
    # reads as 404 (empty) for the browse view unless the toggle is on.
    if not include_archived and await archived_repo.is_archived(
        customer_id, manifest.snapshot_version
    ):
        raise HTTPException(
            status_code=404,
            detail=f"feature pack {manifest.snapshot_version!r} is archived",
        )
    summaries: list[CapabilitySummary] = []
    for name in manifest.capabilities:
        # `domain` rides along from the manifest's grouping index (#244 / crawler
        # #18) — no extra read, and it survives even when the body is missing.
        domain = manifest.capability_domains.get(name)
        try:
            capability = loader.load_capability(
                customer_id, manifest.snapshot_version, name, setup_id
            )
            summaries.append(
                CapabilitySummary(name=capability.name, roles=capability.roles, domain=domain)
            )
        except (ArtifactNotFound, ArtifactSchemaError):
            # Keep the list complete; the detail route surfaces the real error.
            summaries.append(CapabilitySummary(name=name, roles=[], domain=domain))
    return FeaturePackSummary(
        customer_id=customer_id,
        snapshot_version=manifest.snapshot_version,
        generated_at=manifest.generated_at,
        capabilities=summaries,
    )


@router.get("/{capability_name}", response_model=CapabilityRecord)
async def get_capability(
    capability_name: str,
    setup_id: str = DEFAULT_SETUP_ID,
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
) -> CapabilityRecord:
    """Return a single capability — reverse-PRD + reverse-Figma — from the latest pack.

    Wrapped in a :class:`CapabilityRecord` so the snapshot version + capture
    timestamp that the Library's record header shows come from the SAME read that
    served the body (#207, DESIGN.md §7.6), not a second `latest` lookup.

    Powers the Library's capability-detail page (#207 browsability). 404 when the
    pack, the `latest` pointer, or the named capability is missing; 502 when the
    stored reverse-Figma fails schema validation (corrupt/stale artifact).

    Membership is gated on the latest manifest, not on the storage path alone: a
    crawl that drops a capability rewrites the manifest but may leave the old
    `capabilities/<name>/` directory behind, so loading by path would serve an
    orphaned artifact that the manifest-driven Library list no longer shows. We
    404 anything absent from `manifest.capabilities` so a direct or bookmarked
    URL can't surface a dropped capability as if it were current.

    Both reads are pinned to `manifest.snapshot_version` rather than resolving
    `latest` twice: a crawl that flips the pointer between the manifest load and
    the capability load could otherwise serve a capability from a different pack
    than the one whose membership we checked (TOCTOU), reintroducing the orphan.
    """
    _validate_setup_id(setup_id)
    try:
        manifest = loader.load_latest_manifest(customer_id, setup_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if capability_name not in manifest.capabilities:
        raise HTTPException(
            status_code=404,
            detail=f"capability {capability_name!r} is not in the latest pack",
        )
    try:
        capability = loader.load_capability(
            customer_id, manifest.snapshot_version, capability_name, setup_id
        )
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ArtifactSchemaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CapabilityRecord(
        snapshot_version=manifest.snapshot_version,
        generated_at=manifest.generated_at,
        capability=capability,
    )


def _require_pack_exists(
    loader: FeaturePackLoader,
    customer_id: str,
    version: str,
    setup_id: str = DEFAULT_SETUP_ID,
) -> None:
    """404 if this customer has no pack at ``version`` in R2 under ``setup_id``.

    Archiving is a soft-delete of a REAL version, so we refuse to mark a phantom
    one. We probe the manifest (not the `latest` pointer) so any historical
    version — not just the current latest — can be archived. Customer + setup
    scope come for free: the loader keys every read on ``customer_id`` and the
    per-setup R2 prefix, so one tenant can never archive another's version, and a
    version that exists only under a different setup 404s here.
    """
    try:
        loader.load_manifest_at_version(customer_id, version, setup_id)
    except ArtifactNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail=f"no feature pack {version!r} for this customer",
        ) from exc


@archive_router.post("/{version}/archive", response_model=ArchiveState)
async def archive_feature_pack(
    version: str,
    setup_id: str = DEFAULT_SETUP_ID,
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
    archived_repo: ArchivedFeaturePackRepo = Depends(get_archived_feature_pack_repo),
) -> ArchiveState:
    """Archive (hide from the Library) one Feature Pack version (#214).

    ``?setup_id=`` selects which setup's pack to existence-check (#215/#245),
    defaulting to ``"default"`` so an unparameterized call is byte-identical to
    today. The existence probe reads through the per-setup R2 prefix.

    A SOFT-DELETE: the version is hidden from the Library's pack listing, but its
    R2 artifacts are untouched and it STAYS resolvable for any historical
    simulation that froze it — ``FeaturePackLoader`` never reads this marker, so a
    past run still replays. This is distinct from the forbidden hand-edit /
    hard-delete (both corrupt the control arm). Idempotent: re-archiving an
    already-archived version is a no-op.

    KNOWN LIMITATION (#215/#245, deferred to PR 3): the archive marker table is
    keyed ``(customer_id, pack_version)`` — NOT setup-aware (adding setup_id to
    its PK is a migration, out of this PR's scope). So if two setups of one org
    happen to share a version string, archiving one hides the other in the
    Library. This is a VISIBILITY edge case only — the loader never consults this
    marker, so pack RESOLUTION and the integrity invariant are unaffected. PR 3
    re-keys the marker by setup. (codex P2)
    """
    _validate_setup_id(setup_id)
    _require_pack_exists(loader, customer_id, version, setup_id)
    await archived_repo.archive(customer_id, version)
    return ArchiveState(customer_id=customer_id, pack_version=version, archived=True)


@archive_router.post("/{version}/unarchive", response_model=ArchiveState)
async def unarchive_feature_pack(
    version: str,
    setup_id: str = DEFAULT_SETUP_ID,
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
    archived_repo: ArchivedFeaturePackRepo = Depends(get_archived_feature_pack_repo),
) -> ArchiveState:
    """Unarchive (un-hide) a Feature Pack version (#214). Idempotent — unarchiving
    a version that was never archived returns ``archived=false`` without error.

    ``?setup_id=`` selects which setup's pack to existence-check, default
    ``"default"`` (byte-identical to today)."""
    _validate_setup_id(setup_id)
    _require_pack_exists(loader, customer_id, version, setup_id)
    await archived_repo.unarchive(customer_id, version)
    return ArchiveState(customer_id=customer_id, pack_version=version, archived=False)
