"""Feature Pack loader — reads versioned packs from the artifact store.

Production layout (R2):
    customers/<customer_id>/featurepacks/<version>/manifest.json
    customers/<customer_id>/featurepacks/<version>/capabilities/<name>/reverse-prd.md
    customers/<customer_id>/featurepacks/<version>/capabilities/<name>/reverse-figma.json
    customers/<customer_id>/featurepacks/latest  ← pointer file, contents = version string

The `latest` pointer is atomically updated by the crawler after a successful run.
The simulator reads via `load_latest()` for the common path; explicit
`load_at_version()` is available for reproducing a specific past simulation.
"""

from __future__ import annotations

from pythia_simulator.adapters.base import (
    ArtifactNotFound,
    ArtifactSchemaError,
    load_json_artifact,
)
from pythia_simulator.adapters.r2 import ArtifactStore, get_store
from pythia_simulator.schemas.feature_pack import (
    Capability,
    FeaturePackManifest,
    ReverseFigma,
)


class FeaturePackLoader:
    """Reads versioned Feature Packs scoped by customer."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        self._store = store or get_store()

    # ── Version resolution ──────────────────────────────────────────────

    def resolve_latest_version(self, customer_id: str) -> str:
        """Read the `latest` pointer file. Raises ArtifactNotFound if absent."""
        key = f"customers/{customer_id}/featurepacks/latest"
        try:
            return self._store.read_text(key).strip()
        except FileNotFoundError as exc:
            raise ArtifactNotFound(
                f"No 'latest' pointer for customer {customer_id!r}. "
                "Has the crawler run yet?"
            ) from exc

    # ── Manifest reads ─────────────────────────────────────────────────

    def load_manifest_at_version(
        self, customer_id: str, version: str
    ) -> FeaturePackManifest:
        key = f"customers/{customer_id}/featurepacks/{version}/manifest.json"
        return load_json_artifact(self._store, key, FeaturePackManifest)

    def load_latest_manifest(self, customer_id: str) -> FeaturePackManifest:
        version = self.resolve_latest_version(customer_id)
        return self.load_manifest_at_version(customer_id, version)

    # ── Capability reads ───────────────────────────────────────────────

    def load_capability(
        self, customer_id: str, version: str, capability_name: str
    ) -> Capability:
        """Load a single capability — reverse-PRD markdown + reverse-Figma JSON.

        The Capability schema requires both `surfaces` and `entry_points`. The
        crawler embeds these in capabilities/<name>/manifest.json; if absent we
        infer surfaces from the figma screens and leave entry_points empty (the
        Acme sample doesn't pre-write them; this is a known fixture quirk).
        """
        base = f"customers/{customer_id}/featurepacks/{version}/capabilities/{capability_name}"
        prd_key = f"{base}/reverse-prd.md"
        figma_key = f"{base}/reverse-figma.json"

        try:
            reverse_prd = self._store.read_text(prd_key)
        except FileNotFoundError as exc:
            raise ArtifactNotFound(f"Missing reverse-PRD: {prd_key}") from exc

        reverse_figma = load_json_artifact(self._store, figma_key, ReverseFigma)

        surfaces = sorted({s.id for s in reverse_figma.screens})
        roles = sorted(
            {s.role for s in reverse_figma.screens if s.role is not None}
            | {
                r
                for t in reverse_figma.transitions
                for r in (t.role_gated or [])
            }
        )

        try:
            return Capability(
                name=capability_name,
                surfaces=surfaces,
                roles=roles,
                entry_points=[],  # Phase 4.5 fixture limitation; crawler will populate
                reverse_prd=reverse_prd,
                reverse_figma=reverse_figma,
            )
        except Exception as exc:
            raise ArtifactSchemaError(
                f"Capability {capability_name!r} at {version!r} failed validation: {exc}"
            ) from exc

    def load_latest_capability(
        self, customer_id: str, capability_name: str
    ) -> Capability:
        version = self.resolve_latest_version(customer_id)
        return self.load_capability(customer_id, version, capability_name)
