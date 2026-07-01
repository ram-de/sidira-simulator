"""Direction-only output contract tests (Epic #538, ticket #545).

Pure: no R2, no live LLM. Covers the acceptance criterion (the schema STRUCTURALLY
forbids a point-estimate magnitude), the DecisionResult → DirectionVerdict builder,
SimulationResult backward-compat, and the sidecar persist/read round-trip against a
temp filesystem store.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.adapters.r2 import LocalArtifactStore
from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.schemas.simulation import SimulationResult
from sidira_simulator.schemas.verdict import DirectionVerdict, GuardrailMetric
from sidira_simulator.services.decision_flow import (
    DecisionResult,
    decision_verdict_key,
    read_decision_verdict,
    verdict_from_decision,
    write_decision_verdict,
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
        dict(direction="positive", caution="none", confidence="low",
             label="x", source="grounded"),
        dict(direction=None, caution="hard", confidence="high",
             label="x", source="llm_fallback"),
        # a trustworthy verdict with no direction
        dict(direction=None, caution="none", confidence="high",
             label="x", source="grounded"),
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


# ── the builder: DecisionResult → DirectionVerdict ────────────────────────────


def _spec(**over) -> MechanismSpec:
    base = dict(
        capability_name="difficulty_gate",
        treatment_column="gate_level",
        treatment_contrast="gate 30 vs gate 40",
        outcome_column="day7_retention",
        sibling_metric="day1_retention",
        negative_controls=["prior_sessions", "signup_channel"],
    )
    base.update(over)
    return MechanismSpec(**base)


def _decision(**over) -> DecisionResult:
    base = dict(
        source="grounded",
        direction="positive",
        caution="none",
        label="verified verdict",
        watchdog_verdict="CONFIRMS",
        mechanism_spec=_spec(),
        grounded=None,
        reason="trace",
    )
    base.update(over)
    return DecisionResult(**base)


def test_verdict_from_grounded_confirms():
    """A trustworthy grounded CONFIRMS → verified, high confidence, guardrails."""
    v = verdict_from_decision(_decision())
    assert v.direction == "positive"
    assert v.caution == "none"
    assert v.confidence == "high"
    assert v.source == "grounded"
    assert v.unverified is False
    assert v.watchdog_verdict == "CONFIRMS"
    assert v.label == "verified verdict"
    # guardrails: sibling + both negative controls, NAMES + roles only.
    roles = {(g.name, g.role) for g in v.guardrails}
    assert roles == {
        ("day1_retention", "sibling"),
        ("prior_sessions", "negative_control"),
        ("signup_channel", "negative_control"),
    }
    # No magnitude leaked anywhere.
    dumped = v.model_dump()
    assert not any(isinstance(val, float) for val in dumped.values())


def test_verdict_from_grounded_contradicts_negative():
    v = verdict_from_decision(
        _decision(
            direction="negative",
            label="verified — data overrides intuition",
            watchdog_verdict="CONTRADICTS",
        )
    )
    assert v.direction == "negative"
    assert v.confidence == "high"
    assert v.source == "grounded"
    assert v.unverified is False


def test_verdict_from_abstain():
    """Step-2 grounded-abstain / hard caution → no arrow, low confidence, unverified."""
    v = verdict_from_decision(
        _decision(
            source="llm_fallback",
            direction=None,
            caution="hard",
            label="inconclusive — test it",
            watchdog_verdict="CANT_VALIDATE",
            mechanism_spec=_spec(sibling_metric=None, negative_controls=[]),
        )
    )
    assert v.direction is None
    assert v.caution == "hard"
    assert v.confidence == "low"
    assert v.source == "llm_fallback"
    assert v.unverified is True
    assert v.guardrails == []


def test_verdict_from_unverified_moderate():
    v = verdict_from_decision(
        _decision(
            source="llm_fallback",
            direction="positive",
            caution="moderate",
            label="unverified — hypothesis, not verdict",
            watchdog_verdict="CANT_VALIDATE",
        )
    )
    assert v.unverified is True
    assert v.confidence == "low"
    assert v.direction == "positive"


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


def test_simulation_result_roundtrips_verdict():
    v = verdict_from_decision(_decision())
    r = SimulationResult(confidence_score=80.0, decision_verdict=v)
    reloaded = SimulationResult.model_validate_json(r.model_dump_json())
    assert reloaded.decision_verdict is not None
    assert reloaded.decision_verdict.direction == "positive"


# ── sidecar persist / read round-trip ─────────────────────────────────────────


def test_sidecar_key_matches_per_sim_convention():
    key = decision_verdict_key("cust_1", "sim_abc")
    assert key == "customers/cust_1/simulations/sim_abc/decision_verdict.json"


def test_sidecar_roundtrip(tmp_path):
    store = LocalArtifactStore(tmp_path)
    v = verdict_from_decision(_decision())
    write_decision_verdict(store, "cust_1", "sim_abc", v)
    got = read_decision_verdict(store, "cust_1", "sim_abc")
    assert got is not None
    assert got.direction == "positive"
    assert got.confidence == "high"
    assert {(g.name, g.role) for g in got.guardrails} == {
        (g.name, g.role) for g in v.guardrails
    }


def test_sidecar_read_missing_returns_none(tmp_path):
    store = LocalArtifactStore(tmp_path)
    assert read_decision_verdict(store, "cust_1", "nope") is None


def test_sidecar_read_malformed_returns_none(tmp_path):
    store = LocalArtifactStore(tmp_path)
    store.write_text(decision_verdict_key("cust_1", "bad"), "{not valid json")
    assert read_decision_verdict(store, "cust_1", "bad") is None


# ── the #542 hook writes the sidecar (persist path) ───────────────────────────


def test_run_decision_flow_sync_writes_sidecar(tmp_path, monkeypatch):
    """The #542 hook computes the verdict and persists it beside the run."""
    from sidira_simulator.schemas.simulation import Hypothesis
    from sidira_simulator.services import council as council_mod
    from sidira_simulator.services import decision_flow as df_mod
    from sidira_simulator.services import grounded_predictor as gp_mod
    from sidira_simulator.adapters import r2 as r2_mod
    from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator

    store = LocalArtifactStore(tmp_path)
    # Avoid R2: no manifest, degrade council to NullCouncil, fix the decision.
    monkeypatch.setattr(gp_mod, "load_estimability_manifest", lambda *a, **k: None)
    monkeypatch.setattr(
        council_mod, "build_default_council", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("no keys"))
    )
    monkeypatch.setattr(df_mod, "decide", lambda *a, **k: _decision())
    monkeypatch.setattr(r2_mod, "get_store", lambda: store)

    orch = SimulationOrchestrator.__new__(SimulationOrchestrator)
    orch._run_decision_flow_sync(
        sim_id="sim_xyz",
        customer_id="cust_1",
        hypothesis=Hypothesis(capability_name="difficulty_gate", prose="move the gate earlier"),
        pack_version="v_1",
        setup_id="default",
        model_id=None,
    )

    got = read_decision_verdict(store, "cust_1", "sim_xyz")
    assert got is not None
    assert got.direction == "positive"
    assert got.source == "grounded"


