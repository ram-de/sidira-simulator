"""Capabilities route — lists capabilities from the customer's latest Feature Pack."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sidira_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.api.deps import current_customer_id, get_feature_pack_loader
from sidira_simulator.schemas.feature_pack import (
    CapabilityRecord,
    CapabilitySummary,
    FeaturePackManifest,
    FeaturePackSummary,
)

router = APIRouter(prefix="/capabilities", tags=["capabilities"])

# The pack-summary projection lives under its OWN prefix, NOT as /capabilities/summary.
# A sibling static segment under /capabilities would collide with the dynamic
# /capabilities/{capability_name} detail route for any capability literally named
# `summary` — and that name can arrive in a manifest we don't validate (the crawler
# is a separate repo; manifests are read straight from R2). A dedicated prefix makes
# the collision structurally impossible regardless of manifest provenance, so no
# slug needs reserving. (#207)
summary_router = APIRouter(prefix="/feature-pack", tags=["capabilities"])


@router.get("", response_model=FeaturePackManifest)
async def list_capabilities(
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
) -> FeaturePackManifest:
    """Return the latest Feature Pack manifest for the authenticated customer."""
    try:
        return loader.load_latest_manifest(customer_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@summary_router.get("/summary", response_model=FeaturePackSummary)
async def list_capabilities_summary(
    customer_id: str = Depends(current_customer_id),
    loader: FeaturePackLoader = Depends(get_feature_pack_loader),
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
    try:
        manifest = loader.load_latest_manifest(customer_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    summaries: list[CapabilitySummary] = []
    for name in manifest.capabilities:
        # `domain` rides along from the manifest's grouping index (#244 / crawler
        # #18) — no extra read, and it survives even when the body is missing.
        domain = manifest.capability_domains.get(name)
        try:
            capability = loader.load_capability(customer_id, manifest.snapshot_version, name)
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
    try:
        manifest = loader.load_latest_manifest(customer_id)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if capability_name not in manifest.capabilities:
        raise HTTPException(
            status_code=404,
            detail=f"capability {capability_name!r} is not in the latest pack",
        )
    try:
        capability = loader.load_capability(customer_id, manifest.snapshot_version, capability_name)
    except ArtifactNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ArtifactSchemaError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return CapabilityRecord(
        snapshot_version=manifest.snapshot_version,
        generated_at=manifest.generated_at,
        capability=capability,
    )
