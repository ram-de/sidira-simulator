"""Sample-workspace route — seed an empty tenant with the Streamly sample packs.

Post-cutover, a brand-new org lands in an empty workspace (no Persona Pack, no
Feature Pack) and every screen shows an empty state. This route clones the
hand-built Streamly fixture (streaming vertical: 6 personas, 2 capabilities)
into the *caller's own* tenant prefix so they have something to simulate
against immediately. Triggered only by an explicit button click in the UI —
never automatically.

Tenancy invariants:
- The source customer is HARDCODED. A caller-supplied source id would let any
  tenant read any other tenant's packs by guessing its id.
- The clone refuses (409) if the target tenant already has a personas or
  featurepacks `latest` pointer — sample data never overwrites real data.
- All copies go through the ArtifactStore protocol, so the behavior is
  identical on LocalArtifactStore (dev) and R2 (prod). Prod R2 already
  carries the streamly_sample tree.

Failure / concurrency model (codex round 1):
- Content artifacts are written first, `latest` pointers last (personas
  pointer, then featurepacks pointer). A failure before any pointer lands
  leaves the tenant reading as empty; debris is invisible and a retry
  re-clones over it.
- The cloned persona manifest carries a `cloned_from` marker. If the run
  dies between the two pointer writes, the retry recognizes the personas
  pointer as an interrupted *sample* clone (marker present, featurepacks
  pointer absent) and proceeds — without the marker that state would 409
  forever. Real persona data never carries the marker, so it stays
  protected.
- The empty-workspace check runs again right before the pointer writes.
  The store protocol has no compare-and-swap, so a concurrent crawler /
  persona-build can still race us in the window between that re-check and
  the two writes; the re-check shrinks the window from "entire copy
  duration" to microseconds, which is as good as the protocol allows.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from sidira_simulator.adapters.base import ArtifactSchemaError, load_json_artifact
from sidira_simulator.adapters.r2 import ArtifactStore
from sidira_simulator.api.deps import current_customer_id, get_artifact_store
from sidira_simulator.schemas.feature_pack import FeaturePackManifest
from sidira_simulator.schemas.persona import PersonaPack

SAMPLE_SOURCE_CUSTOMER_ID = "streamly_sample"

router = APIRouter(prefix="/sample-workspace", tags=["sample-workspace"])


class SampleWorkspaceResponse(BaseModel):
    """What got seeded — enough for the UI to confirm and refresh."""

    source: str
    persona_pack_version: str
    persona_count: int
    feature_pack_version: str
    capabilities: list[str]


def _personas_latest_key(customer_id: str) -> str:
    return f"customers/{customer_id}/personas/latest"


def _featurepacks_latest_key(customer_id: str) -> str:
    return f"customers/{customer_id}/featurepacks/latest"


def _has_pointer(store: ArtifactStore, key: str) -> bool:
    try:
        store.read_text(key)
        return True
    except FileNotFoundError:
        return False


def _is_interrupted_sample_clone(store: ArtifactStore, customer_id: str) -> bool:
    """True iff the tenant's personas tree is a sample clone (marker present).

    Used to let a retry proceed after a clone died between the two pointer
    writes. Anything unreadable or unmarked is treated as real data.
    """
    try:
        version = store.read_text(_personas_latest_key(customer_id)).strip()
        manifest = json.loads(
            store.read_text(f"customers/{customer_id}/personas/{version}/manifest.json")
        )
    except (FileNotFoundError, ValueError):
        return False
    return isinstance(manifest, dict) and manifest.get("cloned_from") == SAMPLE_SOURCE_CUSTOMER_ID


def _refuse_unless_seedable(store: ArtifactStore, customer_id: str) -> None:
    personas_exists = _has_pointer(store, _personas_latest_key(customer_id))
    featurepacks_exists = _has_pointer(store, _featurepacks_latest_key(customer_id))
    if not personas_exists and not featurepacks_exists:
        return
    # Personas pointer from an interrupted sample clone (featurepacks pointer
    # never landed) is safe to overwrite on retry.
    if (
        personas_exists
        and not featurepacks_exists
        and _is_interrupted_sample_clone(store, customer_id)
    ):
        return
    raise HTTPException(
        status_code=409,
        detail=(
            "This workspace already has a persona or feature pack. "
            "The sample workspace only seeds empty workspaces."
        ),
    )


def _rewrite_persona_manifest(raw_json: str, target_customer_id: str) -> str:
    """Re-stamp customer_id and mark the manifest as a sample clone."""
    doc = json.loads(raw_json)
    if not isinstance(doc, dict):  # valid JSON but wrong shape, e.g. [] (codex R2-P2)
        raise ArtifactSchemaError(
            f"persona manifest must be a JSON object, got {type(doc).__name__}"
        )
    doc["customer_id"] = target_customer_id
    doc["cloned_from"] = SAMPLE_SOURCE_CUSTOMER_ID
    return json.dumps(doc, indent=2)


@router.post("", response_model=SampleWorkspaceResponse, status_code=201)
async def generate_sample_workspace(
    customer_id: str = Depends(current_customer_id),
    store: ArtifactStore = Depends(get_artifact_store),
) -> SampleWorkspaceResponse:
    """Clone the Streamly sample Persona Pack + Feature Pack into the caller's tenant."""
    _refuse_unless_seedable(store, customer_id)

    src = SAMPLE_SOURCE_CUSTOMER_ID
    try:
        persona_version = store.read_text(_personas_latest_key(src)).strip()
        feature_version = store.read_text(_featurepacks_latest_key(src)).strip()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Sample source {src!r} is not available in the artifact store.",
        ) from exc

    try:
        # ── Personas: persona_pack.json (schema-validated) + manifest.json ──
        src_personas = f"customers/{src}/personas/{persona_version}"
        dst_personas = f"customers/{customer_id}/personas/{persona_version}"

        pack = load_json_artifact(store, f"{src_personas}/persona_pack.json", PersonaPack)
        store.write_text(
            f"{dst_personas}/persona_pack.json",
            pack.model_copy(update={"customer_id": customer_id}).model_dump_json(indent=2),
        )
        store.write_text(
            f"{dst_personas}/manifest.json",
            _rewrite_persona_manifest(
                store.read_text(f"{src_personas}/manifest.json"), customer_id
            ),
        )

        # ── Feature pack: manifest + each capability's PRD and Figma files ──
        src_fp = f"customers/{src}/featurepacks/{feature_version}"
        dst_fp = f"customers/{customer_id}/featurepacks/{feature_version}"

        manifest = load_json_artifact(store, f"{src_fp}/manifest.json", FeaturePackManifest)
        for capability in manifest.capabilities:
            for filename in ("reverse-prd.md", "reverse-figma.json"):
                store.write_text(
                    f"{dst_fp}/capabilities/{capability}/{filename}",
                    store.read_text(f"{src_fp}/capabilities/{capability}/{filename}"),
                )
        store.write_text(
            f"{dst_fp}/manifest.json",
            manifest.model_copy(update={"customer_id": customer_id}).model_dump_json(indent=2),
        )
    except (FileNotFoundError, ArtifactSchemaError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Sample source {src!r} is incomplete in the artifact store: {exc}",
        ) from exc

    # Pointers last — the tenant only becomes non-empty once everything above
    # landed. Re-check first: a crawler or persona-build may have produced
    # real pointers while we were copying. Personas pointer is written before
    # the featurepacks pointer; _is_interrupted_sample_clone() relies on that
    # order to recover if we die between the two writes.
    _refuse_unless_seedable(store, customer_id)
    store.write_text(_personas_latest_key(customer_id), persona_version)
    store.write_text(_featurepacks_latest_key(customer_id), feature_version)

    return SampleWorkspaceResponse(
        source=src,
        persona_pack_version=persona_version,
        persona_count=len(pack.personas),
        feature_pack_version=feature_version,
        capabilities=list(manifest.capabilities),
    )
