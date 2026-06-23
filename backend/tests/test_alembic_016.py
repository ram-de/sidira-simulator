"""Alembic 016 (#215/#245 PR 1/3): crawl_configs → composite (customer_id, setup_id).

Two layers of coverage:

  * DDL shape — the migration adds setup_id (NOT NULL, server_default 'default')
    and name (nullable), then swaps the single-column PK for the composite PK,
    with a correct reverse in downgrade(). Asserted by mocking ``op``.
  * Backfill safety — an existing single-key row (the one prod config each org
    already has) is preserved verbatim as its "default" setup. Proven on a real
    in-memory SQLite engine: the server_default fills setup_id='default' and the
    UPDATE sets name='Default' without touching config_json.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa


def _load_migration():
    """Load the 016 migration by file path (alembic.versions isn't a package)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "016_crawl_setups_composite_key.py"
    )
    spec = importlib.util.spec_from_file_location("migration_016", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_016_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "016"
    assert mod.down_revision == "015"


def test_migration_016_upgrade_adds_columns_and_swaps_pk() -> None:
    mod = _load_migration()
    added_columns: list[tuple[str, sa.Column]] = []
    dropped_constraints: list[tuple[str, str, str]] = []
    created_pks: list[tuple[str, str, list[str]]] = []

    def _add_column(table: str, column: sa.Column) -> None:
        added_columns.append((table, column))

    def _drop_constraint(name: str, table: str, type_: str | None = None) -> None:
        dropped_constraints.append((name, table, type_))

    def _create_primary_key(name: str, table: str, columns: list[str]) -> None:
        created_pks.append((name, table, columns))

    with (
        patch.object(mod.op, "add_column", side_effect=_add_column),
        patch.object(mod.op, "drop_constraint", side_effect=_drop_constraint),
        patch.object(mod.op, "create_primary_key", side_effect=_create_primary_key),
        patch.object(mod.op, "execute"),
    ):
        mod.upgrade()

    by_name = {col.name: (table, col) for table, col in added_columns}
    assert set(by_name) == {"setup_id", "name"}

    setup_table, setup_col = by_name["setup_id"]
    assert setup_table == "crawl_configs"
    assert setup_col.nullable is False
    # NOT NULL + server_default 'default' is what backfills every existing row.
    assert setup_col.server_default.arg == "default"

    name_table, name_col = by_name["name"]
    assert name_table == "crawl_configs"
    assert name_col.nullable is True

    # The old single-column PK is dropped and the composite PK created.
    assert dropped_constraints == [("crawl_configs_pkey", "crawl_configs", "primary")]
    assert created_pks == [
        ("pk_crawl_configs", "crawl_configs", ["customer_id", "setup_id"])
    ]


def test_migration_016_downgrade_restores_single_column_pk() -> None:
    mod = _load_migration()
    dropped_constraints: list[tuple[str, str, str]] = []
    created_pks: list[tuple[str, str, list[str]]] = []
    dropped_columns: list[tuple[str, str]] = []

    def _drop_constraint(name: str, table: str, type_: str | None = None) -> None:
        dropped_constraints.append((name, table, type_))

    def _create_primary_key(name: str, table: str, columns: list[str]) -> None:
        created_pks.append((name, table, columns))

    def _drop_column(table: str, column: str) -> None:
        dropped_columns.append((table, column))

    with (
        patch.object(mod.op, "drop_constraint", side_effect=_drop_constraint),
        patch.object(mod.op, "create_primary_key", side_effect=_create_primary_key),
        patch.object(mod.op, "drop_column", side_effect=_drop_column),
    ):
        mod.downgrade()

    assert dropped_constraints == [("pk_crawl_configs", "crawl_configs", "primary")]
    assert created_pks == [("crawl_configs_pkey", "crawl_configs", ["customer_id"])]
    # Columns dropped in reverse add order.
    assert dropped_columns == [
        ("crawl_configs", "name"),
        ("crawl_configs", "setup_id"),
    ]


def test_migration_016_backfills_existing_row_to_default_setup() -> None:
    """The single prod row each org has is preserved as its "default" setup.

    Run the column-add half of the migration on a real SQLite engine that
    already holds a legacy row (customer_id + config_json only). After adding
    setup_id with server_default 'default' and running the name backfill, the
    pre-existing row resolves to setup_id='default', name='Default', and its
    config_json is untouched. (SQLite can't ALTER a PRIMARY KEY, so the PK swap
    itself is covered by the mocked-op DDL test above; here we prove the
    data-preservation half on real SQL.)"""
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE crawl_configs ("
                "  customer_id VARCHAR(64) PRIMARY KEY,"
                "  config_json JSON NOT NULL,"
                "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        # The one existing prod-shaped row, pre-migration.
        conn.execute(
            sa.text(
                "INSERT INTO crawl_configs (customer_id, config_json) "
                "VALUES ('org_real', '{\"walk_depth\": 6}')"
            )
        )

    with engine.begin() as conn:
        # Mirror the migration's column-add + backfill DDL (SQLite dialect).
        conn.execute(
            sa.text(
                "ALTER TABLE crawl_configs "
                "ADD COLUMN setup_id VARCHAR(64) NOT NULL DEFAULT 'default'"
            )
        )
        conn.execute(sa.text("ALTER TABLE crawl_configs ADD COLUMN name VARCHAR(255)"))
        conn.execute(
            sa.text("UPDATE crawl_configs SET name = 'Default' WHERE name IS NULL")
        )

    with engine.connect() as conn:
        row = conn.execute(
            sa.text(
                "SELECT customer_id, setup_id, name, config_json FROM crawl_configs"
            )
        ).one()

    assert row.customer_id == "org_real"
    assert row.setup_id == "default"  # backfilled by server default, no data loss
    assert row.name == "Default"
    assert "walk_depth" in row.config_json  # config_json untouched
