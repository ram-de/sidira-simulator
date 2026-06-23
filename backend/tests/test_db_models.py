"""Smoke tests for SQLAlchemy models — schema imports + table definitions."""

from __future__ import annotations

from sidira_simulator.adapters.db_models import (
    AgentFeedback,
    AgentInstance,
    Base,
    CrawlConfig,
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
        "crawl_runs",
        "feature_store_connections",
        "persona_build_runs",
        # #214 — soft-delete marker hiding a Feature Pack version from the Library.
        "archived_feature_packs",
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


def test_crawl_config_has_composite_setup_key() -> None:
    """#215/#245 PR1: crawl_configs is keyed by (customer_id, setup_id) and
    carries a nullable display name. setup_id is NOT NULL with a 'default'
    server default so old single-key callers and the backfilled prod row both
    resolve to the default setup."""
    cols = {c.name: c for c in CrawlConfig.__table__.columns}
    pk_cols = {c.name for c in CrawlConfig.__table__.primary_key.columns}
    assert pk_cols == {"customer_id", "setup_id"}
    assert cols["setup_id"].nullable is False
    assert cols["setup_id"].server_default.arg == "default"
    assert cols["name"].nullable is True


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
