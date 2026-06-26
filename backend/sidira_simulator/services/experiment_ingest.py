"""Import orchestration (#19) — validate + run an import across connectors.

This is the ADD-only write path: it turns a connector + a confirmed field
mapping into validated Experiment records and writes them to the per-customer
:class:`IngestionStore`. It NEVER touches the existing archive read interface
(seed/similarity/chat). It is HONEST: when a credentialed connector has no
credentials it returns a ``needs_credentials`` result with zero imported rows —
never a fabricated import.

The CSV path runs entirely offline (rows ride in the request). Statsig and SQL
pull their rows from the customer's source the moment credentials are supplied.
"""

from __future__ import annotations

import logging

from sidira_simulator.schemas.connector import (
    ConnectorKind,
    ConnectorState,
    ImportRequest,
    ImportResult,
    ValidateConnectorRequest,
    ValidateConnectorResponse,
)
from sidira_simulator.services.connectors import (
    sql_connector,
    statsig_connector,
)
from sidira_simulator.services.connectors.ingestion_store import IngestionStore
from sidira_simulator.services.connectors.mapping import map_rows, missing_required

logger = logging.getLogger(__name__)

# Generic, customer-safe messages for credentialed-connector failures. The raw
# driver/transport exception is logged server-side (sanitized) but NEVER returned
# — a connection string, host, or DB internals must not leak into an API response
# (MAJOR 3). The detail lives only in the server log.
_SQL_CONNECT_FAILED = "Could not connect with the supplied connection string."
_SQL_QUERY_FAILED = "Query failed under the read-only import policy."
_STATSIG_PULL_FAILED = "Could not pull experiment results from Statsig."


def validate_connector(
    kind: ConnectorKind, req: ValidateConnectorRequest
) -> ValidateConnectorResponse:
    """Check whether a connector can run with the supplied config (honest).

    CSV is always ready. Statsig/SQL report ``needs_credentials`` (with the clear
    "what to supply" message) until their credentials are present; once present
    we validate shape (SQL: the query is a read-only SELECT) but do not run a
    live pull here.
    """
    if kind is ConnectorKind.CSV:
        return ValidateConnectorResponse(
            kind=kind,
            ok=True,
            state=ConnectorState.ACTIVE,
            message="CSV upload is ready — upload a file and map its columns.",
        )

    if kind is ConnectorKind.STATSIG:
        if not statsig_connector.has_credentials(req.config):
            return ValidateConnectorResponse(
                kind=kind,
                ok=False,
                state=ConnectorState.NEEDS_CREDENTIALS,
                message=statsig_connector.NEEDS_MESSAGE,
            )
        return ValidateConnectorResponse(
            kind=kind,
            ok=True,
            state=ConnectorState.ACTIVE,
            message="Statsig API key supplied — ready to pull experiment results.",
        )

    if kind is ConnectorKind.SQL:
        if not sql_connector.has_credentials(req.config):
            return ValidateConnectorResponse(
                kind=kind,
                ok=False,
                state=ConnectorState.NEEDS_CREDENTIALS,
                message=sql_connector.NEEDS_MESSAGE,
            )
        try:
            sql_connector.validate_query(req.config.get("query", ""))
        except sql_connector.SqlQueryError as exc:
            return ValidateConnectorResponse(
                kind=kind,
                ok=False,
                state=ConnectorState.NEEDS_CREDENTIALS,
                message=str(exc),
            )
        return ValidateConnectorResponse(
            kind=kind,
            ok=True,
            state=ConnectorState.ACTIVE,
            message="Connection string + read-only query supplied — ready to import.",
        )

    # Unreachable for the closed enum, but keep the path honest.
    raise ValueError(f"unknown connector kind: {kind}")  # pragma: no cover


def _needs_credentials_result(kind: ConnectorKind, message: str) -> ImportResult:
    return ImportResult(
        kind=kind,
        state=ConnectorState.NEEDS_CREDENTIALS,
        imported=0,
        failed=0,
        errors=[],
        experiments=[],
        message=message,
    )


def _import_failed_result(kind: ConnectorKind, message: str) -> ImportResult:
    """An active connector that failed to pull (no rows written, zero fabricated).

    ``message`` MUST already be a customer-safe generic string — never a raw
    driver/transport exception (MAJOR 3).
    """
    return ImportResult(
        kind=kind,
        state=ConnectorState.ACTIVE,
        imported=0,
        failed=0,
        errors=[],
        experiments=[],
        message=message,
    )


