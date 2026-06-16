"""API tests for the feature-store connection wizard (#22).

Covers connection CRUD (create/list — password never leaks), the connectivity
test (success + auth/permission/network classification), and table preview
(row count + per-column profile). Snowflake is never hit: ``_connect`` is
monkeypatched to return a fake connection/cursor with canned rows, and the
error-kind tests raise fake snowflake exceptions from the fake connect.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))
# Encrypting the connection password at rest needs the local-key fallback set
# before the app imports. Test-only fixed base64 32-byte AESGCM key.
os.environ.setdefault(
    "SIDIRA_LOCAL_CRED_KEY", "c2lkaXJhLXRlc3QtY3JlZC1rZXktMzJieXRlcyEhISE="
)

from sidira_simulator.adapters.feature_stores import (  # noqa: E402
    FeatureStoreConnectionError,
)
from sidira_simulator.adapters.feature_stores import snowflake as sf_mod  # noqa: E402
from sidira_simulator.adapters.repositories import (  # noqa: E402
    get_in_memory_feature_store_connection_repo,
    get_in_memory_repos,
)
from sidira_simulator.main import app  # noqa: E402


@pytest.fixture
def client():
    customer_repo, _, _, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    get_in_memory_feature_store_connection_repo()._connections.clear()
    with TestClient(app) as c:
        yield c


_CREATE_PAYLOAD = {
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


# ── Fakes ──────────────────────────────────────────────────────────────


class _FakeCursor:
    def __init__(self, script):
        self._script = script  # list of (description, rows) keyed by call order
        self._i = 0
        self.description = None
        self._rows: list = []

    def execute(self, sql):
        desc, rows = self._script[self._i]
        self._i += 1
        self.description = desc
        self._rows = rows

    def fetchone(self):
        return self._rows[0]

    def fetchall(self):
        return self._rows

    def close(self):
        pass


class _FakeConn:
    def __init__(self, script):
        self._script = script

    def cursor(self):
        return _FakeCursor(self._script)

    def close(self):
        pass


def _patch_connect(monkeypatch, script):
    monkeypatch.setattr(sf_mod.SnowflakeStore, "_connect", lambda self: _FakeConn(list(script)))


def _patch_connect_raises(monkeypatch, exc):
    def _boom(self):
        raise sf_mod._wrap(exc, "Snowflake connect failed")

    monkeypatch.setattr(sf_mod.SnowflakeStore, "_connect", _boom)


# ── create / list ──────────────────────────────────────────────────────


def test_create_returns_sanitized_summary_without_password(client):
    resp = client.post("/feature-stores", json=_CREATE_PAYLOAD)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"].startswith("fs-")
    assert body["account"] == "acme-xy12345"
    assert body["schema"] == "PUBLIC"
    # The password must never appear anywhere in the response.
    assert "password" not in body
    assert "super-secret-pw" not in resp.text


def test_password_never_stored_in_cleartext(client):
    resp = client.post("/feature-stores", json=_CREATE_PAYLOAD)
    cid = resp.json()["id"]
    row = get_in_memory_feature_store_connection_repo()._connections[cid]
    assert "password" not in row  # only the encrypted blob is persisted
    assert "super-secret-pw" not in str(row["password_enc"])


def test_password_blob_bound_to_connection_id(client):
    """The stored blob is AAD-bound to (customer, connection_id): copying it to
    another connection row makes it undecryptable (defeats blob-swap attacks)."""
    from sidira_simulator.adapters import credentials

    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    row = get_in_memory_feature_store_connection_repo()._connections[cid]
    customer_id = row["customer_id"]
    blob = credentials.deserialize_blob(row["password_enc"])

    # Correct binding decrypts.
    assert credentials.decrypt(blob, aad=f"{customer_id}:{cid}".encode())["password"]
    # A different connection id (the blob-copy attack) fails.
    with pytest.raises(credentials.CredentialError):
        credentials.decrypt(blob, aad=f"{customer_id}:fs-otherrow0001".encode())
    # A different customer fails too.
    with pytest.raises(credentials.CredentialError):
        credentials.decrypt(blob, aad=f"intruder:{cid}".encode())


def test_list_scoped_and_password_free(client):
    client.post("/feature-stores", json=_CREATE_PAYLOAD)
    client.post("/feature-stores", json={**_CREATE_PAYLOAD, "name": "Second"})
    resp = client.get("/feature-stores")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    assert "super-secret-pw" not in resp.text
    for item in body:
        assert "password" not in item


# ── unique connection names (#327) ─────────────────────────────────────────


def test_duplicate_name_rejected_case_insensitive(client):
    """A second connection whose name matches an existing one (case-insensitive,
    trimmed) is rejected 409 — app-level uniqueness, no migration. The form
    surfaces this near the name field."""
    assert client.post("/feature-stores", json=_CREATE_PAYLOAD).status_code == 201
    dup = client.post(
        "/feature-stores", json={**_CREATE_PAYLOAD, "name": "  prod WAREHOUSE  "}
    )
    assert dup.status_code == 409
    assert "already exists" in dup.json()["detail"]


def test_distinct_names_both_succeed(client):
    """Uniqueness is per-name, not a global cap — distinct names both persist."""
    assert client.post("/feature-stores", json=_CREATE_PAYLOAD).status_code == 201
    assert (
        client.post("/feature-stores", json={**_CREATE_PAYLOAD, "name": "Staging"}).status_code
        == 201
    )


# ── delete connection (#327) ───────────────────────────────────────────────


def test_delete_own_connection_is_204_then_gone(client):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    assert client.delete(f"/feature-stores/{cid}").status_code == 204
    # The row is gone — it no longer lists, and a re-fetch via test 404s.
    assert client.get("/feature-stores").json() == []
    assert client.post(f"/feature-stores/{cid}/test").status_code == 404


def test_delete_unknown_id_is_404(client):
    assert client.delete("/feature-stores/fs-nope").status_code == 404


def test_delete_is_customer_scoped(client):
    """A customer may only delete their OWN connection. Deleting another tenant's
    id returns 404 (never leaks existence), and the row survives untouched. We
    swap the customer via FastAPI's dependency_overrides (the route captured the
    real ``current_customer_id`` at import, so a monkeypatch wouldn't take)."""
    from sidira_simulator.api.deps import current_customer_id

    def _as(cust: str):
        app.dependency_overrides[current_customer_id] = lambda: cust

    # Customer A creates a connection.
    _as("cust-A")
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]

    # Customer B attempts to delete A's connection by its (guessed) id → 404.
    _as("cust-B")
    assert client.delete(f"/feature-stores/{cid}").status_code == 404

    # The row still belongs to A and survives.
    _as("cust-A")
    assert any(c["id"] == cid for c in client.get("/feature-stores").json())

    app.dependency_overrides.pop(current_customer_id, None)


