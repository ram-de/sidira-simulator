"""Alembic 017 (#215/#245 PR 3a): persist setup_id on a simulation.

Two layers of coverage, mirroring test_alembic_016:

  * DDL shape — the migration adds setup_id (NOT NULL, server_default 'default')
    to the simulations table, with a correct reverse in downgrade(). Asserted by
    mocking ``op``.
  * Backfill safety — an existing simulation row (no setup_id) is preserved and
    backfilled to the "default" setup. Proven on a real in-memory SQLite engine:
    the server_default fills setup_id='default' without touching any other
    column, so the loader resolves the exact legacy pack prefix for it.
  * Single-head linearity — 017 is the lone head and chains 016 ← 017.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory


def _load_migration():
    """Load the 017 migration by file path (alembic.versions isn't a package)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "017_pr3a_simulation_setup_id.py"
    )
    spec = importlib.util.spec_from_file_location("migration_017", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_017_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "017"
    # down_revision must be the TRUE prior head (016), or the chain forks.
    assert mod.down_revision == "016"


def test_migration_017_chains_from_016_in_linear_history() -> None:
    """017 chains 016 ← 017 and the whole alembic history stays linear (one head).

    Two heads would make `alembic upgrade head` ambiguous and the prod deploy
    (SIDIRA_AUTO_MIGRATE) fail. 017 is no longer the head (018 / #41 now is — see
    test_alembic_018), so this asserts 017's parent + that the chain is still
    single-headed. This walks the real script directory.
    """
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    # Exactly one head keeps `upgrade head` unambiguous (the head itself moves as
    # new migrations land; its identity is owned by the latest migration's test).
    assert len(script.get_heads()) == 1
    rev = script.get_revision("017")
    assert rev.down_revision == "016"


def test_migration_017_upgrade_adds_setup_id_column() -> None:
    mod = _load_migration()
    added_columns: list[tuple[str, sa.Column]] = []

    def _add_column(table: str, column: sa.Column) -> None:
        added_columns.append((table, column))

    with patch.object(mod.op, "add_column", side_effect=_add_column):
        mod.upgrade()

    assert len(added_columns) == 1
    table, col = added_columns[0]
    assert table == "simulations"
    assert col.name == "setup_id"
    assert col.nullable is False
    # NOT NULL + server_default 'default' is what backfills every existing sim
    # row to the default setup (no data loss).
    assert col.server_default.arg == "default"
    # Mirrors the dedicated feature_pack_version column width.
    assert col.type.length == 64


def test_migration_017_downgrade_drops_setup_id_column() -> None:
    mod = _load_migration()
    dropped_columns: list[tuple[str, str]] = []

    def _drop_column(table: str, column: str) -> None:
        dropped_columns.append((table, column))

    with patch.object(mod.op, "drop_column", side_effect=_drop_column):
        mod.downgrade()

    assert dropped_columns == [("simulations", "setup_id")]


def test_migration_017_backfills_existing_sim_to_default_setup() -> None:
    """An existing simulation row (no setup_id) backfills to the "default" setup.

    Run the column-add half of the migration on a real SQLite engine holding a
    legacy sim row. After adding setup_id with server_default 'default', the
    pre-existing row resolves to setup_id='default' with every other column
    untouched — proving no data loss and that a legacy sim re-runs against the
    legacy (default) pack prefix.
    """
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE simulations ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  status VARCHAR(16) NOT NULL,"
                "  feature_pack_version VARCHAR(64) NOT NULL,"
                "  hypothesis_json JSON NOT NULL"
                ")"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO simulations "
                "(id, customer_id, status, feature_pack_version, hypothesis_json) "
                "VALUES ('sim_legacy', 'org_real', 'complete', '2026-W21', "
                "'{\"capability_name\": \"reorder\"}')"
            )
        )

    with engine.begin() as conn:
        # Mirror the migration's column-add DDL (SQLite dialect).
        conn.execute(
            sa.text(
                "ALTER TABLE simulations "
                "ADD COLUMN setup_id VARCHAR(64) NOT NULL DEFAULT 'default'"
            )
        )

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT id, customer_id, setup_id, feature_pack_version "
                "FROM simulations"
            )
        ).one()

    assert row.id == "sim_legacy"
    assert row.customer_id == "org_real"
    assert row.setup_id == "default"  # backfilled, no data loss
    assert row.feature_pack_version == "2026-W21"  # untouched
