"""Runtime configuration compatibility for the Sidira rename."""

from __future__ import annotations

from pathlib import Path

from fastapi import Request

from sidira_simulator.adapters.r2 import LocalArtifactStore, get_store
from sidira_simulator.api.deps import current_customer_id
from sidira_simulator.main import _cors_origins
from sidira_simulator.services.runtime_config import resolve_sidira_env


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
