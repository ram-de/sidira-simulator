"""LLM-assisted mapping of customer columns → Pythia's 7 feature groups.

The 7 groups are fixed (they're the persona-classifier abstraction). Customer
column inventory is variable (a wide user table, 50–200 columns). This service
makes a single deterministic LLM call (temperature=0, one-shot) that proposes
which group each column belongs to, with a per-column confidence. The user
reviews and edits in the wizard; overrides are persisted at build time (#24),
not here — this endpoint is pure suggestion and stateless w.r.t. the connection.

The 7 canonical groups (``FeatureGroup``) are the keys downstream consumers
(``persona_builder.BuildConfig.column_mapping``) expect — do NOT rename them.
The public ``MappingSuggestion`` result is the grouped, wizard-facing shape:
each canonical group name maps to its assigned columns, plus an ``unmapped``
bucket for anything the model omitted, was uncertain about, or labelled with a
group outside the canonical 7.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, Field

from sidira_simulator.adapters.feature_stores import ColumnProfile
from sidira_simulator.adapters.llm import ChatClient, JSONRepairError, get_chat_client

FeatureGroup = Literal[
    "demographic_identity",
    "behavioral_patterns",
    "motivations_jtbd",
    "pain_points_friction",
    "value_sensitivity",
    "channel_tech_behavior",
    "loyalty_lifecycle",
]

#: The canonical 7, validated against on parse. Anything else → unmapped.
CANONICAL_GROUPS: tuple[FeatureGroup, ...] = get_args(FeatureGroup)

Confidence = Literal["high", "med", "low"]


class ColumnMappingError(RuntimeError):
    """Raised when the mapping LLM call fails or its output can't be parsed.

    The API turns this into a 502 (bad upstream) — the model/provider, not the
    caller, is at fault.
    """


class ColumnAssignment(BaseModel):
    """A single column placed into a group, with the model's confidence."""

    column: str
    confidence: Confidence = "low"
    rationale: str = ""


class MappingSuggestion(BaseModel):
    """Wizard-facing grouped suggestion.

    Keys are the canonical 7 feature groups; ``unmapped`` collects every column
    the model omitted, was uncertain about, or tagged with an out-of-canon group.
    Every input column appears in exactly one bucket.
    """

    demographic_identity: list[ColumnAssignment] = Field(default_factory=list)
    behavioral_patterns: list[ColumnAssignment] = Field(default_factory=list)
    motivations_jtbd: list[ColumnAssignment] = Field(default_factory=list)
    pain_points_friction: list[ColumnAssignment] = Field(default_factory=list)
    value_sensitivity: list[ColumnAssignment] = Field(default_factory=list)
    channel_tech_behavior: list[ColumnAssignment] = Field(default_factory=list)
    loyalty_lifecycle: list[ColumnAssignment] = Field(default_factory=list)
    unmapped: list[ColumnAssignment] = Field(default_factory=list)

    def add(self, group: FeatureGroup | None, assignment: ColumnAssignment) -> None:
        bucket = getattr(self, group) if group in CANONICAL_GROUPS else self.unmapped
        bucket.append(assignment)


# ── internal LLM-response schema (flat, one entry per column) ────────────────


class _RawSuggestion(BaseModel):
    column: str
    group: str | None = None
    confidence: str = "low"
    rationale: str = ""


class _RawMapping(BaseModel):
    suggestions: list[_RawSuggestion] = Field(default_factory=list)


_SYSTEM = """You are a data engineer mapping a customer's user-table columns
into Pythia's 7 fixed feature groups. The groups (use these exact ids) are:

1. demographic_identity — who the user is (age, location, device, identity flags)
2. behavioral_patterns — what they do (orders, frequency, session activity, recency)
3. motivations_jtbd — why they engage (jobs-to-be-done flags, basket types, themes)
4. pain_points_friction — where they struggle (cancellations, refunds, support tickets, errors)
5. value_sensitivity — how they respond to price/promo (PSM scores, promo redemption, fee sensitivity)
6. channel_tech_behavior — how they reach the product (notifications, device, platform, response rates)
7. loyalty_lifecycle — where they are in tenure (lifestage, churn risk, subscription status, points)

For EACH column, choose the single best group id from the list above, a
confidence of "high", "med", or "low", and a one-sentence rationale. If a
column is an ID, primary/foreign key, timestamp, or otherwise unmappable, set
group to null with confidence "low". Return strict JSON matching the schema —
no prose, no markdown fences."""

_CONFIDENCE_ALIASES = {
    "high": "high",
    "med": "med",
    "medium": "med",
    "mid": "med",
    "moderate": "med",
    "low": "low",
}


def suggest_mapping(
    columns: list[ColumnProfile],
    llm: ChatClient | None = None,
) -> MappingSuggestion:
    """One deterministic LLM call → grouped column suggestions.

    The call is one-shot and temperature=0. Parsing is defensive: any column the
    model omits, marks uncertain, or tags with a group outside the canonical 7
    lands in ``unmapped``, and every input column is guaranteed to appear in
    exactly one bucket. Raises ``ColumnMappingError`` if the LLM call fails or
    its output can't be coerced into the response schema.
    """
    result = MappingSuggestion()
    if not columns:
        return result

    client = llm or get_chat_client()
    user_prompt = _build_user_prompt(columns)
    try:
        raw = client.chat_json(
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": user_prompt},
            ],
            schema=_RawMapping,
            temperature=0.0,
        )
    except JSONRepairError as exc:
        raise ColumnMappingError(
            "column-mapping LLM returned output that could not be parsed"
        ) from exc
    except Exception as exc:  # provider/network/key failures
        raise ColumnMappingError(f"column-mapping LLM call failed: {exc}") from exc

    by_column = {s.column: s for s in raw.suggestions}
    # Iterate the *input* columns so the result is complete and deterministic:
    # a column the model omitted is unmapped, never silently dropped.
    for col in columns:
        suggestion = by_column.get(col.name)
        if suggestion is None:
            result.unmapped.append(ColumnAssignment(column=col.name, confidence="low"))
            continue
        group = _normalize_group(suggestion.group)
        result.add(
            group,
            ColumnAssignment(
                column=col.name,
                confidence=_normalize_confidence(suggestion.confidence),
                rationale=suggestion.rationale or "",
            ),
        )
    return result


def _normalize_group(group: str | None) -> FeatureGroup | None:
    """Return the group only if it's one of the canonical 7, else None (→ unmapped)."""
    if group in CANONICAL_GROUPS:
        return group  # type: ignore[return-value]
    return None


def _normalize_confidence(confidence: str | None) -> Confidence:
    return _CONFIDENCE_ALIASES.get((confidence or "").strip().lower(), "low")


def _build_user_prompt(columns: list[ColumnProfile]) -> str:
    lines = [
        "Columns to classify (one per line: name :: dtype :: null fraction :: sample values):"
    ]
    for col in columns:
        samples = ", ".join(repr(v) for v in (col.sample_values or [])[:3])
        lines.append(
            f"- {col.name} :: {col.dtype} :: null={col.null_fraction:.2f} :: samples=[{samples}]"
        )
    lines.append("")
    lines.append(
        "Return JSON: "
        '{"suggestions":[{"column":"<name>","group":"<group_id_or_null>",'
        '"confidence":"high|med|low","rationale":"<one sentence>"}, ...]}'
    )
    return "\n".join(lines)
