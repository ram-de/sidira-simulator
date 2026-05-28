"""Capabilities route — lists capabilities from the customer's latest Feature Pack."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from sidira_simulator.adapters.base import ArtifactNotFound
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.api.deps import current_customer_id, get_feature_pack_loader
from sidira_simulator.schemas.feature_pack import FeaturePackManifest

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
