"""
Persona-pack capability scorer (ticket #518).

The information-sufficiency gate (`persona_info_gate.py`) answers ONE hypothesis
at a time. This module runs the SAME presence/variance/support measurement over
the WHOLE feature schema at pack-build time and emits a capability profile:

    "This pack scores N/100. With {present-and-varying classes} it can ground
     DIRECTION for {experiment types}; it must abstain on {types} for lack of
     {classes} or for structural reasons; to extend, ingest {classes} next."

Three sub-scores per feature class (PERSONA_PACK_CAPABILITY_SCORE.md / SPEC §6):
  - presence : a pack column matches the class's name patterns (L0).
  - variance : ≥1 matched column is non-degenerate — reuses persona_info_gate
               `_l1_check` so the build-time and run-time gates are identical (L1).
  - support  : enough rows + column coverage; for `requires_variation` classes
               (A1, A2, B3, B4) ALSO a stronger spread, with the honest caveat
               that true support needs experiment-history / price-variation grain.

status = validated (all three) | present-weak (present, not validated) | absent.
score  = 100 · Σ(weight · status_value) / Σ(weight),  value ∈ {0, 0.5, 1.0}.

The same gate that produces N fires the answer/abstain decision at prediction
time — capability score and run-time decision are one measurement, two moments.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

import pandas as pd

from feature_taxonomy import (
    ADAPTERS,
    EXPERIMENT_REGISTRY,
    TAXONOMY,
    ExperimentType,
    FeatureClass,
)
from persona_info_gate import GateConfig, _l1_check

# Support thresholds (fixed, not tuned post-hoc — see the gate's pre-reg note).
MIN_SUPPORT_ROWS = 30        # a class can't be "validated" on a toy population
MIN_COL_COVERAGE = 0.5       # best matched column must be ≥50% non-null
STRONG_SPREAD_FACTOR = 2.5   # requires_variation: numeric spread must clear floor × this

_STATUS_VALUE = {"absent": 0.0, "present-weak": 0.5, "validated": 1.0}


# --------------------------------------------------------------------------- #
# Per-class status
# --------------------------------------------------------------------------- #
@dataclass
class ClassStatus:
    code: str
    status: str                       # "absent" | "present-weak" | "validated"
    matched_columns: list[str] = field(default_factory=list)
    variance_ok: bool = False
    support_ok: bool = False
    note: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _matches(column: str, patterns: list[str]) -> bool:
    """Case-insensitive: any pattern as a regex (falling back to substring) hits
    the column name."""
    col = column.lower()
    for p in patterns:
        pl = p.lower()
        if pl in col:
            return True
        try:
            if re.search(pl, col):
                return True
        except re.error:
            continue
    return False


def _strong_spread_ok(pack: pd.DataFrame, matched: list[str], cfg: GateConfig) -> bool:
    """≥1 matched NUMERIC column is non-degenerate AND its spread clears the floor
    by `STRONG_SPREAD_FACTOR` — a proxy for the real treatment/price variation a
    requires_variation class needs (presence alone overstates identifiability)."""
    floor = cfg.spread_floor * STRONG_SPREAD_FACTOR
    for col in matched:
        s = pack[col].dropna()
        if pd.api.types.is_numeric_dtype(s):
            ok, measure, _ = _l1_check(pack[col], cfg)
            if ok and measure >= floor:
                return True
    return False


def _matched_columns(
    pack: pd.DataFrame,
    fc: FeatureClass,
    column_map: dict[str, str] | None,
    vertical: str | None,
) -> list[str]:
    """Resolve which pack columns map to a class, by precedence:
      1. `column_map` (col -> class_code) → DIRECT, name-agnostic ("Map step").
      2. `vertical`  → ADAPTERS[vertical][code] ∪ generic_patterns (pattern match).
      3. neither     → generic_patterns only (best-effort fallback).
    """
    if column_map is not None:
        return [c for c in pack.columns if column_map.get(c) == fc.code]
    patterns = list(fc.generic_patterns)
    if vertical is not None:
        patterns = list(ADAPTERS[vertical].get(fc.code, [])) + patterns
    return [c for c in pack.columns if _matches(c, patterns)]


def _score_class(
    pack: pd.DataFrame, fc: FeatureClass, cfg: GateConfig, matched: list[str]
) -> ClassStatus:
    if not matched:
        return ClassStatus(fc.code, "absent", note="no matching columns in pack")

    # L1 variance — reuse the gate's non-degeneracy check on each matched column.
    variance_ok = any(_l1_check(pack[c], cfg)[0] for c in matched)

    # Support — rows + best-column coverage (+ strong spread for variation classes).
    coverage = max(float(pack[c].notna().mean()) for c in matched)
    enough_rows = len(pack) >= MIN_SUPPORT_ROWS
    support_ok = enough_rows and coverage >= MIN_COL_COVERAGE
    note = ""
    if fc.requires_variation:
        spread_ok = _strong_spread_ok(pack, matched, cfg)
        support_ok = support_ok and spread_ok
        note = ("requires historical treatment/price variation — presence+spread is "
                "a PROXY; true support needs experiment-history grain")

    if not enough_rows:
        note = (note + "; " if note else "") + f"only {len(pack)} rows (<{MIN_SUPPORT_ROWS})"
    elif coverage < MIN_COL_COVERAGE:
        note = (note + "; " if note else "") + f"best column coverage {coverage:.0%} (<50%)"

    if variance_ok and support_ok:
        status = "validated"
    else:
        status = "present-weak"
        if not variance_ok:
            note = (note + "; " if note else "") + "present but degenerate (no variance)"
    return ClassStatus(fc.code, status, matched, variance_ok, support_ok, note)


# --------------------------------------------------------------------------- #
# Pack capability profile
# --------------------------------------------------------------------------- #
@dataclass
class CapabilityProfile:
    score: float
    per_class: dict                   # code -> ClassStatus.to_dict()
    answerable: list[str]             # experiment types fully grounded
    partial: list[str]                # some-but-not-all required classes validated
    abstain: list[str]                # none validated, or structurally abstain-only
    gap_list: list[str]               # "ingest {classes} to unlock {type}"
    config: dict
    vertical: str | None = None       # vertical adapter used, if any
    mapping_source: str = "generic"   # "column_map" | "adapter:<vertical>" | "generic"

    def to_dict(self) -> dict:
        return asdict(self)

    def validated_codes(self) -> list[str]:
        return [c for c, s in self.per_class.items() if s["status"] == "validated"]

    def summary(self) -> str:
        validated = self.validated_codes()
        with_clause = ", ".join(validated) if validated else "no validated classes"
        ground_clause = ", ".join(self.answerable + self.partial) or "nothing yet"
        abstain_clause = ", ".join(self.abstain) or "nothing"
        # Prescribe the next ingest = classes named most often across the gap list.
        next_classes = _top_gap_classes(self.gap_list)
        ingest_clause = ", ".join(next_classes) if next_classes else "no further classes"
        if self.mapping_source == "column_map":
            map_clause = "explicit column map"
        elif self.mapping_source.startswith("adapter:"):
            map_clause = f"{self.vertical} adapter"
        else:
            map_clause = "generic patterns only (no vertical/column map supplied)"
        return (
            f"This pack scores {self.score:.0f}/100 [{map_clause}]. "
            f"With {with_clause} it can ground {ground_clause}; "
            f"abstains on {abstain_clause}; "
            f"to extend, ingest {ingest_clause} next."
        )


def _top_gap_classes(gap_list: list[str], top: int = 4) -> list[str]:
    """Pull class codes out of the gap-list strings, ranked by how many experiment
    types they would help unlock."""
    counts: dict[str, int] = {}
    for g in gap_list:
        for code in re.findall(r"\b([A-I]\d{1,2})\b", g):
            counts[code] = counts.get(code, 0) + 1
    return [c for c, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))][:top]


def _classify_experiment(
    name: str, et: ExperimentType, statuses: dict[str, ClassStatus]
) -> tuple[str, list[str]]:
    """Return (bucket, missing_codes). bucket ∈ {answerable, partial, abstain}."""
    required = [c for c in et.required if not c.startswith("H")]
    missing = [c for c in required if statuses[c].status != "validated"]
    if et.abstain_only:
        return "abstain", missing
    if not required:
        return "abstain", missing
    if not missing:
        return "answerable", []
    if len(missing) < len(required):
        return "partial", missing
    return "abstain", missing


def score_pack(
    pack: pd.DataFrame,
    taxonomy: list[FeatureClass] = TAXONOMY,
    registry: dict[str, ExperimentType] = EXPERIMENT_REGISTRY,
    cfg: GateConfig = GateConfig(),
    column_map: dict[str, str] | None = None,
    vertical: str | None = None,
) -> CapabilityProfile:
    """Score a persona/feature pack against the 33-class schema → CapabilityProfile.

    Presence resolution (product-agnostic), in precedence order:
      - `column_map` (dict[column_name -> class_code]) → used DIRECTLY, overriding
        pattern matching. This is the product "Map step" path and is correct
        regardless of how columns are named.
      - `vertical`   → presence patterns = ADAPTERS[vertical][class] ∪ generic_patterns.
        Raises ValueError if the vertical is unknown.
      - neither      → generic_patterns only (best-effort); mapping_source="generic"
        flags that no mapping was supplied.

    Variance/support checks are unchanged (reuse persona_info_gate `_l1_check`).
    """
    if column_map is not None:
        mapping_source = "column_map"
    elif vertical is not None:
        if vertical not in ADAPTERS:
            raise ValueError(
                f"unknown vertical {vertical!r}; known verticals: {sorted(ADAPTERS)}"
            )
        mapping_source = f"adapter:{vertical}"
    else:
        mapping_source = "generic"

    statuses = {
        fc.code: _score_class(
            pack, fc, cfg, _matched_columns(pack, fc, column_map, vertical)
        )
        for fc in taxonomy
    }
    weight = {fc.code: fc.weight for fc in taxonomy}

    num = sum(weight[c] * _STATUS_VALUE[s.status] for c, s in statuses.items())
    den = sum(weight.values())
    score = 100.0 * num / den if den else 0.0

    answerable, partial, abstain, gap_list = [], [], [], []
    for name, et in registry.items():
        bucket, missing = _classify_experiment(name, et, statuses)
        if bucket == "answerable":
            answerable.append(name)
        elif bucket == "partial":
            partial.append(name)
        else:
            abstain.append(name)
        # Prescriptive gaps only for types we could actually unlock by ingesting.
        if missing and not et.abstain_only:
            gap_list.append(f"ingest {missing} to unlock {name}")

    return CapabilityProfile(
        score=round(score, 1),
        per_class={c: s.to_dict() for c, s in statuses.items()},
        answerable=answerable,
        partial=partial,
        abstain=abstain,
        gap_list=gap_list,
        config=asdict(cfg),
        vertical=vertical,
        mapping_source=mapping_source,
    )
