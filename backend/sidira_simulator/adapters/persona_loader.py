"""Persona Pack loader — reads versioned packs from the artifact store.

Production layout (R2), parallel to feature_pack_loader:
    customers/<customer_id>/personas/<version>/manifest.json
    customers/<customer_id>/personas/<version>/persona_pack.json
    customers/<customer_id>/personas/<version>/prompts/<persona_name>.md
    customers/<customer_id>/personas/latest  ← pointer file, contents = version string
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from sidira_simulator.adapters.base import ArtifactNotFound, load_json_artifact
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.schemas.persona import PersonaPack

# Generic, product-agnostic placeholder pack served to tenants that have no
# Persona Pack yet (#212). It ships with the application image (not the artifact
# store) because it is application data, not a customer artifact.
_STARTER_TEMPLATE_PATH = Path(__file__).with_name("starter_persona_pack.json")


@lru_cache(maxsize=1)
def _starter_template() -> PersonaPack:
    """Parse + validate the bundled starter pack once, then cache it."""
    return PersonaPack.model_validate_json(_STARTER_TEMPLATE_PATH.read_text())


class PersonaPackLoader:
    """Reads versioned Persona Packs scoped by customer."""

    def __init__(self, store: ArtifactStore | None = None) -> None:
        self._store = store or get_store()

    @staticmethod
    def _latest_pointer_key(customer_id: str) -> str:
        """The single source of truth for the `latest` pointer key.

        Both the read path (:meth:`resolve_latest_version`) and the write path
        (:meth:`promote`) go through here so the pointer can never drift.
        """
        return f"customers/{customer_id}/personas/latest"

    def resolve_latest_version(self, customer_id: str) -> str:
        try:
            return self._store.read_text(self._latest_pointer_key(customer_id)).strip()
        except FileNotFoundError as exc:
            raise ArtifactNotFound(
                f"No 'latest' personas pointer for customer {customer_id!r}."
            ) from exc

    def promote(self, customer_id: str, version: str) -> None:
        """Point the customer's `latest` pointer at `version`.

        A single pointer write — the contents are the version string — so a
        subsequent :meth:`load_latest` resolves to the promoted snapshot. Uses
        the same key as :meth:`resolve_latest_version` via
        :meth:`_latest_pointer_key`.
        """
        self._store.write_text(self._latest_pointer_key(customer_id), version)

    def load_at_version(self, customer_id: str, version: str) -> PersonaPack:
        key = f"customers/{customer_id}/personas/{version}/persona_pack.json"
        return load_json_artifact(self._store, key, PersonaPack)

    def starter_pack(self, customer_id: str) -> PersonaPack:
        """The generic starter pack, stamped with the caller's customer_id.

        Re-stamping (rather than mutating the cached template) keeps the
        cached parse pristine and gives the tenant a pack that round-trips
        through the rest of the pipeline as its own.
        """
        return _starter_template().model_copy(
            update={"customer_id": customer_id, "is_starter": True}
        )

    def load_latest(self, customer_id: str) -> PersonaPack:
        """Load the active pack, or serve the starter when none exists yet.

        A tenant with no `latest` pointer (a brand-new org, or one whose
        Feature Pack landed before any Persona Pack was built) gets the
        generic starter pack instead of a 404, so `/personas`, the wizard's
        persona filter, and simulations all work immediately (#212). The
        starter is served in-memory only — nothing is written, so the
        sample-workspace clone still sees an empty tenant and can seed it.
        """
        try:
            version = self.resolve_latest_version(customer_id)
        except ArtifactNotFound:
            return self.starter_pack(customer_id)
        return self.load_at_version(customer_id, version)
