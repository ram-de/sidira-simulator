"""Clerk webhook endpoint — #31.

The endpoint is public (Clerk reaches it server-to-server) but verifies every
delivery against the Svix signing secret before any side effect, and provisions a
``customers`` row from ``organization.created`` events. These tests cover the
security boundary (missing secret, bad signature, gate-bypass) and the tenancy
side effect (org → customer, idempotency, ignored events).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from sidira_simulator.api import auth
from sidira_simulator.api.deps import get_customer_repo
from sidira_simulator.main import create_app

WEBHOOK_SECRET = "whsec_MfKQ9r8GKYqrTwjUPD8ILPZIo2LaLaSw"
SESSION_SECRET = "sk_test_dummy"


class _RecordingCustomerRepo:
    """Captures ensure_exists calls so tests can assert the side effect."""

    def __init__(self) -> None:
        self.calls: list[dict[str, str | None]] = []

    async def ensure_exists(
        self, customer_id: str, name: str | None = None, clerk_org_id: str | None = None
    ) -> None:
        self.calls.append({"customer_id": customer_id, "name": name, "clerk_org_id": clerk_org_id})


def _clear_env(monkeypatch) -> None:
    for prefix in ("SIDIRA_", "PYTHIA_"):
        for key in ("CLERK_WEBHOOK_SECRET", "CLERK_SECRET_KEY", "CUSTOMER_ID", "INTERNAL_API_KEY"):
            monkeypatch.delenv(f"{prefix}{key}", raising=False)


def _client(repo: _RecordingCustomerRepo) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_customer_repo] = lambda: repo
    return TestClient(app)


def _signed(payload: dict, *, secret: str = WEBHOOK_SECRET) -> tuple[str, dict[str, str]]:
    """Serialize + Svix-sign a payload, returning (body, headers) for the POST."""
    from svix.webhooks import Webhook

    msg_id = "msg_test_1"
    ts = datetime.now(timezone.utc)
    body = json.dumps(payload)
    signature = Webhook(secret).sign(msg_id, ts, body)
    headers = {
        "svix-id": msg_id,
        "svix-timestamp": str(int(ts.timestamp())),
        "svix-signature": signature,
    }
    return body, headers


def _org_created(org_id: str = "org_abc", name: str = "Acme Inc") -> dict:
    return {"type": "organization.created", "data": {"id": org_id, "name": name}}


def test_missing_secret_returns_503(monkeypatch) -> None:
    _clear_env(monkeypatch)  # no webhook secret -> cannot verify -> refuse
    repo = _RecordingCustomerRepo()
    body, headers = _signed(_org_created())

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 503, resp.text
    assert repo.calls == []


def test_invalid_signature_is_rejected(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    repo = _RecordingCustomerRepo()
    body, headers = _signed(_org_created())
    headers["svix-signature"] = "v1,deadbeefnotarealsignature"

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 401, resp.text
    assert repo.calls == []


def test_org_created_provisions_customer(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    repo = _RecordingCustomerRepo()
    body, headers = _signed(_org_created(org_id="org_xyz", name="Globex"))

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ok", "customer_id": "org_xyz"}
    # customer id == clerk org id == R2 prefix root; clerk_org_id mirrored.
    assert repo.calls == [{"customer_id": "org_xyz", "name": "Globex", "clerk_org_id": "org_xyz"}]


def test_org_created_backfills_placeholder_row_from_prior_simulation(monkeypatch) -> None:
    """Signup-then-act race: a POST /simulations call provisioned a placeholder
    customer (name == org id, clerk_org_id NULL) before organization.created
    arrived. The webhook must backfill the real org name + clerk_org_id rather
    than no-op on the existing row.
    """
    from sidira_simulator.adapters.repositories import InMemoryCustomerRepo

    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    repo = InMemoryCustomerRepo()
    repo._customers["org_race"] = {"id": "org_race", "name": "org_race", "clerk_org_id": None}
    body, headers = _signed(_org_created(org_id="org_race", name="Acme Inc"))

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 200, resp.text
    assert repo._customers["org_race"] == {
        "id": "org_race",
        "name": "Acme Inc",
        "clerk_org_id": "org_race",
    }


def test_org_created_is_idempotent_on_redelivery(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    repo = _RecordingCustomerRepo()
    client = _client(repo)
    body, headers = _signed(_org_created(org_id="org_dup"))

    first = client.post("/webhooks/clerk", content=body, headers=headers)
    second = client.post("/webhooks/clerk", content=body, headers=headers)

    # Both deliveries are accepted (200); the repo's ensure_exists carries the
    # idempotency contract (ON CONFLICT DO NOTHING), so redelivery never errors.
    assert first.status_code == 200 and second.status_code == 200
    assert [c["customer_id"] for c in repo.calls] == ["org_dup", "org_dup"]


def test_org_created_without_id_is_rejected(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    repo = _RecordingCustomerRepo()
    body, headers = _signed({"type": "organization.created", "data": {"name": "No Id"}})

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 400, resp.text
    assert repo.calls == []


def test_unhandled_event_is_acked_without_side_effect(monkeypatch) -> None:
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    repo = _RecordingCustomerRepo()
    body, headers = _signed({"type": "user.created", "data": {"id": "user_1"}})

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"status": "ignored", "event": "user.created"}
    assert repo.calls == []


def test_webhook_bypasses_session_auth_gate(monkeypatch) -> None:
    """Even with the Clerk session gate active, the webhook self-authenticates.

    The endpoint carries no browser session token, so without the _PUBLIC_PATHS
    exemption the gate would 401 it before signature verification ran.
    """
    _clear_env(monkeypatch)
    monkeypatch.setenv("SIDIRA_CLERK_WEBHOOK_SECRET", WEBHOOK_SECRET)
    monkeypatch.setenv("SIDIRA_CLERK_SECRET_KEY", SESSION_SECRET)  # session gate ON
    monkeypatch.setattr(auth, "authenticate", lambda request: None)  # no valid session
    repo = _RecordingCustomerRepo()
    body, headers = _signed(_org_created(org_id="org_gate"))

    resp = _client(repo).post("/webhooks/clerk", content=body, headers=headers)

    assert resp.status_code == 200, resp.text
    assert repo.calls[0]["customer_id"] == "org_gate"
