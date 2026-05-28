"""Repository smoke tests against the in-memory implementations.

Postgres-backed repos satisfy the same Protocol; integration tests against a
real DB land in Phase 2-integration after docker-compose is set up.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sidira_simulator.adapters.repositories import (
    InMemoryAgentFeedbackRepo,
    InMemoryAgentInstanceRepo,
    InMemoryCustomerRepo,
    InMemorySimulationRepo,
)


@pytest.fixture
def customers() -> InMemoryCustomerRepo:
    return InMemoryCustomerRepo()


@pytest.fixture
def simulations() -> InMemorySimulationRepo:
    return InMemorySimulationRepo()


@pytest.fixture
def agents() -> InMemoryAgentInstanceRepo:
    return InMemoryAgentInstanceRepo()


@pytest.fixture
def feedback() -> InMemoryAgentFeedbackRepo:
    return InMemoryAgentFeedbackRepo()


@pytest.mark.asyncio
async def test_customer_ensure_exists_is_idempotent(customers: InMemoryCustomerRepo) -> None:
    await customers.ensure_exists("demo", name="Demo customer")
    await customers.ensure_exists("demo", name="Should not overwrite")
    # No assertion needed beyond not raising — idempotency is the contract.


@pytest.mark.asyncio
async def test_simulation_create_then_get(simulations: InMemorySimulationRepo) -> None:
    await simulations.create(
        sim_id="sim-1",
        customer_id="demo",
        persona_pack_version="v_1",
        feature_pack_version="2026-W21",
        hypothesis_json={"capability_name": "reorder", "prose": "test"},
    )
    row = await simulations.get("sim-1", "demo")
    assert row is not None
    assert row["status"] == "pending"
    assert row["persona_pack_version"] == "v_1"
    assert row["hypothesis_json"]["capability_name"] == "reorder"


@pytest.mark.asyncio
async def test_simulation_scoped_by_customer(simulations: InMemorySimulationRepo) -> None:
    """A simulation created for one customer must not be visible to another."""
    await simulations.create(
        sim_id="sim-1",
        customer_id="demo",
        persona_pack_version="v_1",
        feature_pack_version="2026-W21",
        hypothesis_json={},
    )
    assert await simulations.get("sim-1", "other-customer") is None


@pytest.mark.asyncio
async def test_simulation_update_status_with_result(
    simulations: InMemorySimulationRepo,
) -> None:
    await simulations.create(
        sim_id="sim-2",
        customer_id="demo",
        persona_pack_version="v_1",
        feature_pack_version="2026-W21",
        hypothesis_json={},
    )
    await simulations.update_status(
        "sim-2",
        "demo",
        "complete",
        result_json={"confidence_score": 82.0, "weaknesses": [], "refinement_suggestions": []},
        completed_at=datetime.now(timezone.utc),
    )
    row = await simulations.get("sim-2", "demo")
    assert row["status"] == "complete"
    assert row["result_json"]["confidence_score"] == 82.0


@pytest.mark.asyncio
async def test_agent_list_for_simulation(
    agents: InMemoryAgentInstanceRepo,
) -> None:
    await agents.create(
        {
            "id": "a-1",
            "customer_id": "demo",
            "simulation_id": "sim-1",
            "persona_id": "maya",
            "persona_pack_version": "v_1",
            "persona_name": "Maya",
            "created_at": datetime.now(timezone.utc),
            "last_active_at": datetime.now(timezone.utc),
            "message_count": 0,
        }
    )
    await agents.create(
        {
            "id": "a-2",
            "customer_id": "demo",
            "simulation_id": "sim-1",
            "persona_id": "dom",
            "persona_pack_version": "v_1",
            "persona_name": "Dom",
            "created_at": datetime.now(timezone.utc),
            "last_active_at": datetime.now(timezone.utc),
            "message_count": 0,
        }
    )
    rows = await agents.list_for_simulation("sim-1", "demo")
    assert {r["id"] for r in rows} == {"a-1", "a-2"}


@pytest.mark.asyncio
async def test_agent_touch_increments_message_count(
    agents: InMemoryAgentInstanceRepo,
) -> None:
    await agents.create(
        {
            "id": "a-1",
            "customer_id": "demo",
            "simulation_id": "sim-1",
            "persona_id": "maya",
            "persona_pack_version": "v_1",
            "persona_name": "Maya",
            "created_at": datetime.now(timezone.utc),
            "last_active_at": datetime.now(timezone.utc),
            "message_count": 0,
        }
    )
    await agents.touch("a-1", "demo")
    await agents.touch("a-1", "demo")
    row = await agents.get("a-1", "demo")
    assert row["message_count"] == 2


@pytest.mark.asyncio
async def test_feedback_record(feedback: InMemoryAgentFeedbackRepo) -> None:
    await feedback.record(
        feedback_id="fb-1",
        customer_id="demo",
        agent_id="a-1",
        turn_index=0,
        realistic_flag=True,
    )
    assert len(feedback._feedback) == 1
    assert feedback._feedback[0]["realistic_flag"] is True
