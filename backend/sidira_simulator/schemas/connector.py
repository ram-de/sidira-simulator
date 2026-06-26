"""Connector schemas (#19) — the onboarding/ingestion side of the archive.

These models describe the *ingestion* path that brings EXTERNAL experiments into
the existing :class:`~sidira_simulator.schemas.experiment_memory.Experiment`
archive. They are deliberately additive: nothing here touches the read side
(similarity / chat / dedup) that another builder is extending in parallel.

Two-table firewall (mirrors ``experiment_memory``): a :class:`FieldMapping` maps
source columns onto the Experiment's INPUT fields (change_description, variants,
primary_metric, category) and its OUTCOME fields (winner, result,
effect_size_pct, n, date) — but it is a pure column rename, deterministic and
zero-LLM. It never derives an outcome from an input (or vice versa), so no
leakage path is invented: an imported record is exactly what the customer
recorded, just re-keyed onto our schema.

HONEST connectors: only the CSV connector resolves to data without credentials.
Statsig and SQL are *registered* connectors that report a ``needs_credentials``
state until the customer supplies their own key / connection string — they never
fabricate a result.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from sidira_simulator.schemas.experiment_memory import Experiment


class ConnectorKind(str, Enum):
    """The external source an import was pulled from."""

    CSV = "csv"
    STATSIG = "statsig"
    SQL = "sql"


class ConnectorState(str, Enum):
    """Whether a registered connector can run right now.

    - ``ACTIVE``: works end-to-end with no extra setup (CSV — the customer
      uploads a file; nothing to authenticate).
    - ``NEEDS_CREDENTIALS``: a real connector that is registered but inactive
      until the customer supplies their own credentials (Statsig API key, SQL
      connection string). It NEVER returns fabricated results in this state.
    """

    ACTIVE = "active"
    NEEDS_CREDENTIALS = "needs_credentials"


# The nine Experiment fields a mapping can target. Split exactly along the
# two-table firewall so the boundary is legible in code, not just in prose.
INPUT_FIELDS: tuple[str, ...] = (
    "change_description",
    "variants",
    "primary_metric",
    "category",
)
OUTCOME_FIELDS: tuple[str, ...] = (
    "winner",
    "result",
    "effect_size_pct",
    "n",
    "date",
)
TARGET_FIELDS: tuple[str, ...] = INPUT_FIELDS + OUTCOME_FIELDS


class ConnectorDescriptor(BaseModel):
    """A connector advertised by the registry — what the UI renders in its picker.

    ``state`` is honest: ``needs_credentials`` connectors are shown but cannot run
    until the customer authenticates. ``credential_fields`` lists what the
    customer must supply (never pre-filled, never faked).
    """

    kind: ConnectorKind
    name: str = Field(description="Customer-facing connector name.")
    summary: str = Field(description="One sentence: what this connector ingests.")
    state: ConnectorState
    credential_fields: list[str] = Field(
        default_factory=list,
        description=(
            "Names of credentials the customer must supply for this connector to "
            "run (empty for CSV). The customer provides these — never hardcoded."
        ),
    )
    needs_message: str | None = Field(
        default=None,
        description=(
            "For needs_credentials connectors: the clear 'what to supply' message. "
            "None for active connectors."
        ),
    )


class ListConnectorsResponse(BaseModel):
    connectors: list[ConnectorDescriptor]


class FieldMapping(BaseModel):
    """Maps source column names onto Experiment fields (the firewall boundary).

    A pure, deterministic rename: ``{Experiment field -> source column name}``.
    ``variants`` may map to a single delimited column (split on
    :attr:`variant_delimiter`). Only INPUT/OUTCOME target keys are honored; any
    other key is ignored. Required fields missing from the mapping surface as
    honest per-row errors at parse time rather than silently fabricating values.
    """

    columns: dict[str, str] = Field(
        description="Experiment field name -> source column name.",
    )
    variant_delimiter: str = Field(
        default="|",
        description="Delimiter used to split the variants column into arms.",
    )


class ColumnProfile(BaseModel):
    """A detected source column plus a few example values (for the mapping UI)."""

    name: str
    sample_values: list[str] = Field(default_factory=list)


class RowError(BaseModel):
    """An honest, per-row parse/validation failure (never silently dropped)."""

    row: int = Field(description="1-based source row index (excludes the header).")
    message: str


class CsvPreviewResponse(BaseModel):
    """What the customer sees after uploading a CSV, before importing.

    Carries the detected columns (for mapping), a suggested mapping (best-effort
    header match — the customer confirms/edits it), and a small parsed preview so
    the customer can verify the mapping is right before committing the import.
    """

    columns: list[ColumnProfile]
    suggested_mapping: FieldMapping
    row_count: int = Field(description="Total data rows detected (excludes header).")
    preview: list[Experiment] = Field(
        description="Up to a handful of successfully-mapped rows, for verification.",
    )
    errors: list[RowError] = Field(
        default_factory=list,
        description="Per-row errors in the previewed rows — shown, never hidden.",
    )


class ValidateConnectorRequest(BaseModel):
    """Validate/configure a connector before importing.

    Credentials are supplied by the customer at request time and are NOT
    persisted by this endpoint — keeping the connector honest (no stored faked
    state) and migration-free. ``config`` carries connector-specific fields
    (e.g. the SQL connection string + query, or a Statsig API key).
    """

    config: dict[str, str] = Field(
        default_factory=dict,
        description="Connector-specific credentials / configuration.",
    )


class ValidateConnectorResponse(BaseModel):
    """The honest result of validating a connector's credentials/config."""

    kind: ConnectorKind
    ok: bool
    state: ConnectorState
    message: str = Field(
        description="Human-readable validation outcome (success or what's missing)."
    )


class ImportRequest(BaseModel):
    """Run an import. The CSV path carries the raw rows; Statsig/SQL carry config.

    For CSV, ``rows`` is the parsed source (list of column->value dicts) plus the
    confirmed ``mapping``. For Statsig/SQL, ``config`` carries the customer's
    credentials and the mapping is applied to the rows the connector pulls. If
    the credentials are absent the import returns a needs_credentials result
    rather than inventing data.
    """

    mapping: FieldMapping
    rows: list[dict[str, str]] = Field(
        default_factory=list,
        description="Source rows for the CSV path (column -> value).",
    )
    config: dict[str, str] = Field(
        default_factory=dict,
        description="Credentials / config for the Statsig and SQL paths.",
    )


class ImportResult(BaseModel):
    """The honest outcome of an import — never silently partial.

    ``imported`` counts records written to the archive; ``failed`` rows are
    reported individually so the customer can fix and re-import. When a connector
    ``needs_credentials``, ``state`` says so and ``imported`` is 0 (no fabricated
    rows).
    """

    kind: ConnectorKind
    state: ConnectorState
    imported: int
    failed: int
    errors: list[RowError] = Field(default_factory=list)
    experiments: list[Experiment] = Field(
        default_factory=list,
        description="The records written to the archive by this import.",
    )
    message: str


class ImportSummary(BaseModel):
    """A past import, for the 'what have I brought in' list."""

    id: str
    kind: ConnectorKind
    imported: int
    at: str = Field(description="ISO-8601 timestamp the import completed.")


class ListImportsResponse(BaseModel):
    imports: list[ImportSummary]
    archive_size: int = Field(
        description="Total experiments in the customer's ingested archive."
    )
