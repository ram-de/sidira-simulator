"""Connector / onboarding routes (#19).

The ingestion side of the experiment archive: list connectors, download the CSV
template/sample, preview an uploaded CSV, validate a connector's credentials,
run an import, and list past imports. All NEW routes — no existing endpoint is
touched, and the archive read interface (similarity / chat / dedup) is untouched.

HONEST: CSV works end-to-end with no credentials. Statsig and SQL report a
``needs_credentials`` state until the customer supplies their own credentials;
they never return fabricated results.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import Response

from sidira_simulator.api.deps import current_customer_id
from sidira_simulator.schemas.connector import (
    ConnectorKind,
    CsvPreviewResponse,
    ImportRequest,
    ImportResult,
    ListConnectorsResponse,
    ListImportsResponse,
    ValidateConnectorRequest,
    ValidateConnectorResponse,
)
from sidira_simulator.services.connectors import csv_connector
from sidira_simulator.services.connectors.ingestion_store import (
    IngestionStore,
    get_ingestion_store,
)
from sidira_simulator.services.connectors.mapping import suggest_mapping
from sidira_simulator.services.connectors.registry import describe_connectors
from sidira_simulator.services.experiment_ingest import (
    preview_import,
    run_import,
    validate_connector,
)

router = APIRouter(prefix="/connectors", tags=["connectors"])

# Reject absurdly large uploads up front (the archive is experiment rows, not a
# data lake) — an honest, bounded preview path.
_MAX_CSV_BYTES = 5 * 1024 * 1024  # 5 MiB
_PREVIEW_LIMIT = 5


def get_store() -> IngestionStore:
    """FastAPI dependency wrapper so the suite can override the store if needed."""
    return get_ingestion_store()


@router.get("", response_model=ListConnectorsResponse)
def list_connectors() -> ListConnectorsResponse:
    """List every registered connector and whether it can run right now.

    CSV is ``active``; Statsig and SQL are ``needs_credentials`` until the
    customer supplies their own credentials (the UI renders an honest picker).
    """
    return ListConnectorsResponse(connectors=describe_connectors())


@router.get("/csv/template")
def csv_template() -> Response:
    """Download the header-only CSV template (the expected column shape)."""
    return Response(
        content=csv_connector.template_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="sidira-experiments-template.csv"'
        },
    )


@router.get("/csv/sample")
def csv_sample() -> Response:
    """Download a filled-in sample CSV so the CSV path is demoable with no data."""
    return Response(
        content=csv_connector.sample_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="sidira-experiments-sample.csv"'
        },
    )


@router.post("/csv/preview", response_model=CsvPreviewResponse)
async def csv_preview(
    file: UploadFile = File(...),
    variant_delimiter: str = Form("|"),
) -> CsvPreviewResponse:
    """Parse an uploaded CSV → columns + suggested mapping + a verifiable preview.

    Does NOT import — it lets the customer confirm the column mapping before
    committing. Per-row errors in the previewed rows are shown, never hidden.
    """
    raw = await file.read()
    if len(raw) > _MAX_CSV_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"CSV exceeds the {_MAX_CSV_BYTES // (1024 * 1024)} MiB limit",
        )
    try:
        columns, rows = csv_connector.parse_csv(raw)
    except csv_connector.CsvParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    mapping = suggest_mapping(columns, delimiter=variant_delimiter)
    profiles = csv_connector.profile_columns(columns, rows)

    # Map only the first few rows for the preview (cheap, verifiable). The full
    # import re-maps every row.
    from sidira_simulator.services.connectors.mapping import map_rows

    preview_rows = rows[:_PREVIEW_LIMIT]
    experiments, errors = map_rows(preview_rows, mapping, id_prefix="preview")

    return CsvPreviewResponse(
        columns=profiles,
        suggested_mapping=mapping,
        row_count=len(rows),
        preview=experiments,
        errors=errors,
    )


@router.post("/{kind}/validate", response_model=ValidateConnectorResponse)
def validate(kind: ConnectorKind, req: ValidateConnectorRequest) -> ValidateConnectorResponse:
    """Validate/configure a connector — honest about what credentials are missing."""
    return validate_connector(kind, req)


@router.post("/{kind}/preview", response_model=ImportResult)
def preview_connector_import(
    kind: ConnectorKind,
    req: ImportRequest,
    customer_id: str = Depends(current_customer_id),
) -> ImportResult:
    """Dry-run a credentialed import: pull + map the first rows, persist NOTHING.

    The honest "see it before you commit" path for Statsig/SQL — it fetches from
    the customer's source with their credentials and shows the mapped result, but
    NEVER writes to the archive. The customer reviews the preview, then calls
    ``/import`` to actually persist (MAJOR 5). No store dependency: a preview can
    never touch the customer's archive.
    """
    return preview_import(kind, req, customer_id=customer_id)


@router.post("/{kind}/import", response_model=ImportResult)
def run_connector_import(
    kind: ConnectorKind,
    req: ImportRequest,
    customer_id: str = Depends(current_customer_id),
    store: IngestionStore = Depends(get_store),
) -> ImportResult:
    """Run an import and write the mapped records into the customer's archive.

    A credentialed connector with no credentials returns a ``needs_credentials``
    result with zero imported rows — never a fabricated import.
    """
    return run_import(kind, req, customer_id=customer_id, store=store)


@router.get("/imports", response_model=ListImportsResponse)
def list_imports(
    customer_id: str = Depends(current_customer_id),
    store: IngestionStore = Depends(get_store),
) -> ListImportsResponse:
    """Past imports for this customer + the total size of the ingested archive."""
    return ListImportsResponse(
        imports=store.imports_for(customer_id),
        archive_size=len(store.archive_for(customer_id)),
    )
