"""SQL / PostgreSQL connector (#19) — read-only, customer-supplied creds.

HONEST + safe by construction, with defense in depth:

THE SECURITY BOUNDARY IS THE DATABASE, NOT THIS MODULE'S SYNTAX CHECK.

1. **DB-level read-only is the real, sole security boundary.** We open the
   connection in a read-only transaction before the query runs (**PostgreSQL
   only**): ``default_transaction_read_only=on`` + ``SET TRANSACTION READ ONLY``
   + a session ``statement_timeout``, and the customer is required to supply a
   read-only database role. In a read-only transaction the *server* refuses ANY
   write — including writes smuggled through a function call (``setval()``,
   ``nextval()``, ``dblink_exec()``, ``lo_import()``, a writing stored proc, …):
   those raise ``ERROR: cannot execute ... in a read-only transaction``. So even
   a query that slips past the syntactic guard below cannot mutate data. A
   runaway query is cut off by ``statement_timeout``.
2. **The syntactic allow-list (:func:`validate_query`) is defense-in-depth and
   UX — NOT the security boundary.** It restricts accepted SQL to a plain
   ``SELECT ... FROM <table/view>`` shape so customers get a clear, early error
   instead of a confusing server-side read-only failure, and so an obviously
   abusive query is turned away before we even open a connection. It is
   conservative (reject-on-doubt) but it is *not* what makes the connector safe;
   the read-only transaction is. We rely on a real SQL parser only if one is a
   project dependency — none is (``sqlglot``/``sqlparse`` are absent and we will
   not pull in a heavy new dependency just to harden a non-boundary check), so
   this guard is a careful lexical scan, accepted as best-effort.
3. **Customer creds must themselves be read-only.** We document this and require
   a read-only role; the read-only transaction is belt-and-suspenders on top.

Advertised support is **PostgreSQL only** — the single dialect where we can
actually enforce read-only at the DB level. We do NOT claim "any SQLAlchemy
database" and we do not support SQLite (SQLAlchemy cannot open a SQLite file
read-only via a plain connection string, so we cannot honestly advertise it as
read-only): for any other dialect we refuse rather than fall back to the keyword
filter alone, and we never echo connection-string text back to the caller.

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
# PostgreSQL is the only dialect where a plain connection string lets us open a
# server-enforced read-only transaction; an import against any other dialect is
# refused — we do not silently fall back to the keyword filter as the only
# boundary, and we never reflect the supplied connection string back.
_SUPPORTED_BACKENDS: tuple[str, ...] = ("postgresql",)

# Customer-safe message for an unsupported / unparseable backend. It NEVER
# includes any connection-string-derived text (an ODBC "Pwd=..." string has no
# scheme and would otherwise be echoed back) — the detail is logged server-side.
UNSUPPORTED_BACKEND_MESSAGE = (
    "Unsupported database — the SQL connector supports PostgreSQL only (the "
    "dialect where we enforce a server-side read-only transaction). Supply a "
    "PostgreSQL (postgresql://) connection string."
)
# Backwards-compatible private alias (referenced within this module).
_UNSUPPORTED_BACKEND_MESSAGE = UNSUPPORTED_BACKEND_MESSAGE

NEEDS_MESSAGE = (
    "Connect a database by supplying a read-only PostgreSQL connection string "
    "and a SELECT query. Supported database: PostgreSQL only. The security "
    "boundary is the database itself: we run your query inside a server-enforced "
    "read-only transaction (default_transaction_read_only + SET TRANSACTION READ "
    "ONLY + statement_timeout) and you must supply a read-only database role, so "
    "the server refuses every write — including writes hidden in a function call. "
    "We also pre-screen the query to a plain SELECT … FROM <table/view> as "
    "defense-in-depth (and for a clear early error), but that check is not the "
    "boundary. We map the returned columns — no connection, no data (we never "
    "fabricate imported results)."
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
#
# Explicitly named volatile / side-effecting families: sequence mutation
# (nextval/setval/currval), cross-DB calls (dblink*), large-object I/O (lo_*),
# advisory locks (pg_advisory*), and the broad ``pg_*`` admin/introspection
# surface (server-side file access, query cancellation, sleeps, etc.). Any
# ``pg_<name>(`` call is rejected so we don't have to chase the catalog one
# function at a time.
_SIDE_EFFECTING_FUNCS = re.compile(
    r"\b(nextval|setval|currval|dblink\w*|lo_\w+|"
    r"pg_advisory\w*|pg_\w+|query_to_xml|xpath)\s*\(",
    re.IGNORECASE,
)

# A plain table/view read projects column references (and a small allow-list of
# pure read aggregates), then reads FROM a relation. ANY other function/proc call
# ANYWHERE in the select-list — first position OR a later comma-separated item OR
# a set-returning function — makes the statement a function invocation, not a
# table read, so we reject it. The previous version only inspected the FIRST
# select-list item, which let ``SELECT col, evil_func() FROM t`` and
# set-returning functions slip past. We now scan EVERY top-level projection item.
#
# Matches a function call: an identifier (optionally schema-qualified) immediately
# followed by "(". Used to find every call token in the projection.
_FUNC_CALL_TOKEN = re.compile(r"([a-z_][a-z0-9_.]*)\s*\(", re.IGNORECASE)

# Aggregates / common pure read functions that may legitimately appear in a
# select-list of a table read ("SELECT count(*), round(avg(x),2) FROM t"). These
# are read-only by nature. ANY function call NOT in this set is rejected wherever
# it appears in the projection. The core read-aggregate allow-list codex named is
# count/sum/avg/min/max/coalesce/cast/round; we also permit a few obviously pure
# scalar helpers that commonly wrap a projected column.
_ALLOWED_PROJECTION_FUNCS = frozenset(
    {"count", "sum", "avg", "min", "max", "coalesce", "cast", "round",
     "lower", "upper", "length", "abs", "date_trunc", "extract", "to_char",
     "nullif"}
)

# A CTE / WITH query and a subquery in the projection are rejected outright: they
# open arbitrary nested SELECTs (and set-returning / lateral function calls) that
# this lexical guard cannot soundly walk. Rejecting them keeps the accepted shape
# to a single, flat ``SELECT <columns/aggregates> FROM <relation>``. (The
# read-only transaction would still contain any read smuggled through them — this
# is the conservative, reject-on-doubt posture, not the security boundary.)
_WITH_CTE = re.compile(r"^\s*with\b", re.IGNORECASE)
_SUBQUERY_SELECT = re.compile(r"\(\s*select\b", re.IGNORECASE)


def _split_top_level_commas(s: str) -> list[str]:
    """Split a select-list on commas that are NOT inside parentheses.

    ``round(avg(x), 2), name`` -> ``['round(avg(x), 2)', ' name']`` — the comma
    inside ``round(...)`` is not a projection separator. Conservative: unbalanced
    input still returns the best-effort split (the caller treats parens
    pessimistically elsewhere).
    """
    items: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(s):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            items.append(s[start:i])
            start = i + 1
    items.append(s[start:])
    return items


def _reject_disallowed_projection_funcs(select_list: str) -> None:
    """Raise if any non-allow-listed function/proc call appears in the projection.

    Scans EVERY top-level comma-separated projection item (not just the first) and
    every function-call token within it. A call whose bare (un-qualified) name is
    not in :data:`_ALLOWED_PROJECTION_FUNCS` is rejected — this covers a function
    in a later select-list position (``SELECT col, evil_func() FROM t``),
    set-returning functions (``SELECT generate_series(1,10) FROM t``), and proc
    invocations, regardless of where they sit in the list.
    """
    for item in _split_top_level_commas(select_list):
        for match in _FUNC_CALL_TOKEN.finditer(item):
            fn = match.group(1).rsplit(".", 1)[-1].lower()
            if fn not in _ALLOWED_PROJECTION_FUNCS:
                raise SqlQueryError(
                    "query must be a plain SELECT FROM a table/view — only column "
                    "references and read aggregates "
                    "(count/sum/avg/min/max/coalesce/cast/round) are allowed in "
                    "the select-list; any other function/procedure call is rejected"
                )


class SqlCredentialError(RuntimeError):
    """No usable connection string / query was supplied."""


class SqlQueryError(RuntimeError):
    """The query is unsafe, malformed, or the database call failed."""


class SqlUnsupportedBackendError(SqlQueryError):
    """The connection string targets a dialect where we cannot enforce read-only.

    Its message is the generic :data:`_UNSUPPORTED_BACKEND_MESSAGE` — it NEVER
    contains connection-string-derived text (a no-scheme ODBC ``Pwd=...`` string
    must not be reflected back to the caller).
    """


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


def is_supported_backend(connection_string: str) -> bool:
    """True when the connection string targets a backend we can run read-only.

    Used by the validate path so an unsupported dialect is reported as not-ready
    up front (instead of passing validation and being refused at import time). It
    never reflects the connection string — the caller surfaces a generic message.
    """
    return _backend_name(connection_string) in _SUPPORTED_BACKENDS


def validate_query(query: str) -> str:
    """Return the cleaned query, or raise if it is not a single read-only SELECT.

    DEFENSE-IN-DEPTH / UX — **NOT the security boundary.** The security boundary
    is the server-side read-only transaction + the customer's read-only role (see
    the module docstring and :func:`_run_query`); that refuses every write,
    including writes hidden in a function call, even if a query slips past this
    check. This guard turns away obviously-not-a-read queries early with a clear
    error, and is deliberately conservative (reject-on-doubt). It is a careful
    lexical scan because no SQL parser is a project dependency.

    We restrict accepted SQL to a single, flat ``SELECT <cols/aggregates> FROM
    <table/view>`` shape:
    - exactly one statement (no ``;``-chained second statement);
    - must begin with SELECT — ``WITH`` / CTEs are rejected (they open arbitrary
      nested SELECTs a lexical scan cannot soundly walk), as are ``CALL`` / ``DO``
      / any other statement form;
    - must read FROM a table/view (a bare ``SELECT <expr>`` with no FROM, e.g.
      ``SELECT setval('s', 1)``, is rejected — it is not a table read);
    - NO subquery in the projection (``SELECT (SELECT …) FROM t`` is rejected);
    - the ENTIRE select-list — every comma-separated projection item, not just
      the first — must contain only column references + the read-aggregate
      allow-list (count/sum/avg/min/max/coalesce/cast/round); ANY other
      function/proc call anywhere in the projection (a later position, a
      set-returning function, a nested call) is rejected;
    - must not invoke a side-effecting / volatile function anywhere
      (nextval/setval/dblink*/lo_*/pg_*/advisory-lock funcs/…);
    - must not contain any data/DDL keyword.
    """
    q = query.strip().rstrip(";").strip()
    if not q:
        raise SqlQueryError("query is empty")
    if ";" in q:
        raise SqlQueryError("only a single SELECT statement is allowed (no ';' chaining)")
    head = q.split(None, 1)[0].lower()
    if head == "with" or _WITH_CTE.match(q):
        raise SqlQueryError(
            "query must be a single plain SELECT — WITH/CTE queries are rejected "
            "(they nest arbitrary SELECTs the read-only guard cannot soundly walk)"
        )
    if head != "select":
        raise SqlQueryError(
            "query must be a read-only SELECT — WITH/CTE, CALL/DO and procedure "
            "statements are rejected"
        )
    if _SIDE_EFFECTING_FUNCS.search(q):
        raise SqlQueryError(
            "query must be a plain SELECT FROM a table/view — side-effecting / "
            "volatile function calls (nextval/setval/dblink/lo_*/pg_*/…) are rejected"
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
    # Isolate the select-list: everything after the leading SELECT and before the
    # FIRST top-level FROM. (Top-level FROM = a FROM not nested in parens; but we
    # reject projection subqueries below, so a simple first-FROM split is sound
    # for the accepted flat shape.)
    select_list = re.split(
        r"\bfrom\b", q[len("select"):], maxsplit=1, flags=re.IGNORECASE
    )[0]
    # No subquery in the projection — that smuggles a nested SELECT (and any
    # set-returning / lateral call inside it) past the flat-shape guarantee.
    if _SUBQUERY_SELECT.search(select_list):
        raise SqlQueryError(
            "query must be a plain SELECT FROM a table/view — a subquery in the "
            "select-list is rejected"
        )
    # Scan the WHOLE select-list (every projection item, every call token) and
    # reject any function/proc call outside the read-aggregate allow-list. This is
    # the fix for function calls in later select-list positions and set-returning
    # functions, which the old first-item-only check missed.
    _reject_disallowed_projection_funcs(select_list)
    return q


def _run_query(connection_string: str, query: str) -> tuple[list[str], list[tuple[Any, ...]]]:
    """Execute the validated SELECT in a READ-ONLY transaction; return (columns, rows).

    Isolated for testability — the suite patches this. Enforces read-only at the
    DB level (the real boundary), PostgreSQL only:
    ``default_transaction_read_only=on`` + ``SET TRANSACTION READ ONLY`` +
    ``statement_timeout`` so a write is refused by the server and a runaway query
    is cut off.

    Refuses any dialect outside :data:`_SUPPORTED_BACKENDS` rather than relying on
    the keyword filter alone, and never reflects the connection string back.
    """
    backend = _backend_name(connection_string)
    if backend not in _SUPPORTED_BACKENDS:
        raise SqlUnsupportedBackendError(_UNSUPPORTED_BACKEND_MESSAGE)

    try:
        from sqlalchemy import create_engine, text
    except ImportError as exc:  # pragma: no cover - sqlalchemy is a runtime dep
        raise SqlQueryError("sqlalchemy is required for the SQL connector") from exc

    try:
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
    if not is_supported_backend(conn_str):
        raise SqlUnsupportedBackendError(_UNSUPPORTED_BACKEND_MESSAGE)
    query = validate_query(raw_query)
    columns, raw_rows = _run_query(conn_str, query)
    rows = [
        {col: ("" if val is None else str(val)) for col, val in zip(columns, row)}
        for row in raw_rows
    ]
    return columns, rows
