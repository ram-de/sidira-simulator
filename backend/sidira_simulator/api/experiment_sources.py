"""Persisted experiment-SOURCE connections (#46) — admin-managed.

Today ``/connectors`` is a ONE-SHOT import: it validates / previews / imports
past A/B experiments with request-time credentials and persists NOTHING. This
router adds the persisted, admin-managed SOURCE the admin-console council called
for: an admin CONNECTS an experiment source (Statsig / SQL / CSV) once, the
credentials are envelope-encrypted at rest (AAD-bound to ``customer_id:id``,
adapters/credentials.py), and the source can then be RE-IMPORTED on demand using
the stored creds. Refresh is one-time-on-connect + on-demand re-import — NEVER
live per-query (council §"Data-refresh model").

RBAC (council "configuration = admin; execution = member"):
  * create / test / delete  → ``require_admin`` (they create persistent workspace
    state, bear / exercise credentials, or destroy state).
  * list / get               → member-readable: a member may SEE a source's
    EXISTENCE / status / last-import — never its secrets.
  * re-import                → member-OK: it is EXECUTION (it runs an import
    against an already-configured source; it creates no new credential and spends
    only what running the existing source costs). Mirrors "run a crawl / build
    personas / run a sim" staying open to members.

Secrets are write-only (#488 invariant): the credentials are accepted on create,
encrypted, and NEVER echoed back — GET/list return a non-secret ``display_config``
plus a ``credentials_set`` flag. Re-import failures return a customer-safe generic
message; the raw driver/transport detail is logged server-side, never returned.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.credentials import CredentialError
from sidira_simulator.adapters.repositories import (
    ExperimentConnectionRepo,
    ExperimentImportRunRepo,
)
from sidira_simulator.api.deps import (
    current_customer_id,
    current_user_id,
    get_experiment_connection_repo,
    get_experiment_import_run_repo,
    require_admin,
)
from sidira_simulator.schemas.connector import (
    ConnectorKind,
    ConnectorState,
    FieldMapping,
    ImportRequest,
    ValidateConnectorRequest,
)
from sidira_simulator.services.connectors.ingestion_store import (
    IngestionStore,
    get_ingestion_store,
)
from sidira_simulator.services.experiment_ingest import run_import, validate_connector

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/experiment-sources", tags=["experiment-sources"])


def get_store() -> IngestionStore:
    """FastAPI dependency wrapper so the suite can override the store if needed."""
    return get_ingestion_store()


# Which config keys are SECRET per connector kind. These are encrypted at rest
# and NEVER returned. Everything else in the supplied config is non-secret
# ``display_config`` (host/database/project/query/delimiter). Keep this aligned
# with the connector modules' credential fields (statsig: api_key; sql:
# connection_string). The SQL ``query`` is NOT a secret — it stays in display.
_SECRET_KEYS: dict[ConnectorKind, tuple[str, ...]] = {
    ConnectorKind.CSV: (),
    ConnectorKind.STATSIG: ("api_key",),
    ConnectorKind.SQL: ("connection_string",),
}


class CreateSourceRequest(BaseModel):
    """Connect a persisted experiment source.

    ``config`` carries the connector's full configuration; the SECRET keys
    (``api_key`` for Statsig, ``connection_string`` for SQL) are encrypted at
    rest and never returned. The remaining keys are non-secret display config.
    ``mapping`` is the confirmed field mapping the re-import re-applies to every
    pulled row (the firewall rename — see schemas/connector.py).
    """

    name: str = Field(description="Customer-facing label for this source.")
    kind: ConnectorKind
    config: dict[str, str] = Field(
        default_factory=dict,
        description="Connector config; secret keys are encrypted, the rest displayed.",
    )
    mapping: FieldMapping = Field(
        default_factory=lambda: FieldMapping(columns={}),
        description="Confirmed column→Experiment-field mapping for re-imports.",
    )


class ImportRunSummary(BaseModel):
    id: str
    status: Literal["running", "succeeded", "failed"]
    started_at: datetime
    finished_at: datetime | None = None
    imported_count: int = 0
    failed_count: int = 0
    error: str | None = None


class SourceSummary(BaseModel):
    """Sanitized view of a saved source. NEVER includes any credential.

    ``display_config`` carries only the non-secret fields (host/database/project/
    query/delimiter). ``credentials_set`` is the write-only-secret flag (#488):
    True means a credential is stored, without ever echoing it.
    """

    id: str
    name: str
    kind: ConnectorKind
    status: str
    display_config: dict[str, Any]
    credentials_set: bool
    created_by: str | None = None
    created_at: datetime
    last_import_at: datetime | None = None


def _summary_from_row(row: dict) -> SourceSummary:
    return SourceSummary(
        id=row["id"],
        name=row["name"],
        kind=row["kind"],
        status=row["status"],
        display_config=row.get("display_config") or {},
        credentials_set=row.get("credentials_enc") is not None,
        created_by=row.get("created_by"),
        created_at=row["created_at"],
        last_import_at=row.get("last_import_at"),
    )


def _split_config(
    kind: ConnectorKind, config: dict[str, str]
) -> tuple[dict[str, str], dict[str, str]]:
    """Split a supplied config into (secret, display) by the per-kind secret keys.
    Secret values are dropped from display so they never reach a stored/echoed
    column."""
    secret_keys = _SECRET_KEYS.get(kind, ())
    secret = {k: v for k, v in config.items() if k in secret_keys and v}
    display = {k: v for k, v in config.items() if k not in secret_keys}
    return secret, display


def _rebuild_config(row: dict, customer_id: str) -> dict[str, str]:
    """Reassemble the full connector config for an import: decrypt the stored
    secret blob (if any) and merge it over the non-secret display_config.
    Decryption is fresh per call; the cleartext secret never leaves this scope.
    Raises 503 on a credential/key problem (never an opaque 500)."""
    # display_config holds the non-secret connector config PLUS the saved
    # `_mapping` (a nested dict, applied separately by the re-import) — exclude
    # `_mapping` so the connector config stays a flat dict[str, str].
    config: dict[str, str] = {
        k: str(v) for k, v in (row.get("display_config") or {}).items() if k != "_mapping"
    }
    blob = row.get("credentials_enc")
    if blob is not None:
        aad = f"{customer_id}:{row['id']}".encode()
        try:
            secret = credentials.decrypt(
                credentials.deserialize_blob(blob),
                customer_id=customer_id,
                aad=aad,
            )
        except CredentialError as exc:
            raise HTTPException(
                status_code=503,
                detail="cannot decrypt stored source credentials — re-connect the source",
            ) from exc
        config.update({k: str(v) for k, v in secret.items()})
    return config


@router.post(
    "",
    response_model=SourceSummary,
    status_code=201,
    dependencies=[Depends(require_admin)],  # #46: persists creds — admin-only
)
async def create_source(
    payload: CreateSourceRequest,
    customer_id: str = Depends(current_customer_id),
    user_id: str = Depends(current_user_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
) -> SourceSummary:
    """Connect a persisted experiment source: encrypt the credentials at rest
    (AAD-bound to ``customer_id:id``) and persist a sanitized row. Admin-only —
    it creates persistent, credential-bearing workspace state."""
    if await repo.name_exists(customer_id, payload.name):
        raise HTTPException(
            status_code=409,
            detail=f"a source named {payload.name.strip()!r} already exists — "
            "pick a different name",
        )
    connection_id = f"es-{uuid4().hex[:12]}"
    secret, display = _split_config(payload.kind, payload.config)
    # Persist the confirmed mapping alongside the non-secret display config so
    # the re-import can re-apply it without re-asking the admin.
    display["_mapping"] = payload.mapping.model_dump()

    credentials_enc: dict[str, Any] | None = None
    if secret:
        aad = f"{customer_id}:{connection_id}".encode()
        try:
            blob = credentials.encrypt(secret, customer_id=customer_id, aad=aad)
        except CredentialError as exc:
            raise HTTPException(
                status_code=503, detail="credential encryption is not configured"
            ) from exc
        credentials_enc = credentials.serialize_blob(blob)

    row = await repo.insert(
        {
            "id": connection_id,
            "customer_id": customer_id,
            "name": payload.name,
            "kind": payload.kind.value,
            "display_config": display,
            "credentials_enc": credentials_enc,
            "status": "connected",
            "created_by": user_id,
        }
    )
    return _summary_from_row(row)


@router.get("", response_model=list[SourceSummary])
async def list_sources(
    customer_id: str = Depends(current_customer_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
) -> list[SourceSummary]:
    """List the customer's saved sources. Member-readable: existence / status /
    last-import are visible to everyone in the org; secrets are NEVER returned."""
    rows = await repo.list_for_customer(customer_id)
    return [_summary_from_row(row) for row in rows]


@router.get("/{connection_id}", response_model=SourceSummary)
async def get_source(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
) -> SourceSummary:
    """Metadata only — secrets never echoed (``credentials_set`` flag + non-secret
    ``display_config``). Cross-tenant id → 404 (existence never leaks)."""
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="source not found")
    return _summary_from_row(row)


@router.get("/{connection_id}/imports", response_model=list[ImportRunSummary])
async def list_imports(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
    run_repo: ExperimentImportRunRepo = Depends(get_experiment_import_run_repo),
) -> list[ImportRunSummary]:
    """Import-run history for one source (member-readable). Cross-tenant → 404."""
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="source not found")
    runs = await run_repo.list_for_connection(connection_id, customer_id)
    return [ImportRunSummary(**run) for run in runs]


@router.delete(
    "/{connection_id}",
    status_code=204,
    dependencies=[Depends(require_admin)],  # #46: destroys creds + history — admin-only
)
async def delete_source(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
) -> None:
    """Delete a saved source. Customer-scoped: unknown id OR another tenant's id
    both → 404 (existence never leaks). The cred blob is a column on the deleted
    row (gone with it) and the import-run history cascades via the FK."""
    deleted = await repo.delete(connection_id, customer_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="source not found")


@router.post(
    "/{connection_id}/test",
    status_code=204,
    dependencies=[Depends(require_admin)],  # #46: exercises stored creds — admin-only
)
async def test_source(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
) -> None:
    """Validate the stored config can run (shape + credential presence). 204 on
    ready; 400 with a customer-safe message when the source needs credentials /
    config. Decrypts the stored blob to validate, never echoing it."""
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="source not found")
    kind = ConnectorKind(row["kind"])
    config = _rebuild_config(row, customer_id)
    result = validate_connector(kind, ValidateConnectorRequest(config=config))
    if not result.ok:
        # validate_connector's messages are already customer-safe (never reflect a
        # connection string back — see experiment_ingest / sql_connector).
        raise HTTPException(status_code=400, detail=result.message)


@router.post("/{connection_id}/reimport", response_model=ImportRunSummary)
async def reimport_source(
    connection_id: str,
    customer_id: str = Depends(current_customer_id),
    repo: ExperimentConnectionRepo = Depends(get_experiment_connection_repo),
    run_repo: ExperimentImportRunRepo = Depends(get_experiment_import_run_repo),
    store: IngestionStore = Depends(get_store),
) -> ImportRunSummary:
    """RE-IMPORT on demand: pull the source again using the STORED credentials and
    materialize the mapped experiments into the customer's archive.

    EXECUTION, so member-OK (council: refresh = execution = member). It runs the
    existing one-shot import pipeline (services/experiment_ingest.run_import) with
    the decrypted stored creds + saved mapping — there is NO live per-query path;
    a re-import is a fresh full pull each time the admin/member asks for one.

    Records an ``ExperimentImportRun`` (started → finished) and stamps the
    connection's ``last_import_at``. The import result's message is customer-safe
    (#488); a connector that needs credentials / fails returns the run with
    status='failed' and a safe error, never a raw driver string.
    """
    row = await repo.get(connection_id, customer_id)
    if row is None:
        raise HTTPException(status_code=404, detail="source not found")

    kind = ConnectorKind(row["kind"])
    config = _rebuild_config(row, customer_id)
    mapping_data = (row.get("display_config") or {}).get("_mapping") or {"columns": {}}
    mapping = FieldMapping(**mapping_data)

    run_id = f"eir-{uuid4().hex[:12]}"
    started_at = datetime.now(timezone.utc)
    await run_repo.create(
        {
            "id": run_id,
            "connection_id": connection_id,
            "customer_id": customer_id,
            "status": "running",
            "started_at": started_at,
        }
    )

    result = run_import(
        kind,
        ImportRequest(mapping=mapping, config=config),
        customer_id=customer_id,
        store=store,
    )
    finished_at = datetime.now(timezone.utc)
    # needs_credentials or zero imported with a failure message → failed; an
    # honest import (even 0 rows from an empty source) is a success.
    failed = result.state is ConnectorState.NEEDS_CREDENTIALS
    status = "failed" if failed else "succeeded"
    # result.message is already customer-safe (experiment_ingest sanitizes every
    # driver/transport detail). Carry it as the run error only on failure.
    error = result.message if failed else None

    await run_repo.finish(
        run_id,
        customer_id,
        status=status,
        finished_at=finished_at,
        imported_count=result.imported,
        failed_count=result.failed,
        error=error,
    )
    await repo.mark_import(
        connection_id,
        customer_id,
        status="connected" if not failed else "error",
        imported_at=finished_at,
    )

    return ImportRunSummary(
        id=run_id,
        status=status,
        started_at=started_at,
        finished_at=finished_at,
        imported_count=result.imported,
        failed_count=result.failed,
        error=error,
    )
