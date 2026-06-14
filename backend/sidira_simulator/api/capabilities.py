"""Capabilities route — lists capabilities from the customer's latest Feature Pack."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sidira_simulator.adapters.base import ArtifactNotFound, ArtifactSchemaError
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.api.deps import current_customer_id, get_feature_pack_loader
from sidira_simulator.schemas.feature_pack import CapabilityRecord, FeaturePackManifest

router = APIRouter(prefix="/capabilities", tags=["capabilities"])


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
