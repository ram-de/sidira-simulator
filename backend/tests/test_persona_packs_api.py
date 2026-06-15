"""GET /persona-packs/{pack_id} endpoint tests.

The Library's persona-pack detail page (#207) reads this to render each
persona's description / JTBD / weight — the fields the wizard-shaped
`GET /personas` projection deliberately omits. `pack_id="latest"` resolves the
active pack (with the #212 starter fallback for empty tenants); an explicit
version loads that snapshot and 404s when it is genuinely missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.api.deps import current_customer_id, get_persona_loader
from sidira_simulator.main import app

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"


@pytest.fixture(autouse=True)
def _customer() -> None:
    app.dependency_overrides[current_customer_id] = lambda: "demo"
    yield
    app.dependency_overrides.clear()


def test_get_latest_returns_full_pack_with_descriptions() -> None:
    """`latest` resolves the real active pack with the detail fields the page needs."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is False
    assert body["version"] == "v_1"
    assert len(body["personas"]) == 6
    # The whole point of this endpoint over /personas: full persona bodies.
    assert all(p["description"].strip() for p in body["personas"])
    # Weights + stability surface so the detail page can show "% of population".
    assert "head_count" in body["weights"]
    assert isinstance(body["stability_score"], (int, float))


def test_get_explicit_version_matches_latest() -> None:
    """Addressing the version directly returns the same snapshot as `latest`."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    client = TestClient(app)
    explicit = client.get("/persona-packs/v_1")
    assert explicit.status_code == 200, explicit.text
    assert explicit.json() == client.get("/persona-packs/latest").json()


def test_empty_tenant_latest_returns_starter(tmp_path: Path) -> None:
    """No pack in the store → `latest` serves the #212 starter, not a 404."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(tmp_path)
    )
    resp = TestClient(app).get("/persona-packs/latest")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is True
    assert body["version"] == "starter-v1"
    assert len(body["personas"]) >= 1


def test_unknown_version_404s() -> None:
    """An explicit version that does not exist is a real not-found, not a starter."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/persona-packs/v_999")
    assert resp.status_code == 404, resp.text
