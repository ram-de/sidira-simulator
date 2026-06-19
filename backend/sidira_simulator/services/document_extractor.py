"""#3 Document → feature feeder (MiroFish-borrow) — the bounded extractor.

Turns unstructured documents (interview notes, support tickets, surveys, crawl
text) into the SAME per-entity row shape a `FeatureStore.run_query()` returns —
``list[dict[str, Any]]``, one row per entity, keys = feature-column names — so the
entire existing build path (column mapping → clustering → gates → wizard) consumes
it unchanged. The only new thing is *how the rows are produced*.

PRIOR-ECHO DISCIPLINE (the whole point of the ticket, mirrors #4 column_mapper):
the extraction is **closed-set and extractive**, never generative.

  * The caller supplies a CLOSED `ExtractionSchema` — a fixed list of fields, each
    with one of the 8 sidira-personas metric types. The output row carries EXACTLY
    those fields (+ the entity key) and nothing else: a value the model invents for
    a field outside the schema is dropped, exactly as column_mapper buckets an
    out-of-canon group into ``unmapped``.
  * The model is instructed to EXTRACT/quantify only what the text evidences and to
    return null when a field is not supported by the document — it may never guess.
    A fabricated persona attribute is the exact "more-is-better" failure mode Sidira
    guards against, so absence must read as null, not as an invented value.

Parsing is defensive and deterministic: we iterate the schema's fields (not the
model's output), so a field the model omits becomes None rather than silently
vanishing, and the row schema is identical across entities.

This module is PURE and currently UNWIRED — nothing imports it into a live build
yet. The build-source wiring and the wizard upload step are separate slices; until
they land, existing Snowflake builds are untouched.
"""

from __future__ import annotations

import json
import math
from typing import Any

from pydantic import BaseModel, Field

from sidira_simulator.adapters.feature_stores import ColumnProfile
from sidira_simulator.adapters.llm import ChatClient, JSONRepairError, get_chat_client

#: The closed set of metric types `sidira_personas.adapter.adapt_group` accepts
#: (adapter.py:103-121). An extraction field MUST declare one of these so the row
#: it produces is normalizable by the existing pipeline — never an ad-hoc type.
METRIC_TYPES: tuple[str, ...] = (
    "count",
    "score",
    "ratio",
    "flag",
    "categorical",
    "json_ratios",
    "json_counts",
    "tenure_days",
)

#: Metric types whose extracted value is a plain real number.
_NUMERIC_TYPES = frozenset({"count", "score", "ratio", "tenure_days"})
#: Metric types whose extracted value is a JSON object of name → number.
_JSON_TYPES = frozenset({"json_ratios", "json_counts"})


class DocumentExtractionError(RuntimeError):
    """Raised when the extraction LLM call fails or its output can't be parsed.

    The API layer turns this into a 502 — the model/provider, not the caller, is
    at fault. A malformed *schema* (caller error) raises ``ValueError`` instead.
    """


class ExtractionField(BaseModel):
    """One bounded column to pull from each entity's documents.

    ``type`` must be one of :data:`METRIC_TYPES` so the column re-enters the
    existing adapter. ``description`` is the extraction instruction shown to the
    model (what evidence to look for); it never widens the field set.
    """

    name: str
    type: str
    description: str = ""


class ExtractionSchema(BaseModel):
    """The CLOSED set of fields extraction may emit. Anything else is dropped."""

    fields: list[ExtractionField] = Field(default_factory=list)
    entity_key: str = "entity_id"

    def validate_closed(self) -> None:
        """Reject a malformed schema up front (caller error, not model error)."""
        if not self.fields:
            raise ValueError("ExtractionSchema.fields must be non-empty")
        seen: set[str] = set()
        for f in self.fields:
            if not f.name:
                raise ValueError("ExtractionField.name must be non-empty")
            if f.type not in METRIC_TYPES:
                raise ValueError(
                    f"ExtractionField {f.name!r} has unknown type {f.type!r}; "
                    f"must be one of {METRIC_TYPES}"
                )
            if f.name == self.entity_key:
                raise ValueError(
                    f"field name {f.name!r} collides with entity_key"
                )
            if f.name in seen:
                raise ValueError(f"duplicate field name {f.name!r}")
            seen.add(f.name)


