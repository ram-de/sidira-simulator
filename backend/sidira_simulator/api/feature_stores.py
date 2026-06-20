"""Feature-store routes — connection CRUD, connectivity test, schema inspection, mapping suggestions."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Literal
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
from sidira_simulator.services import column_mapper, document_extractor
from sidira_simulator.services.column_mapper import ColumnMappingError, MappingSuggestion
from sidira_simulator.services.document_extractor import (
    DocumentExtractionError,
    EntityDocument,
    ExtractionSchema,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feature-stores", tags=["feature-stores"])


async def _record_test_result_best_effort(
    repo: FeatureStoreConnectionRepo,
    connection_id: str,
    customer_id: str,
    *,
    status: str,
    tested_at: datetime,
    error_kind: str | None,
    error_message: str | None,
) -> None:
    """Persist a connectivity-test outcome (#328) WITHOUT ever changing the
    route's HTTP contract. The connectivity result (204 / structured error) has
    already been determined by the time this runs; the persisted health is
    metadata. A write failure here (DB hiccup) must not become a 500 that masks
    the real connectivity verdict — so we log and swallow."""
    try:
        await repo.record_test_result(
            connection_id,
            customer_id,
            status=status,
            tested_at=tested_at,
            error_kind=error_kind,
            error_message=error_message,
        )
    except Exception:  # noqa: BLE001 — best-effort metadata, never fail the route
        logger.warning(
            "failed to persist test result for connection %s", connection_id, exc_info=True
        )

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
    # Per-connection health (#328) — the persisted outcome of the last
    # connectivity test, so the saved-connections register (#327) can show a
    # last-known state in words (OK · TESTED … / FAILED · AUTH / UNTESTED). All
    # null on a never-tested row. ``last_test_status`` is 'ok' | 'failed'.
    last_tested_at: datetime | None = None
    last_test_status: Literal["ok", "failed"] | None = None
    last_error_kind: str | None = None
    last_error_message: str | None = None


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
        # Health fields (#328). Surfaced read-only; never include the password.
        last_tested_at=row.get("last_tested_at"),
        last_test_status=row.get("last_test_status"),
        last_error_kind=row.get("last_error_kind"),
        last_error_message=row.get("last_error_message"),
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
    network/unknown.

    Either outcome is PERSISTED to the row (#328) so the saved-connections
    register can show a last-known state without re-testing: on success
    last_test_status='ok' with the error fields cleared; on failure 'failed'
    with the classified error_kind/message. record_test_result is customer-
    scoped — it only ever updates THIS customer's owned row. The persisted
    state is best-effort metadata: the HTTP contract (204 / structured error)
    is unchanged and never gated on the write succeeding."""
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="connection not found")
    store = _store_from_row(row, customer_id)
    tested_at = datetime.now(timezone.utc)
    try:
        store.test_connection()
    except FeatureStoreConnectionError as exc:
        kind = getattr(exc, "kind", "unknown")
        await _record_test_result_best_effort(
            repo,
            connection_id,
            customer_id,
            status="failed",
            tested_at=tested_at,
            error_kind=kind,
            error_message=str(exc),
        )
        raise _connection_error(exc) from exc
    await _record_test_result_best_effort(
        repo,
        connection_id,
        customer_id,
        status="ok",
        tested_at=tested_at,
        error_kind=None,
        error_message=None,
    )


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


@router.post("/suggest-mapping", response_model=MappingSuggestion)
async def suggest_mapping_for_columns(
    payload: SuggestMappingRequest,
    customer_id: str = Depends(current_customer_id),
) -> MappingSuggestion:
    """Connection-agnostic column mapping — same stateless suggestion as the
    ``/{connection_id}/suggest-mapping`` route, but for columns that don't come
    from a saved connection (the #3 document feeder, where the documents ARE the
    source). The suggestion never touched the connection anyway. Runs the blocking
    LLM call off the event loop. Returns 502 if the upstream LLM call fails."""
    try:
        return await asyncio.to_thread(column_mapper.suggest_mapping, payload.columns)
    except ColumnMappingError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