# ── test connection ──────────────────────────────────────────────────────


def test_connection_success_is_204(client, monkeypatch):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    _patch_connect(monkeypatch, [([("1",)], [(1,)])])  # SELECT 1 -> one row
    resp = client.post(f"/feature-stores/{cid}/test")
    assert resp.status_code == 204


def test_connection_unknown_id_is_404(client):
    resp = client.post("/feature-stores/fs-nope/test")
    assert resp.status_code == 404


def test_connection_auth_error_is_400(client, monkeypatch):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    exc = RuntimeError("Incorrect username or password was specified.")
    _patch_connect_raises(monkeypatch, exc)
    resp = client.post(f"/feature-stores/{cid}/test")
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_kind"] == "auth"


def test_connection_permission_error_is_400(client, monkeypatch):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    exc = RuntimeError("Insufficient privileges to operate on warehouse")
    _patch_connect_raises(monkeypatch, exc)
    resp = client.post(f"/feature-stores/{cid}/test")
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_kind"] == "permission"


def test_connection_network_error_is_502(client, monkeypatch):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    exc = RuntimeError("Could not connect to Snowflake backend: getaddrinfo failed")
    _patch_connect_raises(monkeypatch, exc)
    resp = client.post(f"/feature-stores/{cid}/test")
    assert resp.status_code == 502
    assert resp.json()["detail"]["error_kind"] == "network"


# ── preview ──────────────────────────────────────────────────────────────