class EntityDocument(BaseModel):
    """All document text for a single entity (one persona-pipeline row)."""

    entity_id: str
    text: str = ""


# ── internal LLM-response schema (flat, one entry per field) ─────────────────


class _RawValue(BaseModel):
    name: str
    value: Any = None


class _RawExtraction(BaseModel):
    values: list[_RawValue] = Field(default_factory=list)


_SYSTEM = """You extract structured features from a user's documents into a FIXED
schema. You are given a numbered list of fields; for EACH field return its value
strictly from evidence in the documents.

Hard rules:
- Only return the listed fields. Do not invent fields.
- If a field is not supported by the documents, return null for it. NEVER guess,
  infer beyond the text, or fill a plausible default — absence must be null.
- count: a non-negative integer/number of occurrences.
- score: a numeric rating/level evidenced in the text.
- ratio: a fraction between 0 and 1.
- flag: true or false (a boolean).
- categorical: a single short string label.
- json_ratios / json_counts: a flat JSON object of {label: number}.
- tenure_days: a number of days.

Return strict JSON matching the schema — no prose, no markdown fences."""


def _coerce(value: Any, mtype: str) -> Any:
    """Coerce a model-returned value to its metric type; unusable → None.

    Light coercion only — the heavy normalization (log1p, z-score, one-hot, JSON
    expansion, clipping) is the adapter's job. Here we just guarantee the Python
    type family the adapter expects, and turn anything malformed into a clean
    missing value rather than letting a bad cell poison the row.
    """
    if value is None:
        return None
    if mtype == "flag":
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return 1.0 if float(value) != 0.0 else 0.0
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("true", "yes", "1", "y", "t"):
                return 1.0
            if v in ("false", "no", "0", "n", "f"):
                return 0.0
        return None
    if mtype in _NUMERIC_TYPES:
        if isinstance(value, bool):  # bool is an int subclass — reject it here
            return None
        if isinstance(value, (int, float)):
            return float(value) if math.isfinite(float(value)) else None
        if isinstance(value, str):
            try:
                f = float(value.strip())
            except ValueError:
                return None
            return f if math.isfinite(f) else None
        return None
    if mtype == "categorical":
        if isinstance(value, str):
            return value.strip() or None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return None
    if mtype in _JSON_TYPES:
        obj = value
        if isinstance(obj, str):
            try:
                obj = json.loads(obj)
            except (ValueError, TypeError):
                return None
        if not isinstance(obj, dict):
            return None
        clean: dict[str, float] = {}
        for k, v in obj.items():
            if isinstance(v, bool) or not isinstance(v, (int, float)):
                continue
            fv = float(v)
            if math.isfinite(fv):
                clean[str(k)] = fv
        return clean or None
    return None


