"""Persona Pack loader — reads versioned packs from the artifact store.

Production layout (R2), parallel to feature_pack_loader:
    customers/<customer_id>/personas/<version>/manifest.json
    customers/<customer_id>/personas/<version>/persona_pack.json
    customers/<customer_id>/personas/<version>/prompts/<persona_name>.md
    customers/<customer_id>/personas/latest  ← pointer file, contents = version string
"""

from __future__ import annotations

from pythia_simulator.adapters.base import ArtifactNotFound, load_json_artifact
from pythia_simulator.adapters.r2 import ArtifactStore, get_store
from pythia_simulator.schemas.persona import PersonaPack


class PersonaPackLoader:
    """Reads versioned Persona Packs scoped by customer."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        self._store = store or get_store()

    def resolve_latest_version(self, customer_id: str) -> str:
        key = f"customers/{customer_id}/personas/latest"
        try:
            return self._store.read_text(key).strip()
        except FileNotFoundError as exc:
            raise ArtifactNotFound(
                f"No 'latest' personas pointer for customer {customer_id!r}."
            ) from exc

    def load_at_version(self, customer_id: str, version: str) -> PersonaPack:
        key = f"customers/{customer_id}/personas/{version}/persona_pack.json"
        return load_json_artifact(self._store, key, PersonaPack)

    def load_latest(self, customer_id: str) -> PersonaPack:
        version = self.resolve_latest_version(customer_id)
        return self.load_at_version(customer_id, version)
