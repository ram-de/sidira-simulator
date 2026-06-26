"""Field mapping + Experiment construction (#19) — the firewall boundary.

This is where a source row (a ``{column -> value}`` dict from CSV / SQL / a
Statsig API payload, all normalized to strings) becomes a validated
:class:`~sidira_simulator.schemas.experiment_memory.Experiment`. It is the ONLY
place that crosses the two-table firewall, and it crosses it by a pure rename:
the INPUT columns and the OUTCOME columns are read independently and never
derived from one another. No outcome is inferred from an input; no input is
back-filled from an outcome. Deterministic, zero-LLM.

Everything here is best-effort-honest: a row that can't be coerced to the schema
yields a :class:`RowError` rather than a silently fabricated value.
"""

from __future__ import annotations

from datetime import date as _date

from sidira_simulator.schemas.connector import (
    INPUT_FIELDS,
    OUTCOME_FIELDS,
    FieldMapping,
    RowError,
)
from sidira_simulator.schemas.experiment_memory import (
    Experiment,
    ExperimentCategory,
    ExperimentResult,
)

# Required Experiment fields that MUST be present in a mapping for a row to map.
# `variants` is required (>= 2 arms) because an A/B record without arms is not a
# resolved experiment. `id` is synthesized, never mapped.
_REQUIRED = INPUT_FIELDS + OUTCOME_FIELDS

# Loose synonyms used to *suggest* a mapping from CSV headers. The customer
# always confirms/edits the suggestion — this only saves typing, it never
# silently maps a column the customer didn't approve.
_HEADER_SYNONYMS: dict[str, tuple[str, ...]] = {
    "change_description": (
        "change_description", "change", "description", "hypothesis", "test",
        "experiment", "what_changed", "name", "title",
    ),
    "variants": ("variants", "arms", "variations", "treatments", "groups"),
    "primary_metric": (
        "primary_metric", "metric", "oec", "kpi", "goal_metric", "primary",
    ),
    "category": ("category", "type", "kind", "area", "surface"),
    "winner": ("winner", "winning_variant", "won", "decision"),
    "result": ("result", "outcome", "verdict", "status"),
    "effect_size_pct": (
        "effect_size_pct", "effect_size", "effect", "lift", "lift_pct",
        "delta", "delta_pct", "uplift", "impact",
    ),
    "n": ("n", "sample_size", "sample", "participants", "users", "visitors", "count"),
    "date": ("date", "concluded", "end_date", "completed", "ended", "decided"),
}

# How RESULT strings map onto the enum. Win/loss is relative to the treatment.
_RESULT_ALIASES: dict[str, ExperimentResult] = {
    "win": ExperimentResult.WIN,
    "won": ExperimentResult.WIN,
    "winner": ExperimentResult.WIN,
    "positive": ExperimentResult.WIN,
    "success": ExperimentResult.WIN,
    "loss": ExperimentResult.LOSS,
    "lost": ExperimentResult.LOSS,
    "lose": ExperimentResult.LOSS,
    "negative": ExperimentResult.LOSS,
    "fail": ExperimentResult.LOSS,
    "failed": ExperimentResult.LOSS,
    "flat": ExperimentResult.FLAT,
    "neutral": ExperimentResult.FLAT,
    "inconclusive": ExperimentResult.FLAT,
    "no change": ExperimentResult.FLAT,
    "ns": ExperimentResult.FLAT,
    "not significant": ExperimentResult.FLAT,
}

_CATEGORY_ALIASES: dict[str, ExperimentCategory] = {
    "copy": ExperimentCategory.COPY,
    "text": ExperimentCategory.COPY,
    "messaging": ExperimentCategory.COPY,
    "content": ExperimentCategory.COPY,
    "pricing": ExperimentCategory.PRICING,
    "price": ExperimentCategory.PRICING,
    "ui": ExperimentCategory.UI,
    "design": ExperimentCategory.UI,
    "visual": ExperimentCategory.UI,
    "layout": ExperimentCategory.UI,
    "flow": ExperimentCategory.FLOW,
    "funnel": ExperimentCategory.FLOW,
    "journey": ExperimentCategory.FLOW,
    "onboarding": ExperimentCategory.FLOW,
}


def _norm(s: str) -> str:
    return s.strip().lower().replace("-", " ").replace("_", " ")


def suggest_mapping(columns: list[str], delimiter: str = "|") -> FieldMapping:
    """Best-effort header -> Experiment-field mapping for the customer to confirm.

    Only maps a target when a column header clearly matches a known synonym;
    leaves a target unmapped otherwise (the customer fills the gap in the UI). It
    never guesses an outcome from an input column or vice versa.
    """
    norm_cols = {_norm(c): c for c in columns}
    mapping: dict[str, str] = {}
    for target, synonyms in _HEADER_SYNONYMS.items():
        for syn in synonyms:
            key = _norm(syn)
            if key in norm_cols:
                mapping[target] = norm_cols[key]
                break
    return FieldMapping(columns=mapping, variant_delimiter=delimiter)


