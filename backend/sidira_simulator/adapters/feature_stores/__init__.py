"""Feature store adapters — pluggable interface for connecting to customer data.

MVP: Snowflake only. Phase 2+: BigQuery, Databricks, Redshift, CSV upload.
All implementations satisfy the `FeatureStore` Protocol below.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class ColumnProfile:
    """Lightweight column-level summary returned by `profile()`."""

    name: str
    dtype: str
    non_null_count: int
    null_fraction: float
    distinct_count: int | None = None
    sample_values: list[Any] | None = None


@dataclass
class TablePreview:
    """Result of a connectivity + lightweight inspection check."""

    table_fqn: str
    row_count: int
    columns: list[ColumnProfile]


class FeatureStoreConnectionError(RuntimeError):
    """Raised when a feature store cannot be reached or authenticated."""


class FeatureStore(Protocol):
    """Pluggable interface satisfied by every feature-store adapter."""

    def test_connection(self) -> None:
        """Round-trip a trivial query. Raises FeatureStoreConnectionError on failure."""

    def list_schemas(self) -> list[str]: ...

    def list_tables(self, schema: str) -> list[str]: ...

    def preview(self, table_fqn: str, sample_size: int = 100) -> TablePreview:
        """Inspect a table: row count + per-column profile."""

    def run_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute arbitrary SELECT — used for SQL-as-source path in the wizard."""
