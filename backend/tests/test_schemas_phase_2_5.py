"""Phase 2.5 schema tests (issue #57).

Foundation schema swap: persona_sample_size -> population_size,
plus new optional fields for CIs, behavioral_seeds, identity_seed.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas import (
    AgentInstance,
    AgentInstanceMetadata,
    Hypothesis,
    Persona,
    SimulationRequest,
    SimulationResult,
    Weakness,
)
from sidira_simulator.schemas.persona import BehavioralSeedSchema
from sidira_simulator.schemas.identity import IdentitySeed


def _hypothesis() -> Hypothesis:
    return Hypothesis(capability_name="reorder", prose="x" * 20)


def test_simulation_request_accepts_population_size() -> None:
    req = SimulationRequest(hypothesis=_hypothesis(), population_size=1000)
    assert req.population_size == 1000


def test_simulation_request_rejects_old_field_name() -> None:
    """persona_sample_size is gone — submitting it must raise (model_config: extra='forbid')."""
    with pytest.raises(ValidationError):
        SimulationRequest.model_validate(
            {"hypothesis": _hypothesis().model_dump(), "persona_sample_size": 10}
        )


def test_simulation_request_population_size_bounds() -> None:
    SimulationRequest(hypothesis=_hypothesis(), population_size=1)
    SimulationRequest(hypothesis=_hypothesis(), population_size=10_000_000)
    with pytest.raises(ValidationError):
        SimulationRequest(hypothesis=_hypothesis(), population_size=0)
    with pytest.raises(ValidationError):
        SimulationRequest(hypothesis=_hypothesis(), population_size=10_000_001)


def test_weakness_optional_ci_fields() -> None:
    """frequency/ci_low/ci_high are optional so existing scoring code still validates."""
    w_no_ci = Weakness(category="wrong_metric", summary="x")
    assert w_no_ci.frequency is None
    assert w_no_ci.ci_low is None
    assert w_no_ci.ci_high is None

    w_with_ci = Weakness(
        category="wrong_metric", summary="x", frequency=0.67, ci_low=0.55, ci_high=0.78
    )
    assert w_with_ci.frequency == 0.67
    assert (w_with_ci.ci_low, w_with_ci.ci_high) == (0.55, 0.78)


def test_simulation_result_optional_ci() -> None:
    r_no_ci = SimulationResult(confidence_score=50.0)
    assert r_no_ci.confidence_score_ci is None

    r_with_ci = SimulationResult(confidence_score=50.0, confidence_score_ci=(42.0, 58.0))
    assert r_with_ci.confidence_score_ci == (42.0, 58.0)


def test_persona_accepts_pack_without_behavioral_seeds() -> None:
    """v1.0 packs (no behavioral_seeds field) must keep validating."""
    p = Persona(id="p1", name="P1", description="d")
    assert p.behavioral_seeds is None


def test_persona_accepts_v1_1_pack_with_behavioral_seeds() -> None:
    seeds = BehavioralSeedSchema(
        age_bands=["25-29", "30-34"],
        locale_bands=["US-urban"],
        tenure_bands=["1y-3y"],
        current_state_pool=["active"],
        recent_gripe_pool=["nothing in particular"],
    )
    p = Persona(id="p1", name="P1", description="d", behavioral_seeds=seeds)
    assert p.behavioral_seeds is not None
    assert p.behavioral_seeds.age_bands == ["25-29", "30-34"]


def test_agent_instance_accepts_identity_seed() -> None:
    meta = AgentInstanceMetadata(
        id="a1",
        customer_id="demo",
        simulation_id="s1",
        persona_id="p1",
        persona_pack_version="v_1",
        persona_name="P",
        created_at=datetime.now(),
        last_active_at=datetime.now(),
    )
    seed = IdentitySeed(
        age_band="25-29",
        locale_band="US-urban",
        tenure_band="1y-3y",
        current_state="active",
        recent_gripe="favorite show pulled",
    )
    agent = AgentInstance(
        metadata=meta,
        identity_prompt="...",
        initial_reaction="...",
        identity_seed=seed,
    )
    assert agent.identity_seed is not None
    assert agent.identity_seed.age_band == "25-29"


def test_max_agents_env_defaults_when_malformed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Codex P2: SIDIRA_MAX_AGENTS='abc' must not 500 the POST. Fall back to 50."""
    from fastapi.testclient import TestClient

    from sidira_simulator.main import create_app

    monkeypatch.delenv("PYTHIA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "abc")
    client = TestClient(create_app())
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x" * 20},
            "population_size": 3,
        },
    )
    # 202 = the env-parse fallback worked; 500 = the unhandled ValueError leaked.
    # 409 is acceptable too (no persona pack for demo) -- proves we got past env parse.
    assert resp.status_code in (202, 409), resp.text


