"""Admin-console RBAC foundation — #45.

The backend had NO role enforcement: ``auth.py`` extracted the tenant but
ignored the Clerk org role, so every authenticated org member could save
credentials / edit crawl configs / delete connectors. This ticket adds the role
primitives (``_extract_org_role`` / ``is_admin_role`` / ``current_org_role`` /
``require_admin``) and gates the CONFIGURATION / credential-bearing routes while
leaving EXECUTION routes open to members (configuration = admin; execution =
member).

These tests cover, in three layers:
  1. role extraction + admin/member classification (pure units),
  2. ``current_org_role`` / ``require_admin`` fallback discipline (keyless dev/
     test path → admin; Clerk configured → session role is authoritative),
  3. each admin-gated route: a member session → 403, an admin session → NOT 403,
     and the keyless path (the rest of the suite) still reaches the route.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Saving feature-store / crawl creds at rest needs the local-key fallback set
# before the app imports (mirrors the other route-test modules).
os.environ.setdefault("SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE=")

from sidira_simulator.api import auth  # noqa: E402
from sidira_simulator.api.deps import current_org_role, require_admin  # noqa: E402
from sidira_simulator.main import app, create_app  # noqa: E402

DUMMY_SECRET = "sk_test_dummy"


# ──────────────────────────────────────────────────────────────────────
# Layer 1 — role extraction + classification (pure units)
# ──────────────────────────────────────────────────────────────────────


def test_extract_org_role_reads_v2_o_rol_claim() -> None:
    # Clerk v2 session tokens nest the active org role under `o.rol` — the claim
    # auth.py ignored until #45.
    assert auth._extract_org_role({"o": {"id": "org_abc", "rol": "admin"}}) == "admin"


def test_extract_org_role_lowercases() -> None:
    assert auth._extract_org_role({"o": {"id": "org_abc", "rol": "Admin"}}) == "admin"


def test_extract_org_role_reads_basic_member() -> None:
    assert auth._extract_org_role({"o": {"id": "org_abc", "rol": "basic_member"}}) == "basic_member"


def test_extract_org_role_reads_top_level_org_role_claim() -> None:
    # Forward-compat / non-v2 templates that emit a flat org_role claim.
    assert auth._extract_org_role({"org_role": "admin"}) == "admin"


def test_extract_org_role_returns_none_when_absent() -> None:
    assert auth._extract_org_role({"sub": "user_1", "o": {"id": "org_abc"}}) is None
    assert auth._extract_org_role({"sub": "user_1"}) is None


@pytest.mark.parametrize("role", ["admin", "owner", "org:admin", "org:owner", "Admin"])
def test_is_admin_role_admin_tier(role: str) -> None:
    assert auth.is_admin_role(role) is True


@pytest.mark.parametrize("role", ["basic_member", "member", "guest", "", None])
def test_is_admin_role_non_admin(role) -> None:
    assert auth.is_admin_role(role) is False


def test_authenticate_surfaces_org_role(monkeypatch) -> None:
    # The full claim → AuthState path carries the role through.
    class _RS:
        is_signed_in = True
        payload = {"sub": "user_1", "o": {"id": "org_abc", "rol": "basic_member"}}

    monkeypatch.setattr(
        auth,
        "_get_client",
        lambda: type("C", (), {"authenticate_request": staticmethod(lambda req, opts: _RS())})(),
    )
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    state = auth.authenticate(Request({"type": "http", "headers": []}))
    assert state is not None
    assert state.org_role == "basic_member"
    assert state.customer_id == "org_abc"


# ──────────────────────────────────────────────────────────────────────
# Layer 2 — current_org_role / require_admin fallback discipline
# ──────────────────────────────────────────────────────────────────────


def _clear_clerk(monkeypatch) -> None:
    for prefix in ("SIDIRA_", "PYTHIA_"):
        monkeypatch.delenv(f"{prefix}CLERK_SECRET_KEY", raising=False)
        monkeypatch.delenv(f"{prefix}ORG_ROLE", raising=False)


def _bare_request() -> Request:
    return Request({"type": "http", "headers": []})


def test_current_org_role_keyless_defaults_to_admin(monkeypatch) -> None:
    _clear_clerk(monkeypatch)  # Clerk unconfigured → dev/test fallback
    assert current_org_role(_bare_request()) == "admin"


def test_current_org_role_keyless_env_override(monkeypatch) -> None:
    _clear_clerk(monkeypatch)
    monkeypatch.setenv("SIDIRA_ORG_ROLE", "basic_member")
    assert current_org_role(_bare_request()) == "basic_member"


def test_current_org_role_clerk_configured_uses_session(monkeypatch) -> None:
    _clear_clerk(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    # Even with an env default present, a Clerk-configured request must NOT fall
    # back to it — the session role is authoritative.
    monkeypatch.setenv("SIDIRA_ORG_ROLE", "admin")
    req = _bare_request()
    req.state.org_role = "basic_member"
    assert current_org_role(req) == "basic_member"


def test_current_org_role_clerk_configured_roleless_is_none(monkeypatch) -> None:
    _clear_clerk(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setenv("SIDIRA_ORG_ROLE", "admin")  # must be ignored
    # No org_role on request.state (roleless session) → None, NOT the env admin.
    assert current_org_role(_bare_request()) is None


def test_require_admin_keyless_allows(monkeypatch) -> None:
    _clear_clerk(monkeypatch)
    # Keyless path → admin fallback → no raise.
    require_admin(_bare_request())


def test_require_admin_denies_member(monkeypatch) -> None:
    _clear_clerk(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    req = _bare_request()
    req.state.org_role = "basic_member"
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        require_admin(req)
    assert exc.value.status_code == 403


def test_require_admin_denies_roleless_when_clerk_configured(monkeypatch) -> None:
    _clear_clerk(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setenv("SIDIRA_ORG_ROLE", "admin")  # must NOT rescue a real session
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        require_admin(_bare_request())  # no org_role on state
    assert exc.value.status_code == 403


# ──────────────────────────────────────────────────────────────────────
# Layer 3 — route-level gating (member → 403, admin → not 403)
# ──────────────────────────────────────────────────────────────────────

# (method, path, json-body) for each admin-gated route. The body only needs to
# get past FastAPI's request parsing — require_admin runs as a route dependency
# before the handler body, so a member 403s regardless of payload validity, and
# an admin reaching the handler is asserted only as "not 403" (the handler's own
# 4xx/5xx for an unconfigured dispatcher etc. is fine; what matters is the gate
# let it through).
_FS_CREATE_BODY = {
    "name": "Prod warehouse",
    "kind": "snowflake",
    "account": "acme-xy12345",
    "user": "SVC_SIDIRA",
    "password": "super-secret-pw",
    "warehouse": "ANALYTICS_WH",
    "role": "SIDIRA_RO",
    "database": "PROD",
    "schema": "PUBLIC",
}
_CRAWL_SETUP_BODY = {
    "capabilities": [
        {"name": "onboarding", "entry_urls": ["https://app.lumen.dev/welcome"]},
    ],
    "sandbox_url": "https://sandbox.lumen.dev",
    "test_users": [
        {"role": "admin", "username": "a@lumen.dev", "password": "pw-1"},
    ],
    "cadence": "weekly",
    "walk_depth": 4,
}
_CRAWL_CREATE_BODY = {**_CRAWL_SETUP_BODY, "name": "iOS Sandbox"}

ADMIN_GATED = [
    ("POST", "/feature-stores", _FS_CREATE_BODY),
    ("DELETE", "/feature-stores/fs-nonexistent", None),
    ("POST", "/feature-stores/fs-nonexistent/test", None),
    ("PUT", "/crawl-setup", _CRAWL_SETUP_BODY),
    ("POST", "/crawl-setups", _CRAWL_CREATE_BODY),
    ("PUT", "/crawl-setups/some-setup", _CRAWL_SETUP_BODY),
    ("DELETE", "/crawl-setups/some-setup", None),
]

# Execution / read routes that MUST stay open to members.
MEMBER_OPEN = [
    ("POST", "/crawls", {}),  # the crawl RUN trigger
    ("GET", "/crawl-setups", None),
    ("GET", "/crawl-setup", None),
    ("GET", "/feature-stores", None),
    ("GET", "/crawls", None),
]


def _request(client: TestClient, method: str, path: str, body):
    return client.request(method, path, json=body)


def _clear_in_memory_repos() -> None:
    """Reset the process-wide in-memory repos so rows from another test file
    can't bleed into (or out of) these route assertions."""
    from sidira_simulator.adapters.repositories import (
        get_in_memory_crawl_config_repo,
        get_in_memory_feature_store_connection_repo,
        get_in_memory_repos,
    )

    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_feature_store_connection_repo()._connections.clear()
    get_in_memory_crawl_config_repo()._configs.clear()