#: Guard rails on a single extract-documents request: extraction fans out into
#: one blocking LLM call per non-empty document, so an unbounded upload would tie
#: up the threadpool and run up provider cost. Reject oversized requests up front.
_MAX_DOCUMENTS = 500
_MAX_TOTAL_TEXT_CHARS = 2_000_000
#: One document = one prompt = one chat call, so a single oversized document
#: would blow the provider context window and turn into a slow 502. Cap each
#: document to a conservative model-safe size (~50k tokens). Chunking large
#: corpora per entity is a follow-up; for now an over-long doc is rejected.
_MAX_DOCUMENT_CHARS = 200_000
#: The schema is repeated in every per-document prompt and scaffolds every row,
#: so an oversized schema inflates prompt size and cost even under the text caps.
#: Bound the field count and the total schema text (names + descriptions).
_MAX_SCHEMA_FIELDS = 100
_MAX_SCHEMA_TEXT_CHARS = 20_000


class ExtractDocumentsRequest(BaseModel):
    documents: list[EntityDocument]
    extraction_schema: ExtractionSchema


class ExtractDocumentsResponse(BaseModel):
    row_count: int
    columns: list[ColumnProfile]
    rows: list[dict[str, Any]]


@router.post("/extract-documents", response_model=ExtractDocumentsResponse)
async def extract_documents(
    payload: ExtractDocumentsRequest,
    customer_id: str = Depends(current_customer_id),
) -> ExtractDocumentsResponse:
    """#3 doc feeder: extract a bounded, fixed-schema feature row per entity from
    its documents, then profile the columns into the same shape the Snowflake
    preview emits — so doc-fed columns flow straight into the wizard's Map step.

    Connection-agnostic (like suggest-mapping); the documents ARE the source.
    The extraction is closed to ``extraction_schema`` (no model-invented columns)
    and extractive (absence ⇒ null). 400 on a malformed schema (caller error);
    502 if the upstream extraction LLM fails; 413 if the request exceeds the
    document-count / total-text guard rails."""
    fields = payload.extraction_schema.fields
    if len(fields) > _MAX_SCHEMA_FIELDS:
        raise HTTPException(
            status_code=413,
            detail=f"extraction schema has too many fields ({len(fields)}); max {_MAX_SCHEMA_FIELDS}",
        )
    schema_chars = sum(len(f.name) + len(f.description) for f in fields)
    if schema_chars > _MAX_SCHEMA_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=(
                f"extraction schema text too large ({schema_chars} chars); "
                f"max {_MAX_SCHEMA_TEXT_CHARS} — it is repeated in every per-document prompt"
            ),
        )
    if len(payload.documents) > _MAX_DOCUMENTS:
        raise HTTPException(
            status_code=413,
            detail=f"too many documents ({len(payload.documents)}); max {_MAX_DOCUMENTS}",
        )
    for doc in payload.documents:
        if len(doc.text) > _MAX_DOCUMENT_CHARS:
            raise HTTPException(
                status_code=413,
                detail=(
                    f"document {doc.entity_id!r} too large ({len(doc.text)} chars); "
                    f"max {_MAX_DOCUMENT_CHARS} per document — a single document is sent "
                    f"in one extraction call and would exceed the provider context window"
                ),
            )
    total_chars = sum(len(d.text) for d in payload.documents)
    if total_chars > _MAX_TOTAL_TEXT_CHARS:
        raise HTTPException(
            status_code=413,
            detail=f"document text too large ({total_chars} chars); max {_MAX_TOTAL_TEXT_CHARS}",
        )
    try:
        # Extraction is a synchronous loop of blocking chat_json calls (one per
        # entity) — run it off the event loop so a slow/multi-doc request can't
        # stall the worker (matches the asyncio.to_thread idiom used for the other
        # sync chat-client calls in this codebase).
        rows = await asyncio.to_thread(
            document_extractor.extract_feature_rows,
            payload.documents,
            payload.extraction_schema,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DocumentExtractionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    row_count, columns = document_extractor.profile_feature_rows(
        rows, payload.extraction_schema
    )
    return ExtractDocumentsResponse(row_count=row_count, columns=columns, rows=rows)
