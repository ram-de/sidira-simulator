"""API test for the #3 doc-feeder extraction route.

Covers POST /feature-stores/extract-documents: the LLM extractor is monkeypatched
(no network) so the test pins the route contract — bounded rows in, row_count +
profiled columns + rows out — plus the 400 on a malformed schema.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
os.environ.setdefault(
    "SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="
)

from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services import document_extractor as de_mod  # noqa: E402


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


_SCHEMA = {
    "fields": [
        {"name": "orders_count", "type": "count"},
        {"name": "is_churned", "type": "flag"},
        {"name": "primary_device", "type": "categorical"},
    ],
    "entity_key": "entity_id",
}

_PAYLOAD = {
    "documents": [
        {"entity_id": "u1", "text": "Orders a lot, on iphone, still active."},
        {"entity_id": "u2", "text": "Churned last month."},
    ],
    "extraction_schema": _SCHEMA,
}


def test_extract_documents_returns_rows_and_profiles(client, monkeypatch):
    # Stub the LLM extraction; the route still profiles the rows for real.
    def _fake(documents, schema, llm=None):
        return [
            {"entity_id": "u1", "orders_count": 9.0, "is_churned": 0.0, "primary_device": "ios"},
            {"entity_id": "u2", "orders_count": None, "is_churned": 1.0, "primary_device": None},
        ]

    monkeypatch.setattr(de_mod, "extract_feature_rows", _fake)

    resp = client.post("/feature-stores/extract-documents", json=_PAYLOAD)
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 2
    assert [c["name"] for c in body["columns"]] == [
        "orders_count", "is_churned", "primary_device"
    ]
    churn = next(c for c in body["columns"] if c["name"] == "is_churned")
    assert churn["dtype"] == "flag"
    assert churn["non_null_count"] == 2
    # rows ride back so the wizard can carry them into the build.
    assert body["rows"][0]["entity_id"] == "u1"
    assert body["rows"][1]["is_churned"] == 1.0


def test_extract_documents_rejects_bad_schema(client):
    """A malformed schema is a caller error → 400, BEFORE any LLM call."""
    bad = {**_PAYLOAD, "extraction_schema": {"fields": [{"name": "x", "type": "vibes"}]}}
    resp = client.post("/feature-stores/extract-documents", json=bad)
    assert resp.status_code == 400
    assert "unknown type" in resp.json()["detail"]


def test_extract_documents_rejects_too_many_documents(client):
    """Guard rail: an unbounded document count fans out into unbounded LLM calls
    → 413 before the extractor is ever invoked."""
    huge = {
        **_PAYLOAD,
        "documents": [{"entity_id": f"u{i}", "text": "x"} for i in range(501)],
    }
    resp = client.post("/feature-stores/extract-documents", json=huge)
    assert resp.status_code == 413
    assert "too many documents" in resp.json()["detail"]


def test_extract_documents_rejects_oversized_single_document(client):
    """Guard rail: ONE document over the per-doc cap → 413, because a single
    document is sent in one call and would blow the provider context window."""
    big = {
        **_PAYLOAD,
        "documents": [{"entity_id": "u1", "text": "x" * 200_001}],
    }
    resp = client.post("/feature-stores/extract-documents", json=big)
    assert resp.status_code == 413
    detail = resp.json()["detail"]
    assert "per document" in detail and "'u1'" in detail


def test_extract_documents_rejects_oversized_total_text(client):
    """Guard rail: many in-spec documents that SUM over the total cap → 413."""
    big = {
        **_PAYLOAD,
        # each doc is under the 200k per-doc cap, but 11 × 199k > 2M total.
        "documents": [{"entity_id": f"u{i}", "text": "x" * 199_000} for i in range(11)],
    }
    resp = client.post("/feature-stores/extract-documents", json=big)
    assert resp.status_code == 413
    assert "document text too large" in resp.json()["detail"]
