"""Runtime config endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from pythia_simulator.main import app


def test_config_limits_uses_default_cap(monkeypatch) -> None:
    monkeypatch.delenv("PYTHIA_MAX_AGENTS", raising=False)

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "max_agents_per_simulation": 50,
        "max_agents_per_arm": 50,
    }


def test_config_limits_surfaces_env_cap(monkeypatch) -> None:
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "12")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json()["max_agents_per_simulation"] == 12
    assert resp.json()["max_agents_per_arm"] == 12


def test_config_limits_matches_post_simulation_bad_env_clamp(monkeypatch) -> None:
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "0")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "max_agents_per_simulation": 1,
        "max_agents_per_arm": 1,
    }


def test_config_limits_malformed_env_falls_back_to_default(monkeypatch) -> None:
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "not-an-int")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "max_agents_per_simulation": 50,
        "max_agents_per_arm": 50,
    }
