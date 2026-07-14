"""Direction-only output contract tests (Epic #538, ticket #545).

Pure: no R2, no live LLM. Covers the acceptance criterion (the schema STRUCTURALLY
forbids a point-estimate magnitude), the DecisionResult → DirectionVerdict builder,
SimulationResult backward-compat, and the sidecar persist/read round-trip against a
temp filesystem store.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.simulation import SimulationResult
from sidira_simulator.schemas.verdict import (
    DirectionVerdict,
    GuardrailMetric,
    screen_action_from_verdict,
)

# ── the acceptance criterion: no magnitude field, structurally ────────────────


@pytest.mark.parametrize("bad_kwarg", ["magnitude", "ate", "lift", "effect_size", "point_estimate"])
def test_direction_verdict_forbids_magnitude(bad_kwarg):
    """extra='forbid' + NO float field → any point-estimate kwarg raises."""
    with pytest.raises(ValidationError):
        DirectionVerdict(
            direction="positive",
            caution="none",
            confidence="high",
            label="verified verdict",
            source="grounded",
            **{bad_kwarg: 0.4},
        )


def test_direction_verdict_has_no_float_field():
    """Belt-and-braces: not one field on the contract is a float/number."""
    for name, fld in DirectionVerdict.model_fields.items():
        assert fld.annotation is not float, f"{name} must not be a float"
        assert fld.annotation is not int, f"{name} must not be an int"


def test_guardrail_metric_forbids_magnitude():
    with pytest.raises(ValidationError):
        GuardrailMetric(name="ad_impressions", role="sibling", magnitude=0.1)


@pytest.mark.parametrize(
    "kwargs",
    [
        # confidence inconsistent with caution
        dict(direction="positive", caution="none", confidence="low", label="x", source="grounded"),
        dict(direction=None, caution="hard", confidence="high", label="x", source="llm_fallback"),
        # a trustworthy verdict with no direction
        dict(direction=None, caution="none", confidence="high", label="x", source="grounded"),
    ],
)
def test_direction_verdict_rejects_inconsistent_invariants(kwargs):
    """A hand-corrupted sidecar (bad confidence/caution or trustworthy-no-sign) is rejected."""
    with pytest.raises(ValidationError):
        DirectionVerdict(**kwargs)


def test_direction_verdict_valid_construction():
    v = DirectionVerdict(
        direction=None,
        caution="hard",
        confidence="low",
        label="inconclusive — test it",
        source="llm_fallback",
        unverified=True,
    )
    assert v.direction is None and v.caution == "hard" and v.unverified is True


# ── SimulationResult backward-compat (additive, migration-free) ───────────────


def test_simulation_result_decision_verdict_defaults_none():
    r = SimulationResult(confidence_score=72.0)
    assert r.decision_verdict is None


def test_simulation_result_loads_old_result_json_without_key():
    """An older result_json dict (no decision_verdict key) loads unchanged."""
    old = {
        "confidence_score": 55.0,
        "weaknesses": [],
        "refinement_suggestions": [],
    }
    r = SimulationResult(**old)
    assert r.decision_verdict is None
    assert r.confidence_score == 55.0


def test_legacy_sidecar_without_gap_reason_parses():
    """A sidecar persisted BEFORE the field existed parses with reason=None."""
    legacy = {
        "direction": "positive",
        "caution": "none",
        "confidence": "high",
        "label": "verified verdict",
        "source": "grounded",
        "watchdog_verdict": "CONFIRMS",
        "unverified": False,
        "guardrails": [],
    }
    v = DirectionVerdict.model_validate(legacy)
    assert v.grounding_gap_reason is None


# ── screen action: KILL / PASS / ABSTAIN mapping (pivot contract) ─────────────


def _mk(direction, caution, source="grounded", label="x"):
    """Build a validator-consistent DirectionVerdict (confidence derives from caution)."""
    confidence = "high" if caution == "none" else "low"
    return DirectionVerdict(
        direction=direction,
        caution=caution,
        confidence=confidence,
        label=label,
        source=source,
    )


@pytest.mark.parametrize(
    "direction, caution, source, expected",
    [
        # KILL: ONLY a grounded, high-confidence negative (confident loser)
        ("negative", "none", "grounded", "KILL"),
        # codex P2: an UNGROUNDED negative+none (malformed sidecar) must NOT kill
        ("negative", "none", "llm_fallback", "PASS"),
        # PASS: predicted winner
        ("positive", "none", "grounded", "PASS"),
        # PASS: a negative that is NOT grounded-confident never kills (safety-first)
        ("negative", "moderate", "llm_fallback", "PASS"),
        # PASS: unverified positive lean
        ("positive", "moderate", "llm_fallback", "PASS"),
        # ABSTAIN: no confident sign (canonical inconclusive)
        (None, "hard", "llm_fallback", "ABSTAIN"),
    ],
)
def test_screen_action_mapping(direction, caution, source, expected):
    v = _mk(direction, caution, source=source)
    assert v.screen_action == expected
    assert screen_action_from_verdict(v) == expected


def test_screen_action_serializes_on_the_contract():
    v = _mk("negative", "none")
    assert v.model_dump()["screen_action"] == "KILL"
    assert '"screen_action":"KILL"' in v.model_dump_json().replace(" ", "")


def test_low_confidence_negative_never_kills():
    """FN ceiling before coverage: raw/low-confidence signal must not KILL."""
    assert _mk("negative", "moderate", source="llm_fallback").screen_action != "KILL"
