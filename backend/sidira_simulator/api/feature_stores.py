"""Feature-store routes — connection CRUD, connectivity test, schema inspection, mapping suggestions."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sidira_simulator.adapters.feature_stores import ColumnProfile
from sidira_simulator.services.column_mapper import MappingSuggestion

router = APIRouter(prefix="/feature-stores", tags=["feature-stores"])


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


@router.post("", response_model=ConnectionSummary, status_code=201)
async def create_connection(payload: SnowflakeConnectionRequest) -> ConnectionSummary:
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — encrypt + persist connection row, return sanitized summary",
    )


@router.get("", response_model=list[ConnectionSummary])
async def list_connections() -> list[ConnectionSummary]:
    raise HTTPException(status_code=501, detail="Phase 4.5 — read from Postgres scoped to customer")


@router.post("/{connection_id}/test", status_code=204)
async def test_connection(connection_id: str) -> None:
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — decrypt creds, run SnowflakeStore.test_connection, 204 on success",
    )


@router.post("/{connection_id}/preview", response_model=PreviewResponse)
async def preview(connection_id: str, payload: PreviewRequest) -> PreviewResponse:
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — preview a table or SQL with row count + column profile",
    )


@router.post("/{connection_id}/suggest-mapping", response_model=MappingSuggestion)
async def suggest_mapping(connection_id: str, payload: SuggestMappingRequest) -> MappingSuggestion:
    raise HTTPException(
        status_code=501,
        detail="Phase 4.5 — call services/column_mapper.suggest_mapping with the provided columns",
    )
