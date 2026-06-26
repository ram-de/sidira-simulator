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
from sidira_simulator.services.connectors.registry import get_descriptor


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

    # ── resolve the source rows for this connector ──────────────────────────
    if kind is ConnectorKind.CSV:
        rows = req.rows
    elif kind is ConnectorKind.STATSIG:
        try:
            rows = statsig_connector.fetch_rows(
                req.config, delimiter=req.mapping.variant_delimiter
            )
        except statsig_connector.StatsigCredentialError as exc:
            return _needs_credentials_result(kind, str(exc))
        except statsig_connector.StatsigFetchError as exc:
            return ImportResult(
                kind=kind,
                state=ConnectorState.ACTIVE,
                imported=0,
                failed=0,
                errors=[],
                experiments=[],
                message=f"Could not pull from Statsig: {exc}",
            )
    elif kind is ConnectorKind.SQL:
        try:
            _, rows = sql_connector.fetch_rows(req.config)
        except sql_connector.SqlCredentialError as exc:
            return _needs_credentials_result(kind, str(exc))
        except sql_connector.SqlQueryError as exc:
            return ImportResult(
                kind=kind,
                state=ConnectorState.ACTIVE,
                imported=0,
                failed=0,
                errors=[],
                experiments=[],
                message=f"Query rejected or failed: {exc}",
            )
    else:  # pragma: no cover - closed enum
        raise ValueError(f"unknown connector kind: {kind}")

    # ── map through the firewall + persist successes ────────────────────────
    missing = missing_required(req.mapping)
    if missing:
        return ImportResult(
            kind=kind,
            state=ConnectorState.ACTIVE,
            imported=0,
            failed=len(rows),
            errors=[],
            experiments=[],
            message=(
                "Mapping is missing required fields: " + ", ".join(missing)
            ),
        )

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
