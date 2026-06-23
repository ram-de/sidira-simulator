"""Repository smoke tests against the in-memory implementations.

Postgres-backed repos satisfy the same Protocol; integration tests against a
real DB land in Phase 2-integration after docker-compose is set up.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from sidira_simulator.adapters.repositories import (
    DEFAULT_SETUP_ID,
    InMemoryAgentFeedbackRepo,
    InMemoryAgentInstanceRepo,
    InMemoryCrawlConfigRepo,
    InMemoryCustomerRepo,
    InMemoryFeatureStoreConnectionRepo,
    InMemorySimulationRepo,
)


@pytest.fixture
def customers() -> InMemoryCustomerRepo:
    return InMemoryCustomerRepo()


@pytest.fixture
def feature_stores() -> InMemoryFeatureStoreConnectionRepo:
    return InMemoryFeatureStoreConnectionRepo()


_FS_ROW = {
    "id": "fs-abc",
    "customer_id": "demo",
    "name": "prod",
    "kind": "snowflake",
    "account": "acct",
    "user": "u",
    "warehouse": "wh",
    "role": "ro",
    "database": "db",
    "schema": None,
    "password_enc": {"blob": "x"},
}


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


# ── feature-store connection health (#328) ──────────────────────────────────


@pytest.mark.asyncio
async def test_fs_insert_seeds_null_health(
    feature_stores: InMemoryFeatureStoreConnectionRepo,
) -> None:
    """A freshly-inserted row reads as UNTESTED — all health fields null."""
    row = await feature_stores.insert(dict(_FS_ROW))
    assert row["last_test_status"] is None
    assert row["last_tested_at"] is None
    assert row["last_error_kind"] is None
    assert row["last_error_message"] is None


@pytest.mark.asyncio
async def test_fs_record_test_result_ok_and_failed(
    feature_stores: InMemoryFeatureStoreConnectionRepo,
) -> None:
    await feature_stores.insert(dict(_FS_ROW))
    now = datetime.now(timezone.utc)
    assert await feature_stores.record_test_result(
        "fs-abc", "demo", status="failed", tested_at=now,
        error_kind="auth", error_message="bad creds",
    )
    row = await feature_stores.get("fs-abc", "demo")
    assert row["last_test_status"] == "failed"
    assert row["last_tested_at"] == now
    assert row["last_error_kind"] == "auth"
    # A passing test clears the error fields.
    assert await feature_stores.record_test_result(
        "fs-abc", "demo", status="ok", tested_at=now,
        error_kind=None, error_message=None,
    )
    row = await feature_stores.get("fs-abc", "demo")
    assert row["last_test_status"] == "ok"
    assert row["last_error_kind"] is None
    assert row["last_error_message"] is None


@pytest.mark.asyncio
async def test_fs_record_test_result_is_customer_scoped(
    feature_stores: InMemoryFeatureStoreConnectionRepo,
) -> None:
    """Another tenant cannot write health onto a row they don't own (security
    requirement): the call returns False and mutates nothing."""
    await feature_stores.insert(dict(_FS_ROW))
    now = datetime.now(timezone.utc)
    assert not await feature_stores.record_test_result(
        "fs-abc", "intruder", status="ok", tested_at=now,
        error_kind=None, error_message=None,
    )
    # Unknown id is also a no-op False.
    assert not await feature_stores.record_test_result(
        "fs-nope", "demo", status="ok", tested_at=now,
        error_kind=None, error_message=None,
    )
    # The owned row was untouched.
    row = await feature_stores.get("fs-abc", "demo")
    assert row["last_test_status"] is None


# ──────────────────────────────────────────────────────────────────────
# CrawlConfig composite key (#215/#245 PR 1/3)
# ──────────────────────────────────────────────────────────────────────


@pytest.fixture
def crawl_configs() -> InMemoryCrawlConfigRepo:
    return InMemoryCrawlConfigRepo()


@pytest.mark.asyncio
async def test_crawl_config_defaults_to_default_setup(
    crawl_configs: InMemoryCrawlConfigRepo,
) -> None:
    """A caller that passes only customer_id (every existing endpoint) reads and
    writes the reserved "default" setup — identical behavior to pre-composite."""
    assert await crawl_configs.get("demo") is None
    saved = await crawl_configs.upsert("demo", {"walk_depth": 3})
    assert saved["setup_id"] == DEFAULT_SETUP_ID
    got = await crawl_configs.get("demo")
    assert got is not None
    assert got["setup_id"] == DEFAULT_SETUP_ID
    assert got["config_json"] == {"walk_depth": 3}
    # The default setup is reachable both by omission and by explicit id.
    assert await crawl_configs.get("demo", DEFAULT_SETUP_ID) == got


@pytest.mark.asyncio
async def test_crawl_config_upsert_overwrites_same_setup(
    crawl_configs: InMemoryCrawlConfigRepo,
) -> None:
    await crawl_configs.upsert("demo", {"walk_depth": 3})
    await crawl_configs.upsert("demo", {"walk_depth": 6})
    got = await crawl_configs.get("demo")
    assert got["config_json"] == {"walk_depth": 6}
    # Still one row for the default setup.
    assert len(await crawl_configs.list("demo")) == 1


@pytest.mark.asyncio
async def test_two_setups_coexist_for_one_customer(
    crawl_configs: InMemoryCrawlConfigRepo,
) -> None:
    """A second setup_id does not clobber the default — both rows coexist and
    list() returns them for the org (foundational for PR2 CRUD)."""
    await crawl_configs.upsert("demo", {"walk_depth": 3}, name="Default")
    await crawl_configs.upsert("demo", {"walk_depth": 6}, setup_id="checkout", name="Checkout")

    default = await crawl_configs.get("demo")
    checkout = await crawl_configs.get("demo", "checkout")
    assert default["config_json"] == {"walk_depth": 3}
    assert default["name"] == "Default"
    assert checkout["config_json"] == {"walk_depth": 6}
    assert checkout["name"] == "Checkout"

    rows = await crawl_configs.list("demo")
    assert {r["setup_id"] for r in rows} == {DEFAULT_SETUP_ID, "checkout"}


@pytest.mark.asyncio
async def test_crawl_config_list_is_customer_scoped(
    crawl_configs: InMemoryCrawlConfigRepo,
) -> None:
    await crawl_configs.upsert("demo", {"walk_depth": 3})
    await crawl_configs.upsert("other", {"walk_depth": 6})
    rows = await crawl_configs.list("demo")
    assert [r["customer_id"] for r in rows] == ["demo"]
    assert await crawl_configs.list("nobody") == []


@pytest.mark.asyncio
async def test_crawl_config_upsert_preserves_name_on_resave(
    crawl_configs: InMemoryCrawlConfigRepo,
) -> None:
    """Re-saving an existing setup without a name keeps the prior label — the
    PUT /crawl-setup path never supplies a name, so a label set later by CRUD
    must survive a setup re-save."""
    await crawl_configs.upsert("demo", {"walk_depth": 3}, name="My Product")
    await crawl_configs.upsert("demo", {"walk_depth": 6})  # no name
    got = await crawl_configs.get("demo")
    assert got["name"] == "My Product"
    assert got["config_json"] == {"walk_depth": 6}