def test_preview_returns_row_count_and_column_profile(client, monkeypatch):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    # First execute = COUNT(*), second = SELECT * sample.
    count_desc = [("COUNT",)]
    count_rows = [(1000,)]
    sample_desc = [("user_id",), ("plan",)]
    sample_rows = [(1, "pro"), (2, "free"), (3, None), (4, "pro")]
    _patch_connect(monkeypatch, [(count_desc, count_rows), (sample_desc, sample_rows)])

    resp = client.post(f"/feature-stores/{cid}/preview", json={"table_fqn": "PROD.PUBLIC.USERS"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["row_count"] == 1000
    cols = {c["name"]: c for c in body["columns"]}
    assert cols["user_id"]["non_null_count"] == 4
    assert cols["user_id"]["null_fraction"] == 0.0
    assert cols["plan"]["non_null_count"] == 3
    assert cols["plan"]["null_fraction"] == 0.25
    assert cols["plan"]["distinct_count"] == 2


def test_preview_requires_table_or_sql(client):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    resp = client.post(f"/feature-stores/{cid}/preview", json={})
    assert resp.status_code == 422


@pytest.mark.parametrize(
    "bad_fqn",
    [
        "t; DROP TABLE x",
        "(SELECT secret FROM other)",
        "PROD.PUBLIC.USERS; DROP TABLE x",
        "PROD..USERS",
        "a.b.c.d",  # too many parts
        "PROD.PUBLIC.USERS WHERE 1=1",
        "PROD.PUBLIC.`USERS`",
    ],
)
def test_preview_rejects_injection_table_fqn(client, monkeypatch, bad_fqn):
    """A crafted table_fqn is rejected as a 400 before any SQL runs."""
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]

    # _connect must never be reached: validation happens first.
    def _should_not_connect(self):  # pragma: no cover - asserts it isn't called
        raise AssertionError("preview reached _connect with an unsafe table_fqn")

    monkeypatch.setattr(sf_mod.SnowflakeStore, "_connect", _should_not_connect)
    resp = client.post(f"/feature-stores/{cid}/preview", json={"table_fqn": bad_fqn})
    assert resp.status_code == 400
    assert resp.json()["detail"]["error_kind"] == "permission"


def test_preview_quotes_validated_fqn(monkeypatch):
    """A normal DB.SCHEMA.TABLE is validated and interpolated double-quoted."""
    executed: list[str] = []

    class _RecordingCursor(_FakeCursor):
        def execute(self, sql):
            executed.append(sql)
            super().execute(sql)

    class _RecordingConn(_FakeConn):
        def cursor(self):
            return _RecordingCursor(self._script)

    script = [([("COUNT",)], [(7,)]), ([("user_id",)], [(1,), (2,)])]
    monkeypatch.setattr(
        sf_mod.SnowflakeStore, "_connect", lambda self: _RecordingConn(list(script))
    )
    store = sf_mod.SnowflakeStore(
        sf_mod.SnowflakeCreds(
            account="a", user="u", password="p", warehouse="w", role="r", database="PROD"
        )
    )
    result = store.preview("PROD.PUBLIC.USERS")
    assert result.row_count == 7
    assert executed[0] == 'SELECT COUNT(*) FROM "PROD"."PUBLIC"."USERS"'
    assert executed[1].startswith('SELECT * FROM "PROD"."PUBLIC"."USERS" LIMIT')


def test_list_tables_rejects_injection_schema(monkeypatch):
    store = sf_mod.SnowflakeStore(
        sf_mod.SnowflakeCreds(
            account="a", user="u", password="p", warehouse="w", role="r", database="PROD"
        )
    )
    with pytest.raises(FeatureStoreConnectionError) as exc_info:
        store.list_tables("PUBLIC'; DROP TABLE x; --")
    assert exc_info.value.kind == "permission"


def test_preview_propagates_error_kind(client, monkeypatch):
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    exc = RuntimeError("timed out")
    _patch_connect_raises(monkeypatch, exc)
    resp = client.post(f"/feature-stores/{cid}/preview", json={"table_fqn": "PROD.PUBLIC.USERS"})
    assert resp.status_code == 502
    assert resp.json()["detail"]["error_kind"] == "network"


# ── classification unit coverage ───────────────────────────────────────


def test_classify_error_kinds():
    assert sf_mod._classify_error(RuntimeError("incorrect username or password")) == "auth"
    assert sf_mod._classify_error(RuntimeError("insufficient privileges")) == "permission"
    assert sf_mod._classify_error(RuntimeError("connection refused")) == "network"
    assert sf_mod._classify_error(RuntimeError("something weird")) == "unknown"


def test_feature_store_error_default_kind():
    assert FeatureStoreConnectionError("x").kind == "unknown"


# ── suggest-mapping endpoint (issue #23) ───────────────────────────────


_SUGGEST_COLUMNS = [
    {"name": "age", "dtype": "INT", "non_null_count": 100, "null_fraction": 0.0},
    {"name": "order_count", "dtype": "INT", "non_null_count": 100, "null_fraction": 0.0},
    {"name": "user_id", "dtype": "TEXT", "non_null_count": 100, "null_fraction": 0.0},
]


def test_suggest_mapping_returns_grouped_shape(client, monkeypatch):
    """Endpoint calls the mapper and returns the grouped MappingSuggestion shape.

    The LLM is never hit: the mapper itself is patched to return a canned
    MappingSuggestion. (The LLM-mocking depth is covered in test_column_mapper.)
    """
    from sidira_simulator.api import feature_stores as fs_mod
    from sidira_simulator.services.column_mapper import ColumnAssignment, MappingSuggestion

    canned = MappingSuggestion(
        demographic_identity=[ColumnAssignment(column="age", confidence="high")],
        behavioral_patterns=[ColumnAssignment(column="order_count", confidence="med")],
        unmapped=[ColumnAssignment(column="user_id", confidence="low")],
    )
    monkeypatch.setattr(fs_mod.column_mapper, "suggest_mapping", lambda columns: canned)

    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    resp = client.post(
        f"/feature-stores/{cid}/suggest-mapping", json={"columns": _SUGGEST_COLUMNS}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["demographic_identity"][0] == {
        "column": "age",
        "confidence": "high",
        "rationale": "",
    }
    assert body["behavioral_patterns"][0]["column"] == "order_count"
    assert body["unmapped"][0]["column"] == "user_id"


def test_suggest_mapping_llm_failure_is_502(client, monkeypatch):
    from sidira_simulator.api import feature_stores as fs_mod
    from sidira_simulator.services.column_mapper import ColumnMappingError

    def _boom(columns):
        raise ColumnMappingError("provider down")

    monkeypatch.setattr(fs_mod.column_mapper, "suggest_mapping", _boom)
    cid = client.post("/feature-stores", json=_CREATE_PAYLOAD).json()["id"]
    resp = client.post(
        f"/feature-stores/{cid}/suggest-mapping", json={"columns": _SUGGEST_COLUMNS}
    )
    assert resp.status_code == 502
