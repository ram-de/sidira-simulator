"""Adapter helpers — used by persona_loader and feature_pack_loader.

DRY for JSON-from-artifact-store reads with Pydantic validation. Both loaders
follow the same shape: read a key, parse JSON, validate against a Pydantic
schema. Putting the helper here keeps the loaders thin.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel

from sidira_simulator.adapters.r2 import ArtifactStore

T = TypeVar("T", bound=BaseModel)


class ArtifactNotFound(FileNotFoundError):
    """Raised when an expected artifact key isn't present in the store."""


class ArtifactSchemaError(ValueError):
    """Raised when an artifact exists but doesn't validate against its schema."""


def load_json_artifact(store: ArtifactStore, key: str, schema: type[T]) -> T:
    """Read a JSON artifact and validate it against the given Pydantic schema."""
    try:
        raw = store.read_text(key)
    except FileNotFoundError as exc:
        raise ArtifactNotFound(f"Missing artifact: {key}") from exc

    try:
        return schema.model_validate_json(raw)
    except Exception as exc:
        raise ArtifactSchemaError(
            f"Artifact {key} failed {schema.__name__} validation: {exc}"
        ) from exc
