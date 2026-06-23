"""API tests for the crawl setup window (#171).

GET /crawl-setup returns an empty envelope before any save; PUT validates
the CrawlSetup contract (capability count, entry-url count + scheme, walk
depth bounds) and round-trips; saves are customer-scoped. The trigger
endpoints are covered in test_crawl_trigger_api.py (#193) — here only the
unconfigured-token 503 is pinned.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Saving a crawl setup now encrypts the role passwords at rest (#206 Slice C),
# so the local-key fallback must be configured before the app imports. A fixed
# base64 32-byte AESGCM key — test-only, never a real secret.
os.environ.setdefault(
    "SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="
)

from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_crawl_config_repo,
    get_in_memory_repos,
)
from sidira_simulator.main import app  # noqa: E402


@pytest.fixture
def client():
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_crawl_config_repo()._configs.clear()
    with TestClient(app) as c:
        yield c


def _setup_payload(**overrides):
    payload = {
        "capabilities": [
            {"name": "onboarding-checklist", "entry_urls": ["https://app.lumen.dev/welcome"]},
            {
                "name": "weekly-digest",
                "entry_urls": ["https://app.lumen.dev/settings/digest"],
            },
        ],
        "sandbox_url": "https://sandbox.lumen.dev",
        "test_users": [
            {"role": "admin", "username": "crawler-admin@lumen.dev", "password": "adm-pw-s3cret"},
            {"role": "member", "username": "crawler-member@lumen.dev", "password": "mbr-pw-s3cret"},
        ],
        "ip_allowlist_note": "egress IPs allowlisted in Cloudflare WAF",
        "cadence": "weekly",
        "walk_depth": 3,
    }
    payload.update(overrides)
    return payload


def test_get_before_any_save_returns_empty_envelope(client):
    resp = client.get("/crawl-setup")
    assert resp.status_code == 200
    body = resp.json()
    assert body["setup"] is None
    assert body["updated_at"] is None


def test_put_then_get_round_trips(client):
    put = client.put("/crawl-setup", json=_setup_payload())
    assert put.status_code == 200
    saved = put.json()
    assert saved["setup"]["walk_depth"] == 3
    assert saved["updated_at"] is not None

    got = client.get("/crawl-setup").json()
    assert got["setup"] == saved["setup"]
    assert [c["name"] for c in got["setup"]["capabilities"]] == [
        "onboarding-checklist",
        "weekly-digest",
    ]


def test_put_overwrites_prior_save(client):
    client.put("/crawl-setup", json=_setup_payload())
    client.put("/crawl-setup", json=_setup_payload(walk_depth=4, cadence="on_demand"))
    got = client.get("/crawl-setup").json()
    assert got["setup"]["walk_depth"] == 4
    assert got["setup"]["cadence"] == "on_demand"


def test_crawl_setup_endpoints_operate_on_the_default_setup(client):
    """#215/#245 PR1: GET/PUT /crawl-setup are unchanged endpoints that now land
    on the org's reserved "default" setup. A single-target tenant is identical;
    the row persists under setup_id="default" (the only key those routes use)."""
    from sidira_simulator.adapters.repositories import (
        DEFAULT_SETUP_ID,
        get_in_memory_crawl_config_repo,
    )

    client.put("/crawl-setup", json=_setup_payload(walk_depth=5))
    repo = get_in_memory_crawl_config_repo()
    # Exactly one row, keyed to the default setup.
    assert list(repo._configs.keys()) == [("demo", DEFAULT_SETUP_ID)]
    # And it is reachable by the default-keyed get the routes use.
    row = repo._configs[("demo", DEFAULT_SETUP_ID)]
    assert row["setup_id"] == DEFAULT_SETUP_ID
    assert client.get("/crawl-setup").json()["setup"]["walk_depth"] == 5


def test_walk_depth_defaults_to_six_and_accepts_new_ceiling(client):
    """#227: walk_depth realigned to the crawler's per-capability max_hops intent —
    default 6 (parity with CapabilityConfig.max_hops), range 2–8 so depth is a
    safety ceiling above the deepest real flow, never the binding constraint."""
    payload = _setup_payload()
    del payload["walk_depth"]
    got = client.put("/crawl-setup", json=payload).json()
    assert got["setup"]["walk_depth"] == 6

    deep = client.put("/crawl-setup", json=_setup_payload(walk_depth=8)).json()
    assert deep["setup"]["walk_depth"] == 8


@pytest.mark.parametrize(
    "overrides",
    [
        {"capabilities": []},  # at least one capability
        {"capabilities": [{"name": f"cap-{i}", "entry_urls": ["https://x.dev"]} for i in range(11)]},
        {
            "capabilities": [
                {"name": "too-many-urls", "entry_urls": [f"https://x.dev/{i}" for i in range(4)]}
            ]
        },
        {"capabilities": [{"name": "bad-scheme", "entry_urls": ["ftp://x.dev"]}]},
        {"capabilities": [{"name": "no-host", "entry_urls": ["https://"]}]},
        # Credential-bearing URLs must never reach config_json (codex P2, #206).
        {"capabilities": [{"name": "creds", "entry_urls": ["https://u:p@x.dev"]}]},
        {"sandbox_url": "not-a-url"},
        {"sandbox_url": "https://"},  # scheme-only — no host to navigate
        {"sandbox_url": "https://user:pass@sandbox.lumen.dev"},  # embedded creds
        {"test_users": []},  # one login per role minimum
        # Slice C (#206): every login must carry a non-blank password, and each
        # role may appear only once (the secret store is keyed by role).
        {"test_users": [{"role": "admin", "username": "a@x.dev"}]},  # missing password
        {"test_users": [{"role": "admin", "username": "a@x.dev", "password": ""}]},  # blank
        {"test_users": [{"role": "admin", "username": "a@x.dev", "password": "   "}]},  # whitespace
        {
            "test_users": [
                {"role": "admin", "username": "a@x.dev", "password": "p1"},
                {"role": "admin", "username": "b@x.dev", "password": "p2"},
            ]
        },  # duplicate role
        {"walk_depth": 1},  # below the floor (#227: range is 2–8)
        {"walk_depth": 9},  # above the ceiling (#227)
        {"cadence": "hourly"},
    ],
)
def test_put_rejects_contract_violations(client, overrides):
    resp = client.put("/crawl-setup", json=_setup_payload(**overrides))
    assert resp.status_code == 422


def test_setup_is_customer_scoped(client, monkeypatch):
    client.put("/crawl-setup", json=_setup_payload())

    monkeypatch.setenv("SIDIRA_CUSTOMER_ID", "other-tenant")
    got = client.get("/crawl-setup").json()
    assert got["customer_id"] == "other-tenant"
    assert got["setup"] is None


def test_dispatch_payload_is_non_secret_projection():
    """The crawl trigger ships this to the workflow (#206). It must carry the
    walk inputs and role *names* but never a login username or password — the
    crawler pulls credentials from an authenticated endpoint at run start."""
    from sidira_simulator.schemas.crawl import CrawlSetup

    setup = CrawlSetup.model_validate(_setup_payload())
    payload = setup.dispatch_payload()

    assert payload["product_id"] == "default"  # #215 forward-compat default
    assert payload["sandbox_url"] == "https://sandbox.lumen.dev"
    assert payload["walk_depth"] == 3
    assert payload["cadence"] == "weekly"
    assert [c["name"] for c in payload["capabilities"]] == [
        "onboarding-checklist",
        "weekly-digest",
    ]
    assert payload["roles"] == ["admin", "member"]

    blob = repr(payload)
    assert "crawler-admin@lumen.dev" not in blob
    assert "username" not in payload and "test_users" not in payload
    assert setup.dispatch_payload(product_id="driver-app")["product_id"] == "driver-app"


def test_password_is_never_echoed_back(client):
    """The PUT response and a follow-up GET both return the password-free
    projection — passwords go in but never come back out (#206 Slice C)."""
    put = client.put("/crawl-setup", json=_setup_payload())
    assert put.status_code == 200
    got = client.get("/crawl-setup")

    for resp in (put, got):
        users = resp.json()["setup"]["test_users"]
        assert [u["role"] for u in users] == ["admin", "member"]
        for u in users:
            assert "password" not in u
        # belt-and-suspenders: the secret never appears anywhere in the body.
        assert "adm-pw-s3cret" not in resp.text
        assert "mbr-pw-s3cret" not in resp.text


def test_password_stored_encrypted_not_cleartext(client):
    """config_json persists the password-free setup plus an encrypted blob — the
    plaintext password must not appear in the stored row (#206 Slice C)."""
    from sidira_simulator.api.crawls import CREDENTIALS_ENC_KEY

    client.put("/crawl-setup", json=_setup_payload())
    row = get_in_memory_crawl_config_repo()._configs[("demo", "default")]
    stored = json.dumps(row["config_json"])
    assert "adm-pw-s3cret" not in stored
    assert "mbr-pw-s3cret" not in stored
    # The encrypted sibling is present and self-describes as the local-key blob.
    enc = row["config_json"][CREDENTIALS_ENC_KEY]
    assert enc["kek_id"] == "local"
    assert enc["ciphertext"] and enc["nonce"]


def test_save_without_cred_key_is_503(client, monkeypatch):
    """With no key material configured we refuse to store a login we cannot
    protect — a 503, not a silent cleartext save."""
    monkeypatch.delenv("SIDIRA_LOCAL_CRED_KEY", raising=False)
    monkeypatch.delenv("PYTHIA_LOCAL_CRED_KEY", raising=False)
    resp = client.put("/crawl-setup", json=_setup_payload())
    assert resp.status_code == 503
    assert "SIDIRA_LOCAL_CRED_KEY" in resp.json()["detail"]


def test_field_validation_error_never_echoes_the_password(client):
    """A 422 on the password field must not reflect the rejected secret — the
    default Pydantic error payload includes `input`, so it is redacted
    (codex P2, #206 Slice C)."""
    secret = "p" * 300  # exceeds max_length=256 → 422 on the password field
    resp = client.put(
        "/crawl-setup",
        json=_setup_payload(
            test_users=[{"role": "admin", "username": "a@x.dev", "password": secret}]
        ),
    )
    assert resp.status_code == 422
    assert secret not in resp.text
    assert "<redacted>" in resp.text


def test_model_level_validation_error_never_echoes_passwords(client):
    """A model-level test_users error (duplicate role) carries the whole
    password-bearing list as its `input` — that must be redacted too."""
    resp = client.put(
        "/crawl-setup",
        json=_setup_payload(
            test_users=[
                {"role": "admin", "username": "a@x.dev", "password": "dup-pw-aaaa"},
                {"role": "admin", "username": "b@x.dev", "password": "dup-pw-bbbb"},
            ]
        ),
    )
    assert resp.status_code == 422
    assert "dup-pw-aaaa" not in resp.text
    assert "dup-pw-bbbb" not in resp.text


def test_top_level_validation_error_never_echoes_passwords(client):
    """A validation failure on an unrelated top-level field (here, missing
    capabilities) can carry the entire submitted body — passwords included — as
    the Pydantic error `input`. The crawl-setup 422 redacts every error's input,
    not just the password-loc ones (codex P2, #206 Slice C)."""
    payload = _setup_payload(
        test_users=[{"role": "admin", "username": "a@x.dev", "password": "whole-body-secret"}]
    )
    del payload["capabilities"]  # triggers a top-level missing-field error
    resp = client.put("/crawl-setup", json=payload)
    assert resp.status_code == 422
    assert "whole-body-secret" not in resp.text


def test_plural_create_top_level_error_never_echoes_passwords(client):
    """POST /crawl-setups carries a password-bearing body too. A 422 on an
    unrelated top-level field (missing capabilities) puts the whole submitted
    body — passwords included — in the Pydantic error `input`, so it must be
    redacted exactly like the singular route. The plural write routes were NOT
    in the secret-body path set until #215/#245 (this is that fix's guard)."""
    payload = _setup_payload(
        test_users=[{"role": "admin", "username": "a@x.dev", "password": "plural-create-secret"}]
    )
    payload["name"] = "Driver app"
    del payload["capabilities"]
    resp = client.post("/crawl-setups", json=payload)
    assert resp.status_code == 422
    assert "plural-create-secret" not in resp.text


def test_plural_update_top_level_error_never_echoes_passwords(client):
    """PUT /crawl-setups/{id} likewise — body validation (and thus redaction)
    runs before the handler's 404 existence check, so an invalid body on ANY id
    must not leak the submitted password."""
    payload = _setup_payload(
        test_users=[{"role": "admin", "username": "a@x.dev", "password": "plural-update-secret"}]
    )
    del payload["capabilities"]
    resp = client.put("/crawl-setups/driver-app", json=payload)
    assert resp.status_code == 422
    assert "plural-update-secret" not in resp.text


@pytest.mark.parametrize(
    "bad_key",
    [
        "not valid base64!!",  # binascii.Error from the base64 decode
        "c2hvcnQ=",  # decodes to "short" — 5 bytes, not a valid AES-GCM length
    ],
)
def test_save_with_malformed_cred_key_is_503_not_500(client, monkeypatch, bad_key):
    """A typo'd or wrong-length SIDIRA_LOCAL_CRED_KEY must fail closed as a
    controlled 503 (the deploy runbook has operators create this key by hand),
    not surface a raw binascii/ValueError as a 500 (codex P2, #206 Slice C)."""
    monkeypatch.setenv("SIDIRA_LOCAL_CRED_KEY", bad_key)
    resp = client.put("/crawl-setup", json=_setup_payload())
    assert resp.status_code == 503
    assert "SIDIRA_LOCAL_CRED_KEY" in resp.json()["detail"]


def test_trigger_unconfigured_is_503_not_501(client, monkeypatch):
    """#193 wired the trigger; without the dispatch token it is explicitly
    un-dispatchable (503), never a silent stub. Full lifecycle coverage
    lives in test_crawl_trigger_api.py."""
    monkeypatch.delenv("SIDIRA_CRAWLER_DISPATCH_TOKEN", raising=False)
    monkeypatch.delenv("PYTHIA_CRAWLER_DISPATCH_TOKEN", raising=False)
    resp = client.post("/crawls")
    assert resp.status_code == 503
    assert "SIDIRA_CRAWLER_DISPATCH_TOKEN" in resp.json()["detail"]
