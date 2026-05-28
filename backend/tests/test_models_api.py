"""Model catalog API tests for #103 model selection."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("PYTHIA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from pythia_simulator.main import app  # noqa: E402


def test_get_models_returns_only_keyed_models_and_marks_default(monkeypatch) -> None:
    monkeypatch.setenv("GROQ_API_KEY", "test-groq")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resp = TestClient(app).get("/models")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    ids = {m["id"] for m in body["models"]}
    assert "llama-3.3-70b-versatile" in ids
    assert "claude-opus-4-7" in ids
    assert "gpt-5.5" not in ids
    assert body["default_model_id"] == "llama-3.3-70b-versatile"
    assert [m["id"] for m in body["models"] if m["is_default"]] == ["llama-3.3-70b-versatile"]


def test_get_models_falls_back_to_first_available_default(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    resp = TestClient(app).get("/models")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["default_model_id"] == "claude-sonnet-4-6"
    assert [m["id"] for m in body["models"] if m["is_default"]] == ["claude-sonnet-4-6"]
