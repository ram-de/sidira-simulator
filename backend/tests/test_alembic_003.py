"""Alembic 003 (#5 T5): simulations.run_seed BIGINT NULL.

Exercises upgrade()/downgrade() by patching alembic.op to record operations,
then asserts the migration adds (upgrade) and removes (downgrade) the run_seed
column with the right type/nullability. This is lighter than spinning up a
real Postgres for a single-column ADD, and matches how 002 would have been
tested if it had a sibling test.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa


def _load_migration():
    """Load the 003 migration by file path (alembic.versions isn't a package)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "003_phase_2_5_run_seed.py"
    )
    spec = importlib.util.spec_from_file_location("migration_003", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_003_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "003"
    assert mod.down_revision == "002"


def test_migration_003_upgrade_adds_run_seed_column() -> None:
    mod = _load_migration()
    calls: list[tuple[str, str, sa.Column]] = []

    def _add_column(table: str, column: sa.Column) -> None:
        calls.append(("add", table, column))

    with patch.object(mod.op, "add_column", side_effect=_add_column):
        mod.upgrade()

    assert len(calls) == 1
    op, table, column = calls[0]
    assert op == "add"
    assert table == "simulations"
    assert column.name == "run_seed"
    assert isinstance(column.type, sa.BigInteger)
    assert column.nullable is True


def test_migration_003_downgrade_removes_run_seed_column() -> None:
    mod = _load_migration()
    calls: list[tuple[str, str]] = []

    def _drop_column(table: str, column: str) -> None:
        calls.append((table, column))

    with patch.object(mod.op, "drop_column", side_effect=_drop_column):
        mod.downgrade()

    assert calls == [("simulations", "run_seed")]


def test_simulations_orm_has_run_seed_column() -> None:
    """Sanity: the ORM model and the migration agree on the column."""
    from pythia_simulator.adapters.db_models import Simulation

    cols = {c.name: c for c in Simulation.__table__.columns}
    assert "run_seed" in cols
    assert cols["run_seed"].nullable is True
    assert isinstance(cols["run_seed"].type, sa.BigInteger)
