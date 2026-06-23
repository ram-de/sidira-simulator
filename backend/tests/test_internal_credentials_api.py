"""API tests for the internal credential-pull endpoint (#206 Slice C).

``GET /internal/crawl-credentials/{customer}`` is the ONE authenticated channel
through which decrypted role logins leave the backend. The crawler CI calls it
at run start. It is gated by a dedicated CI-only bearer token
(``SIDIRA_CRAWLER_CREDENTIALS_TOKEN``), bypasses the Clerk *session* gate (CI
carries no browser session), and returns the decrypted role→{username,password}
joined from the password-free setup + the at-rest blob.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Same test-only local key as test_crawls_api — decrypt must round-trip what the
# PUT path encrypted.
os.environ.setdefault(
    "SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="
)

from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_crawl_config_repo,
    get_in_memory_repos,
)
from sidira_simulator.main import app  # noqa: E402

_TOKEN = "ci-pull-token-abc123"
_URL = "/internal/crawl-credentials/demo"


@pytest.fixture
def client(monkeypatch):
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_crawl_config_repo()._configs.clear()
    monkeypatch.setenv("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", _TOKEN)
    with TestClient(app) as c:
        yield c


def _seed_setup(client):
    """Save a setup (with passwords) for the default 'demo' customer via the
    real PUT path so the at-rest blob is produced exactly as in prod."""
    payload = {
        "capabilities": [
            {"name": "onboarding", "entry_urls": ["https://app.lumen.dev/welcome"]},
        ],
        "sandbox_url": "https://sandbox.lumen.dev",
        "test_users": [
            {"role": "admin", "username": "crawler-admin@lumen.dev", "password": "adm-pw-s3cret"},
            {"role": "member", "username": "crawler-member@lumen.dev", "password": "mbr-pw-s3cret"},
        ],
    }
    resp = client.put("/crawl-setup", json=payload)
    assert resp.status_code == 200


def _auth(token=_TOKEN):
    return {"Authorization": f"Bearer {token}"}


def test_valid_token_returns_decrypted_logins(client):
    _seed_setup(client)
    resp = client.get(_URL, headers=_auth())
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer_id"] == "demo"
    logins = {lg["role"]: lg for lg in body["logins"]}
    assert logins["admin"]["username"] == "crawler-admin@lumen.dev"
    assert logins["admin"]["password"] == "adm-pw-s3cret"
    assert logins["member"]["password"] == "mbr-pw-s3cret"


def test_missing_token_is_404(client):
    _seed_setup(client)
    resp = client.get(_URL)
    # 404, never 401/403: don't confirm the endpoint exists to an unauthed caller.
    assert resp.status_code == 404


def test_wrong_token_is_404(client):
    _seed_setup(client)
    resp = client.get(_URL, headers=_auth("not-the-token"))
    assert resp.status_code == 404


def test_non_bearer_scheme_is_404(client):
    _seed_setup(client)
    resp = client.get(_URL, headers={"Authorization": _TOKEN})  # no "Bearer " prefix
    assert resp.status_code == 404


def test_token_unconfigured_is_503(client, monkeypatch):
    _seed_setup(client)
    monkeypatch.delenv("SIDIRA_CRAWLER_CREDENTIALS_TOKEN", raising=False)
    monkeypatch.delenv("PYTHIA_CRAWLER_CREDENTIALS_TOKEN", raising=False)
    resp = client.get(_URL, headers=_auth())
    assert resp.status_code == 503


def test_unknown_customer_is_404(client):
    # Valid token, but nothing saved for this customer.
    resp = client.get("/internal/crawl-credentials/nobody", headers=_auth())
    assert resp.status_code == 404


def test_pull_passes_through_internal_key_gate(client, monkeypatch):
    """The crawler reaches api.sidira.ai directly and Caddy does not staple
    X-Sidira-Internal-Key on this path, so /internal/* must bypass the
    internal-key gate too — the bearer token is the sole authority. Even with
    SIDIRA_INTERNAL_API_KEY configured and no key header on the request, a valid
    bearer succeeds."""
    _seed_setup(client)  # seed before enabling the gate (PUT isn't an /internal path)
    monkeypatch.setenv("SIDIRA_INTERNAL_API_KEY", "prod-network-key")
    resp = client.get(_URL, headers=_auth())  # bearer only, no x-sidira-internal-key
    assert resp.status_code == 200


def test_undecryptable_blob_is_503_not_500(client):
    """A rotated key or corrupted ciphertext must surface as a controlled 503,
    never an opaque 500 (codex P2)."""
    _seed_setup(client)
    row = get_in_memory_crawl_config_repo()._configs[("demo", "default")]
    # Tamper the ciphertext so AESGCM auth fails (InvalidTag).
    row["config_json"]["credentials_enc"]["ciphertext"] = "QUJDREVG"  # bogus base64
    resp = client.get(_URL, headers=_auth())
    assert resp.status_code == 503


def test_incomplete_credentials_is_409_not_partial_200(client):
    """If the stored blob is missing a login for a configured role, the pull
    must fail closed (409) rather than return a partial set the crawler would
    start half-authenticated with — mirrors the dispatch preflight (codex P2,
    #206 Slice C)."""
    from sidira_simulator.adapters import credentials
    from sidira_simulator.api.crawls import CREDENTIALS_ENC_KEY

    _seed_setup(client)  # setup has admin + member roles
    row = get_in_memory_crawl_config_repo()._configs[("demo", "default")]
    # Re-encrypt with only the admin login — member is now uncovered.
    row["config_json"][CREDENTIALS_ENC_KEY] = credentials.serialize_blob(
        credentials.encrypt({"admin": "adm-pw-s3cret"})
    )
    resp = client.get(_URL, headers=_auth())
    assert resp.status_code == 409
    assert "re-save" in resp.json()["detail"]


def test_setup_without_credentials_is_404(client):
    """A setup row saved before Slice C (no encrypted blob) has nothing to
    deliver — 404 rather than a partial or empty 200."""
    from sidira_simulator.api.crawls import CREDENTIALS_ENC_KEY

    _seed_setup(client)
    row = get_in_memory_crawl_config_repo()._configs[("demo", "default")]
    row["config_json"].pop(CREDENTIALS_ENC_KEY, None)
    resp = client.get(_URL, headers=_auth())
    assert resp.status_code == 404
