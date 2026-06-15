"""Snowflake feature-store adapter — MVP implementation.

Holds a single connection per request; never persists creds beyond
the calling function's scope (creds are loaded fresh from the
encrypted_creds blob via credentials.decrypt on each invocation).

Failures are classified into one of ``auth`` / ``permission`` / ``network`` /
``unknown`` (carried on ``FeatureStoreConnectionError.kind``) so the API can
return a structured, actionable error to the connection wizard.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sidira_simulator.adapters.feature_stores import (
    ColumnProfile,
    FeatureStoreConnectionError,
    TablePreview,
)

ErrorKind = Literal["auth", "permission", "network", "unknown"]


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


def _classify_error(exc: Exception) -> ErrorKind:
    """Map a snowflake-connector exception to a coarse, actionable kind.

    snowflake.connector raises a small family of error types; we also inspect
    the SQLSTATE / errno / message because the connector overloads
    ``ProgrammingError`` for both auth (incorrect username/password) and
    permission (insufficient privilege) failures.
    """
    try:
        from snowflake.connector import errors as sf_errors  # type: ignore[import-not-found]
    except ImportError:
        sf_errors = None  # type: ignore[assignment]

    errno = getattr(exc, "errno", None)
    sqlstate = getattr(exc, "sqlstate", None) or ""
    msg = str(getattr(exc, "msg", None) or exc).lower()

    # Snowflake auth failures: errno 250001 (incorrect username/password),
    # SQLSTATE 08001/28000 (connection/auth rejection).
    if errno in (250001, 251005, 251006) or sqlstate in ("08001", "28000"):
        return "auth"
    if any(s in msg for s in ("incorrect username or password", "authentication", "invalid login")):
        return "auth"

    # Insufficient privilege / object access denied.
    if errno in (3001, 3011, 90105) or sqlstate in ("42501", "42000"):
        return "permission"
    if any(
        s in msg
        for s in (
            "insufficient privileg",
            "not authorized",
            "access denied",
            "does not exist or not authorized",
        )
    ):
        return "permission"

    # Network / operational: name resolution, timeouts, unreachable host.
    if sf_errors is not None and isinstance(exc, sf_errors.OperationalError):
        return "network"
    if any(
        s in msg
        for s in (
            "could not connect",
            "name or service not known",
            "timed out",
            "timeout",
            "network",
            "connection refused",
            "failed to connect",
            "getaddrinfo",
        )
    ):
        return "network"

    # Programming errors that are not clearly auth/permission tend to be
    # malformed SQL or missing objects — still actionable, but not network.
    if sf_errors is not None and isinstance(exc, sf_errors.ProgrammingError):
        return "permission"

    return "unknown"


def _wrap(exc: Exception, prefix: str) -> FeatureStoreConnectionError:
    """Build a classified FeatureStoreConnectionError from a raw exception."""
    kind = _classify_error(exc)
    err = FeatureStoreConnectionError(f"{prefix}: {exc}")
    err.kind = kind
    return err


class SnowflakeStore:
    """Implements FeatureStore for Snowflake via snowflake-connector-python."""

    def __init__(self, creds: SnowflakeCreds) -> None:
        self._creds = creds

    def _connect(self):
        try:
            import snowflake.connector  # type: ignore[import-not-found]
        except ImportError as exc:
            err = FeatureStoreConnectionError(
                "snowflake-connector-python is required for Snowflake support."
            )
            err.kind = "unknown"
            raise err from exc
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
            raise _wrap(exc, "Snowflake connect failed") from exc

    def test_connection(self) -> None:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
        except Exception as exc:
            raise _wrap(exc, "Snowflake test query failed") from exc
        finally:
            conn.close()

    def list_schemas(self) -> list[str]:
        rows = self.run_query(
            "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA ORDER BY SCHEMA_NAME"
        )
        return [str(r["SCHEMA_NAME"]) for r in rows if r.get("SCHEMA_NAME") is not None]

    def list_tables(self, schema: str) -> list[str]:
        rows = self.run_query(
            "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES "
            f"WHERE TABLE_SCHEMA = '{_quote(schema)}' ORDER BY TABLE_NAME"
        )
        return [str(r["TABLE_NAME"]) for r in rows if r.get("TABLE_NAME") is not None]

    def preview(self, table_fqn: str, sample_size: int = 100) -> TablePreview:
        """Inspect a table: total row count + a sample of up to ``sample_size``
        rows, plus a per-column profile (dtype, non-null count, null fraction,
        best-effort distinct count + sample values)."""
        conn = self._connect()
        try:
            cur = conn.cursor()
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table_fqn}")
                row_count = int(cur.fetchone()[0])

                cur.execute(f"SELECT * FROM {table_fqn} LIMIT {int(sample_size)}")
                col_names = [d[0] for d in cur.description]
                rows = cur.fetchall()
            finally:
                cur.close()
        except Exception as exc:
            raise _wrap(exc, f"Snowflake preview of {table_fqn} failed") from exc
        finally:
            conn.close()

        columns = _profile_columns(col_names, rows)
        return TablePreview(table_fqn=table_fqn, row_count=row_count, columns=columns)

    def run_query(self, sql: str) -> list[dict[str, Any]]:
        """Execute a read-only SELECT and return rows as dicts. Rejects any
        statement that is not a bare SELECT to keep this a read path."""
        stripped = sql.strip().rstrip(";").strip()
        if not stripped.lower().startswith(("select", "with", "show")):
            err = FeatureStoreConnectionError(
                "Only read-only SELECT/WITH/SHOW statements are permitted."
            )
            err.kind = "permission"
            raise err
        conn = self._connect()
        try:
            cur = conn.cursor()
            try:
                cur.execute(stripped)
                col_names = [d[0] for d in cur.description]
                rows = cur.fetchall()
            finally:
                cur.close()
        except Exception as exc:
            raise _wrap(exc, "Snowflake query failed") from exc
        finally:
            conn.close()
        return [dict(zip(col_names, row)) for row in rows]


def _quote(value: str) -> str:
    """Escape single quotes for inlining an identifier into a SQL string
    literal (INFORMATION_SCHEMA lookups only — never user free-text SQL)."""
    return value.replace("'", "''")


def _profile_columns(col_names: list[str], rows: list[tuple[Any, ...]]) -> list[ColumnProfile]:
    """Build a per-column profile from an already-fetched sample of rows.

    dtype/distinct/sample are derived from the sample (best-effort); null
    fraction is over the sampled rows. With no rows we still emit one profile
    per column so the wizard can render the schema.
    """
    n = len(rows)
    profiles: list[ColumnProfile] = []
    for idx, name in enumerate(col_names):
        values = [row[idx] for row in rows]
        non_null = [v for v in values if v is not None]
        non_null_count = len(non_null)
        null_fraction = round(1 - (non_null_count / n), 4) if n else 0.0
        dtype = type(non_null[0]).__name__ if non_null else "unknown"
        try:
            distinct_count: int | None = len({_hashable(v) for v in non_null})
        except TypeError:
            distinct_count = None
        sample_values = list(dict.fromkeys(_hashable(v) for v in non_null))[:5] if non_null else []
        profiles.append(
            ColumnProfile(
                name=str(name),
                dtype=dtype,
                non_null_count=non_null_count,
                null_fraction=null_fraction,
                distinct_count=distinct_count,
                sample_values=sample_values or None,
            )
        )
    return profiles


def _hashable(value: Any) -> Any:
    """Coerce unhashable / non-JSON values to a stable representation for
    distinct counting and sample display."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