def missing_required(mapping: FieldMapping) -> list[str]:
    """Required Experiment fields the mapping does not cover (honest, up front)."""
    return [f for f in _REQUIRED if f not in mapping.columns]


def _coerce_result(raw: str) -> ExperimentResult:
    key = _norm(raw)
    if key in _RESULT_ALIASES:
        return _RESULT_ALIASES[key]
    raise ValueError(
        f"unrecognized result {raw!r} (expected one of win/loss/flat or a synonym)"
    )


def _coerce_category(raw: str) -> ExperimentCategory:
    key = _norm(raw)
    if key in _CATEGORY_ALIASES:
        return _CATEGORY_ALIASES[key]
    raise ValueError(
        f"unrecognized category {raw!r} (expected copy/pricing/ui/flow or a synonym)"
    )


def _coerce_float(raw: str, field: str) -> float:
    cleaned = raw.strip().rstrip("%").replace(",", "")
    try:
        return float(cleaned)
    except ValueError as exc:
        raise ValueError(f"{field} {raw!r} is not a number") from exc


def _coerce_int(raw: str, field: str) -> int:
    cleaned = raw.strip().replace(",", "").replace("_", "")
    try:
        value = int(float(cleaned))
    except ValueError as exc:
        raise ValueError(f"{field} {raw!r} is not an integer") from exc
    if value <= 0:
        raise ValueError(f"{field} must be a positive sample size (got {value})")
    return value


def _coerce_date(raw: str) -> str:
    s = raw.strip()
    # Accept ISO YYYY-MM-DD as-is; otherwise validate it parses to a real date.
    try:
        return _date.fromisoformat(s).isoformat()
    except ValueError as exc:
        raise ValueError(
            f"date {raw!r} is not an ISO date (expected YYYY-MM-DD)"
        ) from exc


def map_row(
    row: dict[str, str], mapping: FieldMapping, *, row_index: int, id_prefix: str
) -> Experiment | RowError:
    """Map ONE normalized source row to an Experiment, or report why it failed.

    INPUT and OUTCOME fields are read independently from their mapped columns —
    the firewall is enforced structurally: this function never looks at an
    outcome value to populate an input field (or vice versa).
    """
    cols = mapping.columns

    def get(field: str) -> str:
        src = cols[field]
        return (row.get(src) or "").strip()

    missing = missing_required(mapping)
    if missing:
        return RowError(
            row=row_index,
            message=f"mapping is missing required fields: {', '.join(missing)}",
        )

    try:
        # ── INPUT side ──────────────────────────────────────────────────────
        change_description = get("change_description")
        if not change_description:
            raise ValueError("change_description is empty")
        variants_raw = get("variants")
        variants = [
            v.strip() for v in variants_raw.split(mapping.variant_delimiter) if v.strip()
        ]
        if len(variants) < 2:
            raise ValueError(
                "variants must list at least two arms "
                f"(split on {mapping.variant_delimiter!r}; got {variants_raw!r})"
            )
        primary_metric = get("primary_metric")
        if not primary_metric:
            raise ValueError("primary_metric is empty")
        category = _coerce_category(get("category"))

        # ── OUTCOME side (read independently — never derived from input) ─────
        winner = get("winner") or "no winner"
        result = _coerce_result(get("result"))
        effect_size_pct = _coerce_float(get("effect_size_pct"), "effect_size_pct")
        n = _coerce_int(get("n"), "n")
        date = _coerce_date(get("date"))
    except ValueError as exc:
        return RowError(row=row_index, message=str(exc))

    return Experiment(
        id=f"{id_prefix}-{row_index:04d}",
        change_description=change_description,
        variants=variants,
        primary_metric=primary_metric,
        category=category,
        winner=winner,
        result=result,
        effect_size_pct=effect_size_pct,
        n=n,
        date=date,
    )


def map_rows(
    rows: list[dict[str, str]], mapping: FieldMapping, *, id_prefix: str
) -> tuple[list[Experiment], list[RowError]]:
    """Map every source row; return (mapped experiments, per-row errors).

    Order-preserving and total: every input row produces exactly one of an
    Experiment or a RowError — nothing is silently dropped.
    """
    experiments: list[Experiment] = []
    errors: list[RowError] = []
    for i, row in enumerate(rows, start=1):
        outcome = map_row(row, mapping, row_index=i, id_prefix=id_prefix)
        if isinstance(outcome, RowError):
            errors.append(outcome)
        else:
            experiments.append(outcome)
    return experiments, errors
