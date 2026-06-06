"""Clerk auth gate — #29.

The gate is env-gated: with no Clerk secret it is a pass-through (preserving the
no-auth test/dev path); with a secret it 401s unauthenticated requests and
populates ``request.state`` for the customer resolver.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, Request
from fastapi.testclient import TestClient

from sidira_simulator.api import auth
from sidira_simulator.api.deps import current_customer_id
from sidira_simulator.main import create_app

DUMMY_SECRET = "sk_test_dummy"


def _clear_env(monkeypatch) -> None:
    for prefix in ("SIDIRA_", "PYTHIA_"):
        monkeypatch.delenv(f"{prefix}CLERK_SECRET_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}CUSTOMER_ID", raising=False)


def _client_with_probe() -> TestClient:
    """Real app + a probe route that echoes the resolved customer id."""
    app = create_app()

    @app.get("/_probe/customer")
    def _probe(customer_id: str = Depends(current_customer_id)) -> dict[str, str]:
        return {"customer_id": customer_id}

    return TestClient(app)


def test_passthrough_when_clerk_unconfigured(monkeypatch) -> None:
    _clear_env(monkeypatch)  # no secret -> gate disabled

    resp = _client_with_probe().get("/_probe/customer")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"customer_id": "demo"}  # env default, gate not consulted


def test_unauthenticated_request_is_rejected(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(auth, "authenticate", lambda request: None)

    resp = _client_with_probe().get("/_probe/customer")

    assert resp.status_code == 401, resp.text
    assert resp.json() == {"detail": "Unauthorized"}


def test_health_is_exempt_even_when_configured(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(auth, "authenticate", lambda request: None)

    resp = _client_with_probe().get("/health")

    assert resp.status_code == 200, resp.text


def test_options_is_exempt_even_when_configured(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(auth, "authenticate", lambda request: None)

    resp = _client_with_probe().options("/_probe/customer")

    assert resp.status_code != 401, resp.text


def test_authenticated_request_sets_customer_from_session(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    # Even with a conflicting env default, the session value must win.
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "env_default")
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(user_id="user_123", customer_id="acme"),
    )

    resp = _client_with_probe().get("/_probe/customer")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"customer_id": "acme"}


def test_authenticated_without_tenant_is_rejected(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    # An env default exists; the gate must NOT let a tenantless session fall
    # through to it (that would silently grant the "demo"/env tenant).
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "env_default")
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(user_id="user_123", customer_id=None),
    )

    resp = _client_with_probe().get("/_probe/customer")

    assert resp.status_code == 403, resp.text
    assert resp.json() == {"detail": "No tenant for user"}


def test_current_customer_id_prefers_session_over_env(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "env_default")

    request = Request({"type": "http", "headers": []})
    request.state.customer_id = "from_session"

    assert current_customer_id(request) == "from_session"


@pytest.mark.parametrize("claim", ["customer_id", "org_id"])
def test_extract_customer_id_reads_claim_chain(claim: str) -> None:
    assert auth._extract_customer_id({claim: "acme"}) == "acme"


def test_extract_customer_id_reads_nested_metadata() -> None:
    assert auth._extract_customer_id({"metadata": {"customer_id": "acme"}}) == "acme"


def test_extract_customer_id_returns_none_when_absent() -> None:
    assert auth._extract_customer_id({"sub": "user_123"}) is None