@pytest.fixture
def member_client(monkeypatch):
    """App whose Clerk gate is active and resolves every request to a MEMBER."""
    _clear_clerk(monkeypatch)
    _clear_in_memory_repos()
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(
            user_id="user_m", customer_id="org_member", org_role="basic_member"
        ),
    )
    with TestClient(create_app()) as c:
        yield c


@pytest.fixture
def admin_client(monkeypatch):
    """App whose Clerk gate is active and resolves every request to an ADMIN."""
    _clear_clerk(monkeypatch)
    _clear_in_memory_repos()
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", DUMMY_SECRET)
    monkeypatch.setenv("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", "ci-pull-token")
    monkeypatch.setattr(
        auth,
        "authenticate",
        lambda request: auth.AuthState(user_id="user_a", customer_id="org_admin", org_role="admin"),
    )
    with TestClient(create_app()) as c:
        yield c


@pytest.mark.parametrize("method,path,body", ADMIN_GATED)
def test_member_is_forbidden_on_admin_routes(member_client, method, path, body) -> None:
    resp = _request(member_client, method, path, body)
    assert resp.status_code == 403, f"{method} {path} → {resp.status_code}: {resp.text}"
    assert resp.json()["detail"] == "admin role required for this action"


@pytest.mark.parametrize("method,path,body", ADMIN_GATED)
def test_admin_passes_the_gate(admin_client, method, path, body) -> None:
    # An admin must clear require_admin. The handler may still 4xx/5xx for its
    # own reasons (missing dispatcher, unknown id) — what we assert is that the
    # RBAC gate did NOT reject it.
    resp = _request(admin_client, method, path, body)
    assert resp.status_code != 403, f"{method} {path} → {resp.status_code}: {resp.text}"


