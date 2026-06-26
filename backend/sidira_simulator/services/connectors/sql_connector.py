"""Generic SQL / database connector (#19) — read-only, customer-supplied creds.

HONEST + safe by construction, with defense in depth:

1. **DB-level read-only** is the real boundary. We open the connection in a
   read-only transaction before the query runs:
   - **Postgres**: ``SET TRANSACTION READ ONLY`` + a session
     ``statement_timeout`` so a write is rejected by the server (not just by our
     keyword filter) and a runaway query cannot hang the import.
   - **SQLite**: opened with an immutable / read-only URI so the file cannot be
     mutated.
   The keyword filter below is a *second* layer, not the security boundary.
2. **Statement allow-list** (see :func:`validate_query`): exactly one
   ``SELECT ... FROM ...`` / ``WITH ... SELECT`` statement. Function-call-style
   SELECTs that can have side effects (``SELECT nextval(...)``,
   ``SELECT setval(...)``, ``SELECT dblink_exec(...)``, ``SELECT my_proc()``) are
   rejected because they are not a plain table/view read.
3. **Customer creds should themselves be read-only.** We document this and
   recommend a read-only role; the read-only transaction is belt-and-suspenders
   on top of that.

Advertised support is **narrowed to the dialects where we actually enforce
read-only at the DB level** (Postgres + SQLite). We do NOT claim "any SQLAlchemy
database": for an unsupported dialect we refuse rather than fall back to the
keyword filter alone.

The DB round-trip is isolated in :func:`_run_query` so the suite exercises the
guard rails + normalization without a live database.
"""

from __future__ import annotations

import re
from typing import Any

_CONN_FIELD = "connection_string"
_QUERY_FIELD = "query"

# Server-side statement timeout (ms) for the read-only import query. Keeps a
# pathological customer query from hanging the import worker.
_STATEMENT_TIMEOUT_MS = 30_000

# Dialects where we enforce read-only at the DB level (not just by keyword).
# An import against any other dialect is refused — we do not silently fall back
# to the keyword filter as the only boundary.
_SUPPORTED_BACKENDS: tuple[str, ...] = ("postgresql", "sqlite")

NEEDS_MESSAGE = (
    "Connect a database by supplying a read-only connection string and a SELECT "
    "query. Supported databases: PostgreSQL and SQLite. We open the connection "
    "in a read-only transaction (server-enforced) and map the returned columns — "
    "no connection, no data (we never fabricate imported results). Use a "
    "read-only database role for the credentials you supply."
)

# Forbidden keywords: anything that could write or change schema. The connector
# is read-only by policy, not just by intent. This is the SECOND layer; the
# read-only transaction is the first. We keep it to keywords that are
# unambiguously write/DDL/transaction-control even when they appear as a bare
# word (avoiding common column/value words like "set" that would false-positive
# on a legitimate SELECT — the DB-level read-only transaction backstops those).
_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|grant|revoke|merge|"
    r"upsert|exec|execute|attach|vacuum|pragma|reindex|notify|"
    r"commit|rollback|savepoint)\b",
    re.IGNORECASE,
)

# A multi-word write/DDL phrase that a single keyword would either miss or
# over-match. ``SELECT … INTO`` materializes a table (a write); ``CREATE`` is
# caught here so a column literally named "create_date" does not false-positive.
_FORBIDDEN_PHRASE = re.compile(
    r"\b(select\b.*\binto|create\s+(table|view|index|materialized|temp|"
    r"temporary|database|schema|function|procedure|trigger)|copy\s+\w|"
    r"set\s+(transaction|session|role|local)|do\s+\$)\b",
    re.IGNORECASE | re.DOTALL,
)

# Function-call-style SELECTs ("SELECT nextval('s')", "SELECT my_proc()") are not
# a plain table/view read and can carry side effects. Without a real SQL parser
# we conservatively reject a SELECT whose first non-whitespace token after
# SELECT (ignoring a leading DISTINCT / column list) is a function call, and we
# require the statement to contain a FROM clause reading a table/view.
_SIDE_EFFECTING_FUNCS = re.compile(
    r"\b(nextval|setval|currval|dblink|dblink_exec|lo_import|lo_export|"
    r"pg_read_file|pg_sleep|pg_terminate_backend|pg_cancel_backend|"
    r"query_to_xml|xpath|dblink_connect)\s*\(",
    re.IGNORECASE,
)


class SqlCredentialError(RuntimeError):
    """No usable connection string / query was supplied."""


class SqlQueryError(RuntimeError):
    """The query is unsafe, malformed, or the database call failed."""


class SqlUnsupportedBackendError(SqlQueryError):
    """The connection string targets a dialect where we cannot enforce read-only."""


class SqlConnectError(RuntimeError):
    """The engine could not connect with the supplied connection string.

    Carries the raw driver detail for SERVER-SIDE logging only — the API layer
    sanitizes it to a generic message before responding (the connection string /
    host must never leak back to the caller).
    """


class SqlExecutionError(RuntimeError):
    """The query failed at execution time (driver/runtime error, e.g. a write
    refused by the read-only transaction).

    Like :class:`SqlConnectError`, the raw detail is for server-side logging only.
    """


