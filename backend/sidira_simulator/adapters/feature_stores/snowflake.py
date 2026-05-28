"""Snowflake feature-store adapter — MVP implementation.

Holds a single connection per request; never persists creds beyond
the calling function's scope (creds are loaded fresh from the
encrypted_creds blob via credentials.decrypt on each invocation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sidira_simulator.adapters.feature_stores import (
    FeatureStoreConnectionError,
    TablePreview,
)


@dataclass
class SnowflakeCreds:
    """Decrypted Snowflake connection parameters. Lives only in memory."""

    account: str
    user: str
    password: str
    warehouse: str
    role: str
    database: str
    schema: str | None = None


class SnowflakeStore:
    """Implements FeatureStore for Snowflake via snowflake-connector-python."""

    def __init__(self, creds: SnowflakeCreds) -> None:
        self._creds = creds

    def _connect(self):
        try:
            import snowflake.connector  # type: ignore[import-not-found]
        except ImportError as exc:
            raise FeatureStoreConnectionError(
                "snowflake-connector-python is required for Snowflake support."
            ) from exc
        try:
            return snowflake.connector.connect(
                account=self._creds.account,
                user=self._creds.user,
                password=self._creds.password,
                warehouse=self._creds.warehouse,
                role=self._creds.role,
                database=self._creds.database,
                schema=self._creds.schema,
            )
        except Exception as exc:  # snowflake raises many error types
            raise FeatureStoreConnectionError(f"Snowflake connect failed: {exc}") from exc

    def test_connection(self) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        finally:
            conn.close()

    def list_schemas(self) -> list[str]:
        raise NotImplementedError("Phase 4.5 implementation — query INFORMATION_SCHEMA.SCHEMATA")

    def list_tables(self, schema: str) -> list[str]:
        raise NotImplementedError("Phase 4.5 implementation — query INFORMATION_SCHEMA.TABLES")

    def preview(self, table_fqn: str, sample_size: int = 100) -> TablePreview:
        raise NotImplementedError(
            "Phase 4.5 — SELECT COUNT(*) + sample N rows + per-column null/distinct/dtype profile"
        )

    def run_query(self, sql: str) -> list[dict[str, Any]]:
        raise NotImplementedError("Phase 4.5 — guard against non-SELECT statements then execute")
