"""Feature-store routes — connection CRUD, connectivity test, schema inspection, mapping suggestions."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.credentials import CredentialError
from sidira_simulator.adapters.feature_stores import (
    ColumnProfile,
    FeatureStoreConnectionError,
)
from sidira_simulator.adapters.feature_stores.snowflake import SnowflakeCreds, SnowflakeStore
from sidira_simulator.adapters.repositories import FeatureStoreConnectionRepo
from sidira_simulator.api.deps import current_customer_id, get_feature_store_connection_repo
from sidira_simulator.services import column_mapper
from sidira_simulator.services.column_mapper import ColumnMappingError, MappingSuggestion

router = APIRouter(prefix="/feature-stores", tags=["feature-stores"])

#: HTTP status codes per classified connection-failure kind. Client-fixable
#: problems (bad creds / missing grants) are 400; problems on the store/network
#: side are 502 (bad upstream).
_ERROR_KIND_STATUS: dict[str, int] = {
    "auth": 400,
    "permission": 400,
    "network": 502,
    "unknown": 502,
}


class SnowflakeConnectionRequest(BaseModel):
    name: str = Field(description="Customer-facing label for this connection.")
    kind: Literal["snowflake"] = "snowflake"
    account: str
    user: str
    password: str
    warehouse: str
    role: str
    database: str
    schema_: str | None = Field(default=None, alias="schema")


class ConnectionSummary(BaseModel):
    """Sanitized view of a saved connection. Never includes the password."""

    id: str
    name: str
    kind: Literal["snowflake"]
    account: str
    user: str
    warehouse: str
    role: str
    database: str
    schema_: str | None = Field(default=None, alias="schema")


class PreviewRequest(BaseModel):
    table_fqn: str | None = None
    sql: str | None = None
    sample_size: int = 100


class PreviewResponse(BaseModel):
    row_count: int
    columns: list[ColumnProfile]


class SuggestMappingRequest(BaseModel):
    columns: list[ColumnProfile]


def _summary_from_row(row: dict) -> ConnectionSummary:
    """Sanitized view of a stored row — never includes the password/blob."""
    return ConnectionSummary(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        account=row["account"],
        user=row["user"],
        warehouse=row["warehouse"],
        role=row["role"],
        database=row["database"],
        schema=row["schema"],
    )


def _store_from_row(row: dict, customer_id: str) -> SnowflakeStore:
    """Decrypt the password blob and build a SnowflakeStore. Decryption is
    fresh per call; the cleartext password never leaves this function's scope.
    Raises 503 on a credential/key problem (never an opaque 500)."""
    aad = f"{customer_id}:{row['id']}".encode()
    try:
        secrets = credentials.decrypt(
            credentials.deserialize_blob(row["password_enc"]),
            customer_id=customer_id,
            aad=aad,
        )
    except CredentialError as exc:
        raise HTTPException(
            status_code=503,
            detail="cannot decrypt stored connection credentials — re-save the connection",
        ) from exc
    creds = SnowflakeCreds(
        account=row["account"],
        user=row["user"],
        password=secrets["password"],
        warehouse=row["warehouse"],
        role=row["role"],
        database=row["database"],
        schema=row["schema"],
    )
    return SnowflakeStore(creds)


def _connection_error(exc: FeatureStoreConnectionError) -> HTTPException:
    """Translate a classified adapter error into a structured HTTPException."""
    kind = getattr(exc, "kind", "unknown")
    status = _ERROR_KIND_STATUS.get(kind, 502)
    return HTTPException(
        status_code=status,
        detail={"error_kind": kind, "message": str(exc)},
    )


@router.post("", response_model=ConnectionSummary, status_code=201)
async def create_connection(
    payload: SnowflakeConnectionRequest,
    customer_id: str = Depends(current_customer_id),
    repo: FeatureStoreConnectionRepo = Depends(get_feature_store_connection_repo),
) -> ConnectionSummary:
    """Encrypt the password at rest and persist a sanitized connection row."""
    # Unique connection names per customer (#327). The "Saved connections" picker
    # disambiguates near-identical rows by name; two rows sharing a name are what
    # made the live picker unreadable. Enforce uniqueness app-level (a name query,
    # no DB unique constraint → no Alembic migration). Case-insensitive on the
    # trimmed name, mirroring the repo helper; a clash returns a clean 409 the
    # form surfaces near the name field.
    if await repo.name_exists(customer_id, payload.name):
        raise HTTPException(
            status_code=409,
            detail=f"a saved connection named {payload.name.strip()!r} already exists — "
            "pick a different name",
        )
    # Bind the blob to (customer_id, connection_id) via AAD so a password_enc
    # copied to another tenant/connection row cannot decrypt. The id is minted
    # here (not inside the repo) so the same value is the AAD and the row id.
    connection_id = f"fs-{uuid4().hex[:12]}"
    aad = f"{customer_id}:{connection_id}".encode()
    try:
        blob = credentials.encrypt(
            {"password": payload.password}, customer_id=customer_id, aad=aad
        )
    except CredentialError as exc:
        raise HTTPException(
            status_code=503, detail="credential encryption is not configured"
        ) from exc
    row = await repo.insert(
        {
            "id": connection_id,
            "customer_id": customer_id,
            "name": payload.name,
            "kind": payload.kind,
            "account": payload.account,
            "user": payload.user,
            "warehouse": payload.warehouse,
            "role": payload.role,
            "database": payload.database,
            "schema": payload.schema_,
            "password_enc": credentials.serialize_blob(blob),
        }
    )
    return _summary_from_row(row)


@router.get("", response_model=list[ConnectionSummary])
async def list_connections(
    customer_id: str = Depends(current_customer_id),
    repo: FeatureStoreConnectionRepo = Depends(get_feature_store_connection_repo),
) -> list[ConnectionSummary]:
    rows = await repo.list_for_customer(customer_id)
    return [_summary_from_row(row) for row in rows]


@router.delete("/{connection_id}", status_code=204)
async def delete_connection(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: FeatureStoreConnectionRepo = Depends(get_feature_store_connection_repo),
) -> None:
    """Delete a saved connection (#327). Customer-scoped: the repo only deletes a
    row this customer OWNS, and returns False for an unknown id OR another
    tenant's id alike — both map to 404 here so we never confirm a connection's
    existence across customers (the same non-leak posture as ``get``). 204 on a
    successful owned delete. Existing persona builds keep their own records; this
    only removes the credential future builds could reuse."""
    deleted = await repo.delete(connection_id, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="connection not found")


@router.post("/{connection_id}/test", status_code=204)
async def test_connection(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: FeatureStoreConnectionRepo = Depends(get_feature_store_connection_repo),
) -> None:
    """Round-trip a trivial query. 204 on success; on failure a structured
    body {"error_kind", "message"} with 400 for auth/permission, 502 for
    network/unknown."""
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="connection not found")
    store = _store_from_row(row, customer_id)
    try:
        store.test_connection()
    except FeatureStoreConnectionError as exc:
        raise _connection_error(exc) from exc


@router.post("/{connection_id}/preview", response_model=PreviewResponse)
async def preview(
    connection_id: str,
    payload: PreviewRequest,
    customer_id: str = Depends(current_customer_id),
    repo: FeatureStoreConnectionRepo = Depends(get_feature_store_connection_repo),
) -> PreviewResponse:
    """Profile a table (or SQL): total row count + per-column profile over a
    capped sample (default 100 rows)."""
    if not payload.table_fqn and not payload.sql:
        raise HTTPException(status_code=422, detail="provide either table_fqn or sql")
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="connection not found")
    store = _store_from_row(row, customer_id)
    sample_size = max(1, min(payload.sample_size, 100))
    try:
        if payload.table_fqn:
            result = store.preview(payload.table_fqn, sample_size=sample_size)
            return PreviewResponse(row_count=result.row_count, columns=result.columns)
        rows = store.run_query(payload.sql)  # type: ignore[arg-type]
        from sidira_simulator.adapters.feature_stores.snowflake import _profile_columns

        sampled = rows[:sample_size]
        col_names = list(sampled[0].keys()) if sampled else []
        tuples = [tuple(r.get(c) for c in col_names) for r in sampled]
        columns = _profile_columns(col_names, tuples)
        return PreviewResponse(row_count=len(rows), columns=columns)
    except FeatureStoreConnectionError as exc:
        raise _connection_error(exc) from exc


@router.post("/{connection_id}/suggest-mapping", response_model=MappingSuggestion)
async def suggest_mapping(
    connection_id: str,
    payload: SuggestMappingRequest,
    customer_id: str = Depends(current_customer_id),
) -> MappingSuggestion:
    """One deterministic LLM call suggests how the supplied columns map into the
    7 canonical feature groups, with a per-column confidence (high/med/low) and
    an ``unmapped`` bucket. Pure suggestion — stateless w.r.t. the connection,
    so Snowflake is not hit; the user overrides any suggestion in the wizard.
    Returns 502 if the upstream LLM call fails."""
    try:
        return column_mapper.suggest_mapping(payload.columns)
    except ColumnMappingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
