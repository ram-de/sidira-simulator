"""Tests for Phase 4.6 #88 — ArmSplit on SimulationRequest.

Pin three contracts:
  - Schema validation (treatment_fraction strictly in (0, 1); single-arm
    is the default; legacy requests without arm_split still validate).
  - End-to-end round-trip: POST /simulations with arm_split → treatment_fraction
    persists on the row → GET /simulations/{id} surfaces ArmSplit.
  - Backwards compatibility: a pre-#88 sim (no treatment_fraction column
    value, i.e. NULL) round-trips as arm_split=None on GET.

The actual dual-arm EXECUTION lives in #89; #88 is the schema + persistence
contract, nothing more.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "local-artifacts"
os.environ.setdefault("SIDIRA_LOCAL_ARTIFACTS", str(_FIXTURE_ROOT))

from sidira_simulator.schemas.simulation import (  # noqa: E402
    ArmSplit,
    Hypothesis,
    SimulationRequest,
)

# ──────────────────────────────────────────────────────────────────────
# Schema validation
# ──────────────────────────────────────────────────────────────────────


def _h() -> Hypothesis:
    return Hypothesis(capability_name="reorder", prose="x")


def test_simulation_request_omits_arm_split_by_default() -> None:
    """Pre-#88 callers don't know about arm_split; the field defaults to None
    so existing simulator clients keep working without change."""
    req = SimulationRequest(hypothesis=_h(), population_size=10)
    assert req.arm_split is None


def test_arm_split_explicit_50_50_validates() -> None:
    req = SimulationRequest(
        hypothesis=_h(), population_size=10, arm_split=ArmSplit(treatment_fraction=0.5)
    )
    assert req.arm_split is not None
    assert req.arm_split.treatment_fraction == 0.5


def test_arm_split_treatment_fraction_default_is_half() -> None:
    """ArmSplit() with no args defaults treatment_fraction=0.5 — the wizard's
    v1 default for paired sampling."""
    split = ArmSplit()
    assert split.treatment_fraction == 0.5


def test_arm_split_rejects_fraction_zero() -> None:
    """treatment_fraction=0 means an empty treatment arm — no meaning. Reject
    at validation, not at runtime."""
    with pytest.raises(ValidationError):
        ArmSplit(treatment_fraction=0.0)


def test_arm_split_rejects_fraction_one() -> None:
    """Symmetric: treatment_fraction=1 means an empty control arm. Reject."""
    with pytest.raises(ValidationError):
        ArmSplit(treatment_fraction=1.0)


def test_arm_split_rejects_negative_fraction() -> None:
    with pytest.raises(ValidationError):
        ArmSplit(treatment_fraction=-0.1)


def test_arm_split_rejects_fraction_above_one() -> None:
    with pytest.raises(ValidationError):
        ArmSplit(treatment_fraction=1.5)


def test_arm_split_rejects_extra_fields() -> None:
    """ArmSplit uses extra='forbid' so a typo'd field doesn't silently drop."""
    with pytest.raises(ValidationError):
        ArmSplit.model_validate({"treatment_fraction": 0.5, "control_fraction": 0.5})


def test_arm_split_rejects_non_half_fraction() -> None:
    """Codex P2 on PR #95: non-0.5 splits are silently overridden by the
    per-arm max-agent cap and #90's paired lift formula needs f=0.5
    anyway. Tighten the schema to reject anything else until we have a
    product reason for asymmetric arms AND a scorer that supports them."""
    with pytest.raises(ValidationError):
        ArmSplit(treatment_fraction=0.7)
    with pytest.raises(ValidationError):
        ArmSplit(treatment_fraction=0.3)


# ──────────────────────────────────────────────────────────────────────
# End-to-end round-trip through the API
# ──────────────────────────────────────────────────────────────────────

from sidira_simulator.adapters import llm as llm_mod  # noqa: E402
from sidira_simulator.adapters.repositories import get_in_memory_repos  # noqa: E402
from sidira_simulator.api.deps import get_orchestrator  # noqa: E402
from sidira_simulator.main import app  # noqa: E402
from sidira_simulator.services.simulation_orchestrator import (  # noqa: E402
    SimulationOrchestrator,
)
from sidira_simulator.services.simulation_runner import SimulationRunner  # noqa: E402


class _StubChat:
    """Same shape as test_simulations_api stub — minimal for sim run completion."""

    def __init__(self) -> None:
        self.reply = "I'd give it a shot."
        self.calls: list[list[dict]] = []
        self.json_calls: list[tuple[type, list[dict]]] = []

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls.append(messages)
        return self.reply

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        from sidira_simulator.schemas.scoring import (
            RefinementOutput,
            Sentiment,
            SentimentClassification,
            WeaknessClassification,
        )

        self.json_calls.append((schema, messages))
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=["wrong_cohort"], primary_reason="stub")
        if schema is SentimentClassification:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=0.8, one_line_summary="stub"
            )
        if schema is RefinementOutput:
            return RefinementOutput(suggestions=[])
        raise NotImplementedError(schema)


@pytest.fixture
def client_with_stub(monkeypatch):
    chat = _StubChat()
    monkeypatch.setattr(llm_mod, "get_chat_client", lambda model_id=None: chat)

    customer_repo, sim_repo, agent_repo, _ = get_in_memory_repos()
    customer_repo._customers.clear()
    sim_repo._sims.clear()
    agent_repo._agents.clear()

    runner = SimulationRunner(chat_client=chat)

    from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
    from sidira_simulator.adapters.persona_loader import PersonaPackLoader
    from sidira_simulator.adapters.r2 import LocalArtifactStore

    store = LocalArtifactStore(_FIXTURE_ROOT)
    persona_loader = PersonaPackLoader(store)
    feature_loader = FeaturePackLoader(store)

    def _orch():
        return SimulationOrchestrator(
            customer_repo=customer_repo,
            simulation_repo=sim_repo,
            agent_repo=agent_repo,
            persona_loader=persona_loader,
            feature_pack_loader=feature_loader,
            runner=runner,
        )

    app.dependency_overrides[get_orchestrator] = _orch
    yield TestClient(app), sim_repo
    app.dependency_overrides.clear()


def test_post_simulation_with_arm_split_persists_treatment_fraction(client_with_stub) -> None:
    """POST /simulations with arm_split=0.5 → treatment_fraction column
    populated on the row. The single-arm path is unchanged (treatment_fraction
    stays NULL)."""
    client, sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a one-tap reorder banner.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "arm_split": {"treatment_fraction": 0.5},
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202, resp.text
    sim_id = resp.json()["id"]
    persisted = sim_repo._sims[sim_id]
    assert persisted["treatment_fraction"] == 0.5


def test_post_simulation_without_arm_split_persists_null(client_with_stub) -> None:
    """Backwards-compat: omitting arm_split → treatment_fraction stays None."""
    client, sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {
                "capability_name": "reorder",
                "prose": "Surface a banner.",
                "proposed_figma": {"screens": [], "transitions": []},
            },
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    assert resp.status_code == 202
    sim_id = resp.json()["id"]
    assert sim_repo._sims[sim_id]["treatment_fraction"] is None


def test_get_simulation_surfaces_arm_split_when_ab(client_with_stub) -> None:
    """GET /simulations/{id} returns arm_split populated for A/B sims."""
    client, _sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x"},
            "population_size": 3,
            "arm_split": {"treatment_fraction": 0.5},
            "run_as_generic_reception": True,
        },
    )
    sim_id = resp.json()["id"]
    body = client.get(f"/simulations/{sim_id}").json()
    assert body["arm_split"] == {"treatment_fraction": 0.5}


def test_get_simulation_arm_split_none_for_single_arm(client_with_stub) -> None:
    """GET /simulations/{id} returns arm_split=None for single-arm runs.
    Pinning this so a future refactor doesn't accidentally default to
    {treatment_fraction: 0.5} on legacy rows."""
    client, _sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x"},
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    sim_id = resp.json()["id"]
    body = client.get(f"/simulations/{sim_id}").json()
    assert body["arm_split"] is None


def test_get_simulation_handles_legacy_row_without_treatment_fraction_key(
    client_with_stub,
) -> None:
    """Defensive: a sim row persisted before #88 has no `treatment_fraction`
    key at all in the in-memory dict (legacy fixture or older DB row joined
    via Postgres before the alembic migration runs). The GET path must
    handle this without KeyError."""
    client, sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x"},
            "population_size": 3,
            "run_as_generic_reception": True,
        },
    )
    sim_id = resp.json()["id"]
    # Simulate pre-#88 schema: pop the field entirely.
    sim_repo._sims[sim_id].pop("treatment_fraction", None)
    body = client.get(f"/simulations/{sim_id}").json()
    assert body["arm_split"] is None


def test_post_simulation_rejects_invalid_arm_split_fraction(client_with_stub) -> None:
    """treatment_fraction=0 (empty treatment) gets a 422 at request validation,
    not a runtime crash."""
    client, _sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x"},
            "population_size": 3,
            "arm_split": {"treatment_fraction": 0.0},
        },
    )
    assert resp.status_code == 422


def test_post_simulation_rejects_extra_arm_split_field(client_with_stub) -> None:
    """Extra fields on arm_split (typo, future field that doesn't exist)
    get rejected so a buggy client can't silently drop intent."""
    client, _sim_repo = client_with_stub
    resp = client.post(
        "/simulations",
        json={
            "hypothesis": {"capability_name": "reorder", "prose": "x"},
            "population_size": 3,
            "arm_split": {
                "treatment_fraction": 0.5,
                "stratification_method": "by_persona",  # not a real field
            },
        },
    )
    assert resp.status_code == 422
