"""Feature Pack loader — reads versioned packs from the artifact store.

Production layout (R2), DEFAULT setup (byte-identical to pre-#215 prod):
    customers/<customer_id>/featurepacks/<version>/manifest.json
    customers/<customer_id>/featurepacks/<version>/capabilities/<name>/reverse-prd.md
    customers/<customer_id>/featurepacks/<version>/capabilities/<name>/reverse-figma.json
    customers/<customer_id>/featurepacks/latest  ← pointer file, contents = version string

Named setups (#215/#245 — multiple crawl setups per org) get an extra
``setups/<setup_id>/`` segment so each setup's packs never collide:
    customers/<customer_id>/setups/<setup_id>/featurepacks/<version>/...

The DEFAULT setup deliberately keeps the legacy, segment-free prefix: the
Founders org's real pack lives only on an EC2 bind-mount at the legacy path,
so any change to the default path would orphan it. ``feature_pack_prefix``
is the SOLE place this branch is decided — every read/write routes through it.

The `latest` pointer is atomically updated by the crawler after a successful run.
The simulator reads via `load_latest()` for the common path; explicit
`load_at_version()` is available for reproducing a specific past simulation.
"""

from __future__ import annotations

import re

from sidira_simulator.adapters.base import (
    ArtifactNotFound,
    ArtifactSchemaError,
    load_json_artifact,
)
from sidira_simulator.adapters.r2 import ArtifactStore, get_featurepack_store
from sidira_simulator.adapters.repositories import DEFAULT_SETUP_ID
from sidira_simulator.schemas.feature_pack import (
    Capability,
    FeaturePackManifest,
    ReverseFigma,
)

# A setup_id becomes a literal R2 KEY SEGMENT. It MUST stay a single safe
# segment — no separators, no dots, no ``..`` — or a hostile value like
# ``../../other_customer`` could normalize OUT of this tenant's prefix on a
# path-backed store (LocalArtifactStore / the EC2 bind-mount) and read another
# tenant's pack. Mirrors schemas.crawl._SETUP_ID_RE (the mint-time rule); the
# helper re-enforces it at the R2 boundary so EVERY read/write is safe even if a
# raw setup_id reaches here from a query param. (codex P1)
_SAFE_SETUP_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,47}$")


class UnsafeSetupId(ValueError):
    """A setup_id that is not a single safe R2 key segment (path-traversal guard)."""


def feature_pack_prefix(customer_id: str, setup_id: str = DEFAULT_SETUP_ID) -> str:
    """R2 key prefix for one customer's Feature Packs under one crawl setup.

    THE SAFETY CRUX (#215/#245 PR 2). This is the ONE place that decides the
    pack prefix, so the default-setup path stays provably byte-identical to
    legacy prod at every read+write site.

    - ``setup_id == "default"`` → the EXACT legacy prefix, with NO ``setups/``
      segment: ``customers/<customer_id>/featurepacks``. Non-negotiable — the
      Founders org's real pack lives only on the EC2 bind-mount at this path,
      and historical simulations froze versions under it.
    - any other ``setup_id`` → a setup-scoped prefix:
      ``customers/<customer_id>/setups/<setup_id>/featurepacks``. The setup_id is
      validated as a single safe key segment first; anything else raises
      :class:`UnsafeSetupId` so a path-traversal value can never escape the
      tenant prefix.

    Returns the prefix WITHOUT a trailing slash; callers append ``/<version>/...``
    or ``/latest``.
    """
    if setup_id == DEFAULT_SETUP_ID:
        return f"customers/{customer_id}/featurepacks"
    if not _SAFE_SETUP_ID_RE.match(setup_id):
        raise UnsafeSetupId(f"unsafe setup_id for R2 key: {setup_id!r}")
    return f"customers/{customer_id}/setups/{setup_id}/featurepacks"


class FeaturePackLoader:
    """Reads versioned Feature Packs scoped by customer."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        # Feature Packs are crawler-published and live in R2 in prod; the read
        # store (get_featurepack_store) serves them live without dragging the
        # write paths onto R2. Persona packs are seed data and stay on get_store
        # — see PersonaPackLoader. (#208)
        self._store = store or get_featurepack_store()

    # ── Version resolution ──────────────────────────────────────────────

    def resolve_latest_version(
        self, customer_id: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> str:
        """Read the `latest` pointer file. Raises ArtifactNotFound if absent."""
        key = f"{feature_pack_prefix(customer_id, setup_id)}/latest"
        try:
            return self._store.read_text(key).strip()
        except FileNotFoundError as exc:
            raise ArtifactNotFound(
                f"No 'latest' pointer for customer {customer_id!r}. " "Has the crawler run yet?"
            ) from exc

    # ── Manifest reads ─────────────────────────────────────────────────

    def load_manifest_at_version(
        self, customer_id: str, version: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> FeaturePackManifest:
        key = f"{feature_pack_prefix(customer_id, setup_id)}/{version}/manifest.json"
        return load_json_artifact(self._store, key, FeaturePackManifest)

    def load_latest_manifest(
        self, customer_id: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> FeaturePackManifest:
        version = self.resolve_latest_version(customer_id, setup_id)
        return self.load_manifest_at_version(customer_id, version, setup_id)

    # ── Capability reads ───────────────────────────────────────────────

    def load_capability(
        self,
        customer_id: str,
        version: str,
        capability_name: str,
        setup_id: str = DEFAULT_SETUP_ID,
    ) -> Capability:
        """Load a single capability — reverse-PRD markdown + reverse-Figma JSON.

        The Capability schema requires both `surfaces` and `entry_points`. The
        crawler embeds these in capabilities/<name>/manifest.json; if absent we
        infer surfaces from the figma screens and leave entry_points empty (the
        Acme sample doesn't pre-write them; this is a known fixture quirk).
        """
        base = (
            f"{feature_pack_prefix(customer_id, setup_id)}"
            f"/{version}/capabilities/{capability_name}"
        )
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
            | {r for t in reverse_figma.transitions for r in (t.role_gated or [])}
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
        self, customer_id: str, capability_name: str, setup_id: str = DEFAULT_SETUP_ID
    ) -> Capability:
        version = self.resolve_latest_version(customer_id, setup_id)
        return self.load_capability(customer_id, version, capability_name, setup_id)
