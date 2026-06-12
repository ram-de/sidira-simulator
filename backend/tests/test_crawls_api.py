"""API tests for the crawl setup window (#171).

GET /crawl-setup returns an empty envelope before any save; PUT validates
the CrawlSetup contract (capability count, entry-url count + scheme, walk
depth bounds) and round-trips; saves are customer-scoped. The trigger
endpoints are covered in test_crawl_trigger_api.py (#193) — here only the
unconfigured-token 503 is pinned.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

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
            {"role": "admin", "username": "crawler-admin@lumen.dev"},
            {"role": "member", "username": "crawler-member@lumen.dev"},
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
        {"sandbox_url": "not-a-url"},
        {"sandbox_url": "https://"},  # scheme-only — no host to navigate
        {"test_users": []},  # one login per role minimum
        {"walk_depth": 5},
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


def test_trigger_unconfigured_is_503_not_501(client, monkeypatch):
    """#193 wired the trigger; without the dispatch token it is explicitly
    un-dispatchable (503), never a silent stub. Full lifecycle coverage
    lives in test_crawl_trigger_api.py."""
    monkeypatch.delenv("SIDIRA_CRAWLER_DISPATCH_TOKEN", raising=False)
    monkeypatch.delenv("PYTHIA_CRAWLER_DISPATCH_TOKEN", raising=False)
    resp = client.post("/crawls")
    assert resp.status_code == 503
    assert "SIDIRA_CRAWLER_DISPATCH_TOKEN" in resp.json()["detail"]
