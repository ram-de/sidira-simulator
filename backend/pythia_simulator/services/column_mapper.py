"""LLM-assisted mapping of customer columns → Pythia's 7 feature groups.

The 7 groups are fixed (they're the persona-classifier abstraction). Customer
column inventory is variable. This service takes the column list + sample
values and proposes which group each column belongs to. The user reviews and
edits in the UI before the mapping is persisted.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from pythia_simulator.adapters.feature_stores import ColumnProfile
from pythia_simulator.adapters.llm import ChatClient, get_chat_client

FeatureGroup = Literal[
    "demographic_identity",
    "behavioral_patterns",
    "motivations_jtbd",
    "pain_points_friction",
    "value_sensitivity",
    "channel_tech_behavior",
    "loyalty_lifecycle",
]


class ColumnSuggestion(BaseModel):
    column: str
    group: FeatureGroup | None = Field(
        default=None,
        description="Suggested group, or None if the model is uncertain.",
    )
    rationale: str = Field(default="")
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)


class MappingSuggestion(BaseModel):
    suggestions: list[ColumnSuggestion]


_SYSTEM = """You are a data engineer mapping a customer's user-table columns
into Pythia's 7 fixed feature groups. The groups are:

1. demographic_identity — who the user is (age, location, device, identity flags)
2. behavioral_patterns — what they do (orders, frequency, session activity, recency)
3. motivations_jtbd — why they engage (jobs-to-be-done flags, basket types, themes)
4. pain_points_friction — where they struggle (cancellations, refunds, support tickets, errors)
5. value_sensitivity — how they respond to price/promo (PSM scores, promo redemption, fee sensitivity)
6. channel_tech_behavior — how they reach the product (notifications, device, platform, response rates)
7. loyalty_lifecycle — where they are in tenure (lifestage, churn risk, subscription status, points balance)

For each column, propose the best group and a 1-sentence rationale. If a
column is an ID, timestamp, or otherwise unmappable, return group=null with
rationale="unmappable: <reason>". Return strict JSON matching the schema."""


def suggest_mapping(
    columns: list[ColumnProfile],
    llm: ChatClient | None = None,
) -> MappingSuggestion:
    """Single LLM call returns suggestions for all columns at once."""
    client = llm or get_chat_client()
    user_prompt = _build_user_prompt(columns)
    return client.chat_json(
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": user_prompt},
        ],
        schema=MappingSuggestion,
    )


def _build_user_prompt(columns: list[ColumnProfile]) -> str:
    lines = ["Columns to classify (one per line, with type + null fraction + sample values):"]
    for col in columns:
        samples = ", ".join(repr(v) for v in (col.sample_values or [])[:5])
        lines.append(
            f"- {col.name} :: {col.dtype} :: null={col.null_fraction:.2f} :: samples=[{samples}]"
        )
    lines.append("")
    lines.append(
        "Return JSON: "
        '{"suggestions":[{"column":"<name>","group":"<group_or_null>",'
        '"rationale":"<one sentence>","confidence":<0..1>}, ...]}'
    )
    return "\n".join(lines)