def test_run_decision_flow_sync_persist_failure_never_raises(tmp_path, monkeypatch):
    """A store write failure logs + continues — the hook never raises."""
    from sidira_simulator.schemas.simulation import Hypothesis
    from sidira_simulator.services import council as council_mod
    from sidira_simulator.services import decision_flow as df_mod
    from sidira_simulator.services import grounded_predictor as gp_mod
    from sidira_simulator.adapters import r2 as r2_mod
    from sidira_simulator.services.simulation_orchestrator import SimulationOrchestrator

    class _ExplodingStore:
        def write_text(self, key, body):
            raise OSError("disk full")

    monkeypatch.setattr(gp_mod, "load_estimability_manifest", lambda *a, **k: None)
    monkeypatch.setattr(council_mod, "build_default_council", lambda *a, **k: None)
    monkeypatch.setattr(df_mod, "decide", lambda *a, **k: _decision())
    monkeypatch.setattr(r2_mod, "get_store", lambda: _ExplodingStore())

    orch = SimulationOrchestrator.__new__(SimulationOrchestrator)
    # Must not raise despite the exploding store.
    orch._run_decision_flow_sync(
        sim_id="sim_xyz",
        customer_id="cust_1",
        hypothesis=Hypothesis(capability_name="difficulty_gate", prose="p"),
        pack_version="v_1",
        setup_id="default",
        model_id=None,
    )
