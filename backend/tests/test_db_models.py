"""Smoke tests for SQLAlchemy models — schema imports + table definitions."""

from __future__ import annotations

from sidira_simulator.adapters.db_models import (
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
        "crawl_configs",
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
    cols = {c.name: c for c in AgentInstance.__table__.columns}
    assert "persona_pack_version" in cols
    assert "persona_id" in cols
    assert "simulation_id" in cols
    assert "materialization_index" in cols
    assert cols["materialization_index"].nullable is True


def test_agent_feedback_columns() -> None:
    cols = {c.name for c in AgentFeedback.__table__.columns}
    assert {"agent_id", "turn_index", "realistic_flag"} <= cols


def test_customer_clerk_org_id_optional() -> None:
    """Phase 5 wires Clerk; until then clerk_org_id is nullable."""
    col = Customer.__table__.columns["clerk_org_id"]
    assert col.nullable is True


def test_customer_external_id_supports_provider_swap() -> None:
    """Pins the auth-provider portability contract
    (docs/auth-provider-portability.md): ``customers.id`` is the opaque
    internal PK every tenant-scoped table references, and ``clerk_org_id`` is
    a separate unique mapping column — so swapping auth providers is a
    backfill of a new mapping column, never a primary-key migration.
    """
    table = Customer.__table__
    assert [c.name for c in table.primary_key.columns] == ["id"]
    clerk_col = table.columns["clerk_org_id"]
    assert clerk_col.unique is True
    assert clerk_col.primary_key is False
    # Tenant-scoped tables key on the internal id, not a provider id.
    sim_fks = {fk.target_fullname for fk in Simulation.__table__.foreign_keys}
    assert "customers.id" in sim_fks