def _resolve_source_rows(
    kind: ConnectorKind, req: ImportRequest, *, customer_id: str
) -> tuple[list[dict[str, str]] | None, ImportResult | None]:
    """Resolve the source rows for a connector (CSV from request, Statsig/SQL pull).

    Returns ``(rows, None)`` on success or ``(None, early_result)`` when the
    connector cannot produce rows (missing credentials, pull/connect failure).
    All failure messages are already customer-safe (MAJOR 3): the raw
    driver/transport detail is logged here, never returned.
    """
    if kind is ConnectorKind.CSV:
        return req.rows, None
    if kind is ConnectorKind.STATSIG:
        try:
            return statsig_connector.fetch_rows(
                req.config, delimiter=req.mapping.variant_delimiter
            ), None
        except statsig_connector.StatsigCredentialError as exc:
            return None, _needs_credentials_result(kind, str(exc))
        except statsig_connector.StatsigFetchError as exc:
            # Log the raw transport detail server-side; return a generic message
            # so an API key / endpoint detail never echoes back (MAJOR 3).
            logger.warning("Statsig pull failed for customer %s: %s", customer_id, exc)
            return None, _import_failed_result(kind, _STATSIG_PULL_FAILED)
    if kind is ConnectorKind.SQL:
        try:
            _, rows = sql_connector.fetch_rows(req.config)
            return rows, None
        except sql_connector.SqlCredentialError as exc:
            return None, _needs_credentials_result(kind, str(exc))
        except sql_connector.SqlConnectError as exc:
            # Connection failures carry the connection string / host — log it
            # server-side, return a generic message (MAJOR 3).
            logger.warning("SQL connect failed for customer %s: %s", customer_id, exc)
            return None, _import_failed_result(kind, _SQL_CONNECT_FAILED)
        except sql_connector.SqlExecutionError as exc:
            # Driver/runtime failure (incl. a write refused by the read-only
            # transaction). Raw driver text is logged, not returned (MAJOR 3).
            logger.warning("SQL query failed for customer %s: %s", customer_id, exc)
            return None, _import_failed_result(kind, _SQL_QUERY_FAILED)
        except sql_connector.SqlQueryError as exc:
            # The customer's own query was rejected by our read-only guard rails.
            # This message describes THEIR query (no driver internals), so it is
            # safe to return and actionable.
            return None, _import_failed_result(kind, f"Query rejected: {exc}")
    raise ValueError(f"unknown connector kind: {kind}")  # pragma: no cover


def _missing_required_result(
    kind: ConnectorKind, req: ImportRequest, row_count: int
) -> ImportResult | None:
    missing = missing_required(req.mapping)
    if not missing:
        return None
    return ImportResult(
        kind=kind,
        state=ConnectorState.ACTIVE,
        imported=0,
        failed=row_count,
        errors=[],
        experiments=[],
        message="Mapping is missing required fields: " + ", ".join(missing),
    )


def preview_import(
    kind: ConnectorKind,
    req: ImportRequest,
    *,
    customer_id: str,
    limit: int = 5,
) -> ImportResult:
    """Dry-run an import: fetch + map the first ``limit`` rows, persist NOTHING.

    The honest "see it before you commit" path for credentialed connectors
    (MAJOR 5): it pulls from the customer's Statsig/SQL source with their
    credentials and maps the rows through the firewall, but NEVER calls
    ``store.record_import()`` — so the customer can verify the mapped result and
    then explicitly confirm before any write. ``imported`` reflects the rows that
    WOULD be imported from the previewed slice; the message says so.
    """
    rows, early = _resolve_source_rows(kind, req, customer_id=customer_id)
    if early is not None:
        return early
    assert rows is not None

    blocked = _missing_required_result(kind, req, len(rows))
    if blocked is not None:
        return blocked

    preview_rows = rows[:limit]
    experiments, errors = map_rows(preview_rows, req.mapping, id_prefix="preview")

    if not rows:
        message = "No rows found in the source to preview."
    elif not experiments:
        message = (
            f"No rows mapped in the previewed {len(preview_rows)} row(s) — "
            f"{len(errors)} had errors. Nothing has been imported."
        )
    else:
        message = (
            f"Preview only — nothing imported yet. {len(experiments)} of the first "
            f"{len(preview_rows)} row(s) mapped cleanly"
            + (f"; {len(errors)} would be skipped" if errors else "")
            + f". Source has {len(rows)} row(s) total; confirm to import."
        )

    return ImportResult(
        kind=kind,
        state=ConnectorState.ACTIVE,
        imported=len(experiments),
        failed=len(errors),
        errors=errors,
        experiments=experiments,
        message=message,
    )


def run_import(
    kind: ConnectorKind,
    req: ImportRequest,
    *,
    customer_id: str,
    store: IngestionStore,
) -> ImportResult:
    """Run an import for one connector and write the mapped records to the store.

    Resolves source rows (CSV: from the request; Statsig/SQL: pulled from the
    customer's source with their credentials), maps them through the firewall,
    persists the successes, and reports failures per-row. Returns a
    ``needs_credentials`` result (zero rows) when a credentialed connector lacks
    credentials.
    """
    id_prefix = f"{kind.value}"

    rows, early = _resolve_source_rows(kind, req, customer_id=customer_id)
    if early is not None:
        return early
    assert rows is not None

    blocked = _missing_required_result(kind, req, len(rows))
    if blocked is not None:
        return blocked

    experiments, errors = map_rows(rows, req.mapping, id_prefix=id_prefix)
    if experiments:
        store.record_import(customer_id, kind, experiments)

    if not rows:
        message = "No rows to import."
    elif not experiments:
        message = f"No rows imported — {len(errors)} row(s) had errors."
    elif errors:
        message = (
            f"Imported {len(experiments)} experiment(s); "
            f"{len(errors)} row(s) skipped with errors."
        )
    else:
        message = f"Imported {len(experiments)} experiment(s) into the archive."

    return ImportResult(
        kind=kind,
        state=ConnectorState.ACTIVE,
        imported=len(experiments),
        failed=len(errors),
        errors=errors,
        experiments=experiments,
        message=message,
    )
