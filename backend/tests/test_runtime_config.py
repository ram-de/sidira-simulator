"""Runtime configuration compatibility for the Sidira rename."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request

from sidira_simulator.adapters.r2 import (
    LocalArtifactStore,
    R2ArtifactStore,
    get_featurepack_store,
    get_store,
)
from sidira_simulator.api.deps import current_customer_id
from sidira_simulator.main import _cors_origins
from sidira_simulator.services.runtime_config import (
    resolve_elicitation_samples,
    resolve_elicitation_temperature,
    resolve_sidira_env,
)


def _request_without_session() -> Request:
    """A bare request whose state carries no Clerk-resolved customer_id."""
    return Request({"type": "http", "headers": []})


def _clear_product_env(monkeypatch, suffix: str) -> None:
    monkeypatch.delenv(f"SIDIRA_{suffix}", raising=False)
    monkeypatch.delenv(f"PYTHIA_{suffix}", raising=False)


def test_resolve_sidira_env_reads_primary_name(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "CUSTOMER_ID")
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "streamly_sample")

    assert resolve_sidira_env("CUSTOMER_ID", "demo") == "streamly_sample"


def test_resolve_sidira_env_falls_back_to_legacy_pythia_name(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "CUSTOMER_ID")
    monkeypatch.setenv("PYTHIA_CUSTOMER_ID", "legacy_demo")

    assert resolve_sidira_env("CUSTOMER_ID", "demo") == "legacy_demo"


def test_resolve_sidira_env_primary_name_takes_precedence(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "CUSTOMER_ID")
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "sidira_demo")
    monkeypatch.setenv("PYTHIA_CUSTOMER_ID", "legacy_demo")

    assert resolve_sidira_env("CUSTOMER_ID", "demo") == "sidira_demo"


def test_resolve_sidira_env_blank_primary_falls_back_to_legacy(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "LOCAL_CRED_KEY")
    monkeypatch.setenv("SIDIRA_LOCAL_CRED_KEY", "")
    monkeypatch.setenv("PYTHIA_LOCAL_CRED_KEY", "legacy-key")

    assert resolve_sidira_env("LOCAL_CRED_KEY") == "legacy-key"


def test_resolve_sidira_env_blank_values_use_default(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "CUSTOMER_ID")
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", " ")
    monkeypatch.setenv("PYTHIA_CUSTOMER_ID", "")

    assert resolve_sidira_env("CUSTOMER_ID", "demo") == "demo"


def test_current_customer_id_uses_sidira_namespace(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "CUSTOMER_ID")
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "streamly_sample")

    assert current_customer_id(_request_without_session()) == "streamly_sample"


def test_cors_origins_fall_back_to_pythia_namespace(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "CORS_ORIGINS")
    monkeypatch.setenv("PYTHIA_CORS_ORIGINS", "http://legacy.local, http://127.0.0.1:3333")

    assert _cors_origins() == ["http://legacy.local", "http://127.0.0.1:3333"]


def test_local_artifact_store_prefers_sidira_namespace(
    monkeypatch,
    tmp_path: Path,
) -> None:
    sidira_root = tmp_path / "sidira-artifacts"
    legacy_root = tmp_path / "pythia-artifacts"
    monkeypatch.delenv("R2_BUCKET", raising=False)
    _clear_product_env(monkeypatch, "LOCAL_ARTIFACTS")
    monkeypatch.setenv("SIDIRA_LOCAL_ARTIFACTS", str(sidira_root))
    monkeypatch.setenv("PYTHIA_LOCAL_ARTIFACTS", str(legacy_root))

    store = get_store()

    assert isinstance(store, LocalArtifactStore)
    assert store.root == sidira_root


def _clear_r2_pack_env(monkeypatch) -> None:
    for suffix in ("BUCKET", "ENDPOINT_URL", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY"):
        monkeypatch.delenv(f"R2_PACK_{suffix}", raising=False)
        monkeypatch.delenv(f"R2_{suffix}", raising=False)


def test_featurepack_store_falls_back_to_local_when_unconfigured(
    monkeypatch,
    tmp_path: Path,
) -> None:
    # No R2_PACK_BUCKET (dev + tests): packs are read from the same local store
    # as everything else (#208).
    _clear_r2_pack_env(monkeypatch)
    _clear_product_env(monkeypatch, "LOCAL_ARTIFACTS")
    monkeypatch.setenv("SIDIRA_LOCAL_ARTIFACTS", str(tmp_path / "art"))

    assert isinstance(get_featurepack_store(), LocalArtifactStore)


def test_featurepack_store_uses_r2_without_flipping_write_store(monkeypatch) -> None:
    # R2_PACK_* set but R2_BUCKET unset: the pack reader goes to R2 while
    # get_store() (the write path) stays local — the whole point of the split.
    _clear_r2_pack_env(monkeypatch)
    _clear_product_env(monkeypatch, "LOCAL_ARTIFACTS")
    monkeypatch.setenv("R2_PACK_BUCKET", "sidira-crawler")
    monkeypatch.setenv("R2_PACK_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("R2_PACK_ACCESS_KEY_ID", "ak")
    monkeypatch.setenv("R2_PACK_SECRET_ACCESS_KEY", "sk")

    assert isinstance(get_featurepack_store(), R2ArtifactStore)
    assert isinstance(get_store(), LocalArtifactStore)


# ── #221 distribution-elicitation flags ──────────────────────────────────────


def test_elicitation_samples_defaults_to_one(monkeypatch) -> None:
    # Default reproduces the historical single-reaction path.
    _clear_product_env(monkeypatch, "ELICITATION_SAMPLES")
    assert resolve_elicitation_samples() == 1


def test_elicitation_samples_reads_env_and_clamps_below_one(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "ELICITATION_SAMPLES")
    monkeypatch.setenv("SIDIRA_ELICITATION_SAMPLES", "5")
    assert resolve_elicitation_samples() == 5

    monkeypatch.setenv("SIDIRA_ELICITATION_SAMPLES", "0")
    assert resolve_elicitation_samples() == 1  # never zero — an agent needs a reaction


def test_elicitation_samples_malformed_fails_open_to_default(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "ELICITATION_SAMPLES")
    monkeypatch.setenv("SIDIRA_ELICITATION_SAMPLES", "not-an-int")
    assert resolve_elicitation_samples() == 1


def test_elicitation_temperature_defaults_to_zero(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "ELICITATION_TEMPERATURE")
    assert resolve_elicitation_temperature() == 0.0


def test_elicitation_temperature_reads_env_and_clamps_negative(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "ELICITATION_TEMPERATURE")
    monkeypatch.setenv("SIDIRA_ELICITATION_TEMPERATURE", "1.1")
    assert resolve_elicitation_temperature() == 1.1

    monkeypatch.setenv("SIDIRA_ELICITATION_TEMPERATURE", "-0.5")
    assert resolve_elicitation_temperature() == 0.0


def test_elicitation_temperature_malformed_fails_open_to_default(monkeypatch) -> None:
    _clear_product_env(monkeypatch, "ELICITATION_TEMPERATURE")
    monkeypatch.setenv("SIDIRA_ELICITATION_TEMPERATURE", "warm")
    assert resolve_elicitation_temperature() == 0.0
