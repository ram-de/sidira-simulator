"""Alembic 021 (#48): audit_log.

Coverage mirrors test_alembic_020:

  * Revision chain — 021 chains 020 ← 021 and is the lone head (a fork would make
    ``alembic upgrade head`` ambiguous and break the prod SIDIRA_AUTO_MIGRATE
    deploy).
  * DDL shape — upgrade() creates audit_log; downgrade() drops it.
  * Round-trip on a real in-memory SQLite engine: an append-only insert reads
    back, the metadata column is nullable, and the actor column is nullable.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory


def _load_migration():
    path = (
        Path(__file__).resolve().parents[1] / "alembic" / "versions" / "021_audit_log.py"
    )
    spec = importlib.util.spec_from_file_location("migration_021", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_021_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "021"
    assert mod.down_revision == "020"


def test_migration_021_is_single_head() -> None:
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert list(script.get_heads()) == ["021"]
    head = script.get_revision("021")
    assert head.down_revision == "020"


def test_migration_021_upgrade_creates_audit_log() -> None:
    mod = _load_migration()
    created: list[str] = []
    with patch.object(
        mod.op, "create_table", side_effect=lambda name, *a, **k: created.append(name)
    ):
        mod.upgrade()
    assert created == ["audit_log"]


def test_migration_021_downgrade_drops_audit_log() -> None:
    mod = _load_migration()
    dropped: list[str] = []
    with patch.object(mod.op, "drop_table", side_effect=lambda name, **k: dropped.append(name)):
        mod.downgrade()
    assert dropped == ["audit_log"]


def test_migration_021_round_trips_on_sqlite() -> None:
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE audit_log ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  actor_user_id VARCHAR(64),"  # NULLABLE (future system events)
                "  action VARCHAR(64) NOT NULL,"
                "  target_type VARCHAR(64) NOT NULL,"
                "  target_id VARCHAR(128),"
                "  audit_metadata TEXT,"  # NULLABLE (optional non-secret context)
                "  created_at TIMESTAMP NOT NULL"
                ")"
            )
        )
        # Append a row with NULL actor + NULL metadata (the minimal shape).
        conn.execute(
            sa.text(
                "INSERT INTO audit_log "
                "(id, customer_id, action, target_type, target_id, created_at) "
                "VALUES ('al-1', 'org_a', 'experiment_source.created', "
                "'experiment_source', 'es-1', CURRENT_TIMESTAMP)"
            )
        )

    with engine.connect() as conn:
        r = conn.execute(
            sa.text(
                "SELECT actor_user_id, action, target_id, audit_metadata "
                "FROM audit_log"
            )
        ).one()
        assert r.actor_user_id is None
        assert r.action == "experiment_source.created"
        assert r.target_id == "es-1"
        assert r.audit_metadata is None