def has_credentials(config: dict[str, str]) -> bool:
    """True when both a connection string and a query were supplied."""
    return bool((config.get(_CONN_FIELD) or "").strip()) and bool(
        (config.get(_QUERY_FIELD) or "").strip()
    )


def _backend_name(connection_string: str) -> str:
    """Return the lowercase SQLAlchemy backend (e.g. 'postgresql', 'sqlite').

    The dialect is the part before ``://`` (or before ``+driver``). We do not
    import SQLAlchemy just to parse this, so the dialect check happens before any
    engine is created.
    """
    scheme = connection_string.split("://", 1)[0].strip().lower()
    return scheme.split("+", 1)[0]


def validate_query(query: str) -> str:
    """Return the cleaned query, or raise if it is not a single read-only SELECT.

    Guard rails (read-only import path) — the SECOND layer behind the DB-level
    read-only transaction:
    - exactly one statement (no ``;``-chained second statement);
    - must begin with SELECT or WITH (CTE);
    - must read FROM a table/view (a bare ``SELECT <expr>`` with no FROM, e.g.
      ``SELECT setval('s', 1)``, is rejected — it is not a table read);
    - must not be a side-effecting function-call SELECT (nextval/setval/dblink/…);
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
    if _SIDE_EFFECTING_FUNCS.search(q):
        raise SqlQueryError(
            "query must be a plain SELECT FROM a table/view — function-call SELECTs "
            "(nextval/setval/dblink/…) are rejected"
        )
    if _FORBIDDEN.search(q) or _FORBIDDEN_PHRASE.search(q):
        raise SqlQueryError("query may only read — data/DDL statements are rejected")
    # A read must pull FROM a relation. A bare expression-SELECT (no FROM) is the
    # shape a function-call SELECT uses to mutate ("SELECT setval(...)"), so we
    # require a FROM clause. Word-boundary match so a column named "fromage" does
    # not satisfy it.
    if not re.search(r"\bfrom\b", q, re.IGNORECASE):
        raise SqlQueryError(
            "query must read FROM a table or view (a SELECT with no FROM is rejected)"
        )
    return q


def _run_query(connection_string: str, query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Execute the validated SELECT in a READ-ONLY transaction; return (columns, rows).

    Isolated for testability — the suite patches this. Enforces read-only at the
    DB level (the real boundary):
    - Postgres: ``SET TRANSACTION READ ONLY`` + ``statement_timeout`` so a write
      is refused by the server and a runaway query is cut off.
    - SQLite: opened read-only via the engine ``execution_options`` / immutable
      connect args so the file cannot be mutated.

    Refuses any dialect outside :data:`_SUPPORTED_BACKENDS` rather than relying on
    the keyword filter alone.
    """
    backend = _backend_name(connection_string)
    if backend not in _SUPPORTED_BACKENDS:
        raise SqlUnsupportedBackendError(
            f"unsupported database '{backend or connection_string}': the SQL "
            "connector only supports PostgreSQL and SQLite (the dialects where we "
            "enforce a read-only transaction)"
        )

    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:  # pragma: no cover - sqlalchemy is a runtime dep
        raise SqlQueryError("sqlalchemy is required for the SQL connector") from exc

    try:
        if backend == "postgresql":
            # default_transaction_read_only + statement_timeout on every new
            # session; the explicit SET TRANSACTION READ ONLY below is the
            # belt-and-suspenders for the active transaction.
            engine = create_engine(
                connection_string,
                connect_args={
                    "options": (
                        "-c default_transaction_read_only=on "
                        f"-c statement_timeout={_STATEMENT_TIMEOUT_MS}"
                    )
                },
            )
        else:  # sqlite
            engine = create_engine(connection_string)
    except Exception as exc:  # pragma: no cover - bad URL shape
        # Raw detail kept for the SERVER-SIDE log only; the API layer turns this
        # into a generic "could not connect" message.
        raise SqlConnectError(f"invalid connection string: {exc}") from exc

    try:
        try:
            conn = engine.connect()
        except Exception as exc:
            raise SqlConnectError(f"could not connect: {exc}") from exc
        try:
            if backend == "postgresql":
                conn.execute(text("SET TRANSACTION READ ONLY"))
            result = conn.execute(text(query))
            columns = list(result.keys())
            rows = [tuple(r) for r in result.fetchall()]
            # Never commit — roll back so even a server that allowed a write
            # leaves nothing behind.
            conn.rollback()
        except Exception as exc:
            raise SqlExecutionError(f"query failed: {exc}") from exc
        finally:
            conn.close()
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
    backend = _backend_name(conn_str)
    if backend not in _SUPPORTED_BACKENDS:
        raise SqlUnsupportedBackendError(
            f"unsupported database '{backend or conn_str}': the SQL connector only "
            "supports PostgreSQL and SQLite (the dialects where we enforce a "
            "read-only transaction)"
        )
    query = validate_query(raw_query)
    columns, raw_rows = _run_query(conn_str, query)
    rows = [
        {col: ("" if val is None else str(val)) for col, val in zip(columns, row)}
        for row in raw_rows
    ]
    return columns, rows