@pytest.mark.parametrize("method,path,body", MEMBER_OPEN)
def test_member_can_reach_execution_and_read_routes(member_client, method, path, body) -> None:
    # Execution (run a crawl) + reads stay open to members — they must NOT 403.
    resp = _request(member_client, method, path, body)
    assert resp.status_code != 403, f"{method} {path} → {resp.status_code}: {resp.text}"


def test_keyless_path_still_reaches_admin_routes(monkeypatch) -> None:
    # The rest of the suite + local dev run keyless: require_admin falls back to
    # admin so a GET/POST is not 403. Use the listing reads (no creds needed) as
    # the proof the gate is transparent when Clerk is off. Clear the shared
    # in-memory repos first so a row another test file left behind can't 500 the
    # listing (these repos are process-wide; the route-test modules clear them in
    # their own fixtures for the same reason).
    from sidira_simulator.adapters.repositories import (
        get_in_memory_crawl_config_repo,
        get_in_memory_feature_store_connection_repo,
    )

    _clear_clerk(monkeypatch)
    get_in_memory_feature_store_connection_repo()._connections.clear()
    get_in_memory_crawl_config_repo()._configs.clear()
    with TestClient(app) as c:
        assert c.get("/feature-stores").status_code != 403
        assert c.get("/crawl-setups").status_code != 403
