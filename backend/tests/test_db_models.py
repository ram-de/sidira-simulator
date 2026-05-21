"""Smoke tests for SQLAlchemy models — schema imports + table definitions."""

from __future__ import annotations

from pythia_simulator.adapters.db_models import (
    AgentFeedback,
    AgentInstance,
    Base,
    Customer,
    Simulation,
)


def test_models_import_and_register_with_metadata() -> None:
    """Every model must be attached to the shared Base.metadata so Alembic sees them."""
    table_names = set(Base.metadata.tables.keys())
    assert table_names == {
        "customers",
        "simulations",
        "agent_instances",
        "agent_feedback",
    }


def test_simulations_has_required_columns() -> None:
    cols = {c.name for c in Simulation.__table__.columns}
    assert {
        "id",
        "customer_id",
        "status",
        "persona_pack_version",
        "feature_pack_version",
        "hypothesis_json",
        "result_json",
        "parent_simulation_id",
        "error",
        "created_at",
        "completed_at",
    } <= cols


def test_agent_instances_has_persona_pack_version_for_identity_pinning() -> None:
    """The identity-continuity guarantee depends on persona_pack_version being
    persisted so the AgentInstance is permanently pinned to one frozen identity.
    """
    cols = {c.name for c in AgentInstance.__table__.columns}
    assert "persona_pack_version" in cols
    assert "persona_id" in cols
    assert "simulation_id" in cols


def test_agent_feedback_columns() -> None:
    cols = {c.name for c in AgentFeedback.__table__.columns}
    assert {"agent_id", "turn_index", "realistic_flag"} <= cols


def test_customer_clerk_org_id_optional() -> None:
    """Phase 5 wires Clerk; until then clerk_org_id is nullable."""
    col = Customer.__table__.columns["clerk_org_id"]
    assert col.nullable is True
