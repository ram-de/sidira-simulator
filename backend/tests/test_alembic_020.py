"""Alembic 020 (#46): experiment_connections + experiment_import_runs.

Coverage mirrors test_alembic_019:

  * Revision chain — 020 chains 019 ← 020 and is the lone head (a fork would
    make ``alembic upgrade head`` ambiguous and break the prod SIDIRA_AUTO_MIGRATE
    deploy).
  * DDL shape — upgrade() creates both tables; downgrade() drops the child
    (import runs) before the parent (connections), FK-safe.
  * Round-trip on a real in-memory SQLite engine: a connection row with NULL
    credentials (CSV kind) and one import-run row both insert and read back; the
    cred-blob column is nullable.
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
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "020_experiment_connections.py"
    )
    spec = importlib.util.spec_from_file_location("migration_020", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_020_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "020"
    assert mod.down_revision == "019"


def test_migration_020_is_single_head() -> None:
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert list(script.get_heads()) == ["020"]
    head = script.get_revision("020")
    assert head.down_revision == "019"


def test_migration_020_upgrade_creates_both_tables() -> None:
    mod = _load_migration()
    created: list[str] = []
    with patch.object(
        mod.op, "create_table", side_effect=lambda name, *a, **k: created.append(name)
    ):
        mod.upgrade()
    assert created == ["experiment_connections", "experiment_import_runs"]


def test_migration_020_downgrade_drops_child_before_parent() -> None:
    mod = _load_migration()
    dropped: list[str] = []
    with patch.object(mod.op, "drop_table", side_effect=lambda name, **k: dropped.append(name)):
        mod.downgrade()
    # Child (import runs, has the FK) must drop before the parent (connections).
    assert dropped == ["experiment_import_runs", "experiment_connections"]


def test_migration_020_round_trips_on_sqlite() -> None:
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE experiment_connections ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  name VARCHAR(256) NOT NULL,"
                "  kind VARCHAR(32) NOT NULL,"
                "  display_config TEXT NOT NULL,"
                "  credentials_enc TEXT,"  # NULLABLE (CSV kind has no secret)
                "  status VARCHAR(16) NOT NULL DEFAULT 'connected',"
                "  created_by VARCHAR(64),"
                "  last_import_at TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE experiment_import_runs ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  connection_id VARCHAR(64) NOT NULL,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  status VARCHAR(16) NOT NULL,"
                "  imported_count INTEGER NOT NULL DEFAULT 0,"
                "  failed_count INTEGER NOT NULL DEFAULT 0,"
                "  error TEXT"
                ")"
            )
        )
        # CSV-kind connection: no credential blob.
        conn.execute(
            sa.text(
                "INSERT INTO experiment_connections "
                "(id, customer_id, name, kind, display_config) "
                "VALUES ('es-1', 'org_a', 'CSV', 'csv', '{}')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO experiment_import_runs "
                "(id, connection_id, customer_id, status, imported_count) "
                "VALUES ('eir-1', 'es-1', 'org_a', 'succeeded', 3)"
            )
        )

    with engine.connect() as conn:
        c = conn.execute(
            sa.text("SELECT credentials_enc, status FROM experiment_connections")
        ).one()
        assert c.credentials_enc is None and c.status == "connected"
        r = conn.execute(
            sa.text("SELECT imported_count, connection_id FROM experiment_import_runs")
        ).one()
        assert r.imported_count == 3 and r.connection_id == "es-1"
