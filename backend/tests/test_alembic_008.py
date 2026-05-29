"""Alembic 008 (#68): agent_instances.materialization_index INT NULL."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa


def _load_migration():
    """Load the 008 migration by file path (alembic.versions isn't a package)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "008_phase_5a_agent_materialization_index.py"
    )
    spec = importlib.util.spec_from_file_location("migration_008", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_008_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "008"
    assert mod.down_revision == "007"


def test_migration_008_upgrade_adds_materialization_index_column_and_index() -> None:
    mod = _load_migration()
    added_columns: list[tuple[str, sa.Column]] = []
    created_indexes: list[tuple[str, str, list[str]]] = []

    def _add_column(table: str, column: sa.Column) -> None:
        added_columns.append((table, column))

    def _create_index(name: str, table: str, columns: list[str]) -> None:
        created_indexes.append((name, table, columns))

    with (
        patch.object(mod.op, "add_column", side_effect=_add_column),
        patch.object(mod.op, "create_index", side_effect=_create_index),
    ):
        mod.upgrade()

    assert len(added_columns) == 1
    table, column = added_columns[0]
    assert table == "agent_instances"
    assert column.name == "materialization_index"
    assert isinstance(column.type, sa.Integer)
    assert column.nullable is True
    assert created_indexes == [
        (
            "ix_agent_instances_simulation_materialization",
            "agent_instances",
            ["simulation_id", "materialization_index"],
        )
    ]


def test_migration_008_downgrade_removes_index_and_column() -> None:
    mod = _load_migration()
    dropped_indexes: list[tuple[str, str | None]] = []
    dropped_columns: list[tuple[str, str]] = []

    def _drop_index(name: str, table_name: str | None = None) -> None:
        dropped_indexes.append((name, table_name))

    def _drop_column(table: str, column: str) -> None:
        dropped_columns.append((table, column))

    with (
        patch.object(mod.op, "drop_index", side_effect=_drop_index),
        patch.object(mod.op, "drop_column", side_effect=_drop_column),
    ):
        mod.downgrade()

    assert dropped_indexes == [("ix_agent_instances_simulation_materialization", "agent_instances")]
    assert dropped_columns == [("agent_instances", "materialization_index")]
