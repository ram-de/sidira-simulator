"""Generic SQL / database connector (#19) — read-only, customer-supplied creds.

HONEST + safe by construction:
- No connection string => ``needs_credentials`` state, no data.
- The query is constrained to a single read-only ``SELECT`` (statement allow-list
  + a refusal of multi-statement / DML / DDL) so the connector cannot mutate the
  customer's database — it is an import path, not a migration tool.
- Rows the query returns are normalized to ``{column -> value}`` strings and
  handed to the shared field mapping (:mod:`mapping`). The customer's confirmed
  FieldMapping does the firewall crossing.

The DB round-trip is isolated in :func:`_run_query` so the suite exercises the
guard rails + normalization without a live database.
"""

from __future__ import annotations

import re
from typing import Any

_CONN_FIELD = "connection_string"
_QUERY_FIELD = "query"

NEEDS_MESSAGE = (
    "Connect a database by supplying a read-only connection string and a SELECT "
    "query. We run the query read-only and map the returned columns — no "
    "connection, no data (we never fabricate imported results)."
)

# Forbidden leading keywords: anything that could write or change schema. The
# connector is read-only by policy, not just by intent.
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|merge|"
    r"replace|call|exec|execute|attach|copy|vacuum|pragma)\b",
    re.IGNORECASE,
)


class SqlCredentialError(RuntimeError):
    """No usable connection string / query was supplied."""


class SqlQueryError(RuntimeError):
    """The query is unsafe, malformed, or the database call failed."""


def has_credentials(config: dict[str, str]) -> bool:
    """True when both a connection string and a query were supplied."""
    return bool((config.get(_CONN_FIELD) or "").strip()) and bool(
        (config.get(_QUERY_FIELD) or "").strip()
    )


def validate_query(query: str) -> str:
    """Return the cleaned query, or raise if it is not a single read-only SELECT.

    Guard rails (read-only import path):
    - exactly one statement (no ``;``-chained second statement);
    - must begin with SELECT or WITH (CTE);
    - must not contain any data/DDL keyword.
    """
    q = query.strip().rstrip(";").strip()
    if not q:
        raise SqlQueryError("query is empty")
    if ";" in q:
        raise SqlQueryError("only a single SELECT statement is allowed (no ';' chaining)")
    head = q.split(None, 1)[0].lower()
    if head not in ("select", "with"):
        raise SqlQueryError("query must be a read-only SELECT (or a WITH … SELECT)")
    if _FORBIDDEN.search(q):
        raise SqlQueryError("query may only read — data/DDL statements are rejected")
    return q


def _run_query(connection_string: str, query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Execute the validated SELECT read-only; return (columns, rows).

    Isolated for testability — the suite patches this. Uses SQLAlchemy Core so
    any SQLAlchemy-supported database (Postgres, MySQL, SQLite, …) works from one
    connection string.
    """
    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:  # pragma: no cover - sqlalchemy is a runtime dep
        raise SqlQueryError("sqlalchemy is required for the SQL connector") from exc

    try:
        engine = create_engine(connection_string)
    except Exception as exc:  # pragma: no cover - bad URL shape
        raise SqlQueryError(f"invalid connection string: {exc}") from exc
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = [tuple(r) for r in result.fetchall()]
    except Exception as exc:
        raise SqlQueryError(f"query failed: {exc}") from exc
    finally:
        engine.dispose()
    return columns, rows


def fetch_rows(config: dict[str, str]) -> tuple[list[str], list[dict[str, str]]]:
    """Run the customer's SELECT read-only and return (columns, normalized rows).

    Raises :class:`SqlCredentialError` when creds are missing — the caller turns
    that into a ``needs_credentials`` result, never a fabricated import.
    """
    conn_str = (config.get(_CONN_FIELD) or "").strip()
    raw_query = config.get(_QUERY_FIELD) or ""
    if not conn_str or not raw_query.strip():
        raise SqlCredentialError(NEEDS_MESSAGE)
    query = validate_query(raw_query)
    columns, raw_rows = _run_query(conn_str, query)
    rows = [
        {col: ("" if val is None else str(val)) for col, val in zip(columns, row)}
        for row in raw_rows
    ]
    return columns, rows
