"""GET /personas endpoint tests.

The wizard's #101 persona-filter list reads this. Post-#212 it never 404s:
an empty tenant gets the generic starter pack flagged `is_starter`.
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


def test_empty_tenant_gets_starter_pack(tmp_path: Path) -> None:
    """No pack in the store → 200 with the starter, not a 404."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(tmp_path)
    )
    resp = TestClient(app).get("/personas")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is True
    assert body["pack_version"] == "starter-v1"
    assert len(body["personas"]) >= 1
    # Weights surface so the wizard's "% of population" subtext renders.
    assert all("weight" in p for p in body["personas"])


def test_stale_pointer_still_404s(tmp_path: Path) -> None:
    """A `latest` pointer to a missing artifact is corrupt state → 404.

    The empty-tenant starter (#212) is only for tenants with *no* pointer.
    A pointer that dangles is a partial/corrupt write, not an empty tenant,
    so we surface a 404 rather than masking it behind a starter pack.
    """
    store = LocalArtifactStore(tmp_path)
    store.write_text("customers/demo/personas/latest", "v_99")
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(store)
    resp = TestClient(app).get("/personas")
    assert resp.status_code == 404, resp.text


def test_real_pack_reports_not_starter() -> None:
    """A tenant with a real pack reports is_starter=False."""
    app.dependency_overrides[get_persona_loader] = lambda: PersonaPackLoader(
        LocalArtifactStore(_FIXTURE_ROOT)
    )
    resp = TestClient(app).get("/personas")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["is_starter"] is False
    assert body["pack_version"] == "v_1"
    assert len(body["personas"]) == 6