def test_max_agents_env_clamped_to_min_one(monkeypatch: pytest.MonkeyPatch) -> None:
    """Codex P2: SIDIRA_MAX_AGENTS=0 must not derive a zero-agent run."""
    from fastapi.testclient import TestClient

    from sidira_simulator.main import create_app

    monkeypatch.delenv("PYTHIA_MAX_AGENTS", raising=False)
    monkeypatch.setenv("SIDIRA_MAX_AGENTS", "0")
    client = TestClient(create_app())
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x" * 20},
            "population_size": 5,
        },
    )
    assert resp.status_code in (202, 409), resp.text


def test_simulation_request_accepts_run_seed() -> None:
    """#5 T5: run_seed is int | None and defaults to None (auto-derive at run time)."""
    # Missing field -> None.
    req_default = SimulationRequest(hypothesis=_hypothesis(), population_size=10)
    assert req_default.run_seed is None

    # Explicit None.
    req_none = SimulationRequest(hypothesis=_hypothesis(), population_size=10, run_seed=None)
    assert req_none.run_seed is None

    # Explicit int -- including large values (sha256-derived ints can exceed int32).
    req_int = SimulationRequest(
        hypothesis=_hypothesis(), population_size=10, run_seed=9_223_372_036_854_775_807
    )
    assert req_int.run_seed == 9_223_372_036_854_775_807


def test_simulation_request_rejects_non_int_run_seed() -> None:
    with pytest.raises(ValidationError):
        SimulationRequest.model_validate(
            {
                "hypothesis": _hypothesis().model_dump(),
                "population_size": 10,
                "run_seed": "not-an-int",
            }
        )
    with pytest.raises(ValidationError):
        SimulationRequest.model_validate(
            {
                "hypothesis": _hypothesis().model_dump(),
                "population_size": 10,
                "run_seed": 3.14,
            }
        )


def test_simulation_request_rejects_out_of_bigint_range_run_seed() -> None:
    """Codex P2: values outside signed BIGINT must fail at request validation,
    not as a database INSERT error."""
    # Just past signed BIGINT max.
    with pytest.raises(ValidationError):
        SimulationRequest(hypothesis=_hypothesis(), population_size=10, run_seed=2**63)
    # Just past signed BIGINT min.
    with pytest.raises(ValidationError):
        SimulationRequest(hypothesis=_hypothesis(), population_size=10, run_seed=-(2**63) - 1)


def test_agent_instance_identity_seed_optional_for_existing_code() -> None:
    """Existing call sites that don't yet emit identity_seed must keep working."""
    meta = AgentInstanceMetadata(
        id="a1",
        customer_id="demo",
        simulation_id="s1",
        persona_id="p1",
        persona_pack_version="v_1",
        persona_name="P",
        created_at=datetime.now(),
        last_active_at=datetime.now(),
    )
    agent = AgentInstance(metadata=meta, identity_prompt="...", initial_reaction="...")
    assert agent.identity_seed is None


# ── Phase 5 #101: SimulationRequest.selected_personas validation ───────────


def test_simulation_request_selected_personas_default_none() -> None:
    """Default is None == 'run against all personas' (backwards-compat)."""
    req = SimulationRequest(hypothesis=_hypothesis(), population_size=10)
    assert req.selected_personas is None


def test_simulation_request_selected_personas_accepts_list() -> None:
    """Non-empty list of persona_ids round-trips through Pydantic unchanged."""
    req = SimulationRequest(
        hypothesis=_hypothesis(),
        population_size=10,
        selected_personas=["p1", "p2"],
    )
    assert req.selected_personas == ["p1", "p2"]


def test_simulation_request_selected_personas_empty_list_rejected() -> None:
    """Empty list is a PM mistake -- reject at the schema layer."""
    with pytest.raises(ValidationError, match="at least one persona_id"):
        SimulationRequest(
            hypothesis=_hypothesis(),
            population_size=10,
            selected_personas=[],
        )


def test_simulation_request_selected_personas_dedupes_duplicates() -> None:
    """Dupes must collapse so a persona's weight isn't double-counted.

    The PM submitting ["p1", "p1", "p2"] almost certainly meant ["p1", "p2"];
    the allocator's renormalize step would otherwise count p1's weight twice
    in the denominator and give it 2/3 of the population instead of 1/2.
    """
    req = SimulationRequest(
        hypothesis=_hypothesis(),
        population_size=10,
        selected_personas=["p1", "p1", "p2"],
    )
    assert req.selected_personas == ["p1", "p2"]
