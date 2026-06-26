"""Connector registry (#19) — the declarative list of ingestion sources.

The registry is the single source of truth for *which* connectors exist and
*whether they can run right now*. The CSV connector is ``ACTIVE`` (no
credentials). Statsig and SQL are real, registered connectors that report
``NEEDS_CREDENTIALS`` until the customer supplies their own credentials — they
are listed (so the UI can show an honest picker) but never run with fabricated
state.

``describe_connectors`` returns the static catalogue (state reflecting "what is
needed", not a per-customer live check). Validation of a specific credential set
happens in the import/validate path, not here.
"""

from __future__ import annotations

from sidira_simulator.schemas.connector import (
    ConnectorDescriptor,
    ConnectorKind,
    ConnectorState,
)
from sidira_simulator.services.connectors import (
    sql_connector,
    statsig_connector,
)

_CSV = ConnectorDescriptor(
    kind=ConnectorKind.CSV,
    name="CSV upload",
    summary="Upload a CSV of past experiments and map its columns to the archive.",
    state=ConnectorState.ACTIVE,
    credential_fields=[],
    needs_message=None,
)

_STATSIG = ConnectorDescriptor(
    kind=ConnectorKind.STATSIG,
    name="Statsig",
    summary="Pull resolved experiment results from your Statsig Console.",
    state=ConnectorState.NEEDS_CREDENTIALS,
    credential_fields=["api_key"],
    needs_message=statsig_connector.NEEDS_MESSAGE,
)

_SQL = ConnectorDescriptor(
    kind=ConnectorKind.SQL,
    name="SQL database",
    summary="Run a read-only SELECT against your warehouse and map the columns.",
    state=ConnectorState.NEEDS_CREDENTIALS,
    credential_fields=["connection_string", "query"],
    needs_message=sql_connector.NEEDS_MESSAGE,
)

_REGISTRY: dict[ConnectorKind, ConnectorDescriptor] = {
    ConnectorKind.CSV: _CSV,
    ConnectorKind.STATSIG: _STATSIG,
    ConnectorKind.SQL: _SQL,
}


def describe_connectors() -> list[ConnectorDescriptor]:
    """All registered connectors, CSV first then the credentialed ones."""
    order = (ConnectorKind.CSV, ConnectorKind.STATSIG, ConnectorKind.SQL)
    return [_REGISTRY[k].model_copy(deep=True) for k in order]


def get_descriptor(kind: ConnectorKind) -> ConnectorDescriptor:
    """The descriptor for one connector kind."""
    return _REGISTRY[kind].model_copy(deep=True)
