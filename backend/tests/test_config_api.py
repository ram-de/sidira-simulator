"""Runtime config endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from sidira_simulator.main import app


def _clear_max_agents_env(monkeypatch) -> None:
    monkeypatch.delenv("SIDIRA_MAX_AGENTS", raising=False)
    monkeypatch.delenv("PYTHIA_MAX_AGENTS", raising=False)


def test_config_limits_uses_default_cap(monkeypatch) -> None:
    _clear_max_agents_env(monkeypatch)

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "max_agents_per_simulation": 100,
        "max_agents_per_arm": 100,
    }


def test_config_limits_surfaces_sidira_env_cap(monkeypatch) -> None:
    _clear_max_agents_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "12")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json()["max_agents_per_simulation"] == 12
    assert resp.json()["max_agents_per_arm"] == 12


def test_config_limits_falls_back_to_pythia_env_cap(monkeypatch) -> None:
    _clear_max_agents_env(monkeypatch)
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "9")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json()["max_agents_per_simulation"] == 9
    assert resp.json()["max_agents_per_arm"] == 9


def test_config_limits_sidira_env_cap_takes_precedence(monkeypatch) -> None:
    _clear_max_agents_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "14")
    monkeypatch.setenv("PYTHIA_MAX_AGENTS", "9")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json()["max_agents_per_simulation"] == 14
    assert resp.json()["max_agents_per_arm"] == 14


def test_config_limits_matches_post_simulation_bad_env_clamp(monkeypatch) -> None:
    _clear_max_agents_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "0")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "max_agents_per_simulation": 1,
        "max_agents_per_arm": 1,
    }


def test_config_limits_malformed_env_falls_back_to_default(monkeypatch) -> None:
    _clear_max_agents_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "not-an-int")

    resp = TestClient(app).get("/config/limits")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {
        "max_agents_per_simulation": 100,
        "max_agents_per_arm": 100,
    }