def extract_feature_rows(
    entities: list[EntityDocument],
    schema: ExtractionSchema,
    llm: ChatClient | None = None,
) -> list[dict[str, Any]]:
    """Extract one bounded feature row per entity, in ``run_query`` shape.

    Each returned row is ``{schema.entity_key: <id>, <field>: <value|None>, ...}``
    carrying EXACTLY ``schema.entity_key`` + ``schema.fields`` — no model-invented
    columns. One deterministic (temperature=0) LLM call per entity. A field the
    model omits or returns an unusable value for is None, never fabricated or
    dropped, so every row shares an identical key set.

    Raises ``ValueError`` for a malformed schema; ``DocumentExtractionError`` if a
    per-entity LLM call fails or can't be parsed.
    """
    schema.validate_closed()
    if not entities:
        return []

    # Construct the client lazily on first real use: a run where every document
    # is empty makes no calls and must not fail just because no provider key is
    # set, and a construction/provider-selection failure surfaces as the
    # documented DocumentExtractionError (502) rather than an uncaught 500.
    client = llm
    allowed = {f.name: f.type for f in schema.fields}
    rows: list[dict[str, Any]] = []

    for entity in entities:
        # Closed row scaffold: every field present, defaulting to missing.
        row: dict[str, Any] = {schema.entity_key: entity.entity_id}
        for f in schema.fields:
            row[f.name] = None

        if entity.text.strip():
            if client is None:
                try:
                    client = get_chat_client()
                except Exception as exc:  # missing key / provider-selection failure
                    raise DocumentExtractionError(
                        f"could not construct extraction LLM client: {exc}"
                    ) from exc
            user_prompt = _build_user_prompt(entity, schema)
            try:
                raw = client.chat_json(
                    messages=[
                        {"role": "system", "content": _SYSTEM},
                        {"role": "user", "content": user_prompt},
                    ],
                    schema=_RawExtraction,
                    temperature=0.0,
                )
            except JSONRepairError as exc:
                raise DocumentExtractionError(
                    f"extraction LLM returned unparseable output for entity "
                    f"{entity.entity_id!r}"
                ) from exc
            except Exception as exc:  # provider/network/key failures
                raise DocumentExtractionError(
                    f"extraction LLM call failed for entity {entity.entity_id!r}: {exc}"
                ) from exc

            # Iterate the MODEL's output but write only into allowed fields, so an
            # invented field is dropped and the row stays closed to the schema.
            for item in raw.values:
                mtype = allowed.get(item.name)
                if mtype is None:
                    continue
                row[item.name] = _coerce(item.value, mtype)

        rows.append(row)

    return rows


def _hashable(value: Any) -> Any:
    """A hashable stand-in for distinct/sample bookkeeping (dicts → JSON str)."""
    try:
        hash(value)
        return value
    except TypeError:
        try:
            return json.dumps(value, sort_keys=True, default=str)
        except (TypeError, ValueError):
            return str(value)


def profile_feature_rows(
    rows: list[dict[str, Any]],
    schema: ExtractionSchema,
) -> tuple[int, list[ColumnProfile]]:
    """Profile extracted rows into the SAME `(row_count, [ColumnProfile])` shape
    the Snowflake preview path emits, so doc-fed columns flow straight into the
    wizard's Map step (suggest_mapping) unchanged.

    Columns are the schema's fields in declared order (NOT the entity key, which
    is an identifier, not a feature) — so the profile is stable even when every
    row is null. ``dtype`` reports the declared metric type; null fraction and
    distinct/sample are computed over the rows.
    """
    n = len(rows)
    profiles: list[ColumnProfile] = []
    for f in schema.fields:
        values = [r.get(f.name) for r in rows]
        non_null = [v for v in values if v is not None]
        non_null_count = len(non_null)
        null_fraction = round(1 - (non_null_count / n), 4) if n else 0.0
        hashed = [_hashable(v) for v in non_null]
        distinct_count = len(set(hashed)) if hashed else 0
        sample_values = list(dict.fromkeys(hashed))[:5] if hashed else None
        profiles.append(
            ColumnProfile(
                name=f.name,
                dtype=f.type,
                non_null_count=non_null_count,
                null_fraction=null_fraction,
                distinct_count=distinct_count,
                sample_values=sample_values,
            )
        )
    return n, profiles


def _build_user_prompt(entity: EntityDocument, schema: ExtractionSchema) -> str:
    lines = ["Fields to extract (return a value or null for each):"]
    for i, f in enumerate(schema.fields, start=1):
        desc = f" — {f.description}" if f.description else ""
        lines.append(f"{i}. {f.name} (type: {f.type}){desc}")
    lines.append("")
    lines.append(f"Documents for entity {entity.entity_id}:")
    lines.append(entity.text)
    return "\n".join(lines)
