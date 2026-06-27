"""Alembic 019 (#42): conversations.user_id — per-USER (private) scoping.

Coverage mirrors test_alembic_018:

  * Revision chain — 019 chains 018 ← 019 and is the lone head (a fork would
    make `alembic upgrade head` ambiguous and break the prod SIDIRA_AUTO_MIGRATE
    deploy).
  * DDL shape — upgrade() adds the user_id column + its index; downgrade() drops
    both, in FK-safe order.
  * The column is NULLABLE (legacy rows / the pre-#42 demo thread need no
    backfill; new rows always stamp it).
  * Round-trip safety on a real in-memory SQLite engine: a NULL-user legacy row
    and a stamped row both insert and read back.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory


def _load_migration():
    """Load the 019 migration by file path (alembic.versions isn't a package)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "019_conversation_user_id.py"
    )
    spec = importlib.util.spec_from_file_location("migration_019", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_019_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "019"
    assert mod.down_revision == "018"


def test_migration_019_chains_from_018() -> None:
    # 019 is no longer the head (020 chains after it for #46's experiment
    # sources); assert the 018 ← 019 link is intact. Single-head is asserted in
    # test_alembic_020.
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    rev_019 = script.get_revision("019")
    assert rev_019.down_revision == "018"
    assert "019" not in script.get_heads()  # 020 now chains after it


def test_migration_019_upgrade_adds_user_id_column_and_index() -> None:
    mod = _load_migration()
    added_cols: list[tuple[str, sa.Column]] = []
    indexes: list[tuple[str, str, list[str]]] = []

    with patch.object(
        mod.op,
        "add_column",
        side_effect=lambda table, col, *a, **k: added_cols.append((table, col)),
    ), patch.object(
        mod.op,
        "create_index",
        side_effect=lambda name, table, cols, *a, **k: indexes.append(
            (name, table, cols)
        ),
    ):
        mod.upgrade()

    assert len(added_cols) == 1
    table, col = added_cols[0]
    assert table == "conversations"
    assert col.name == "user_id"
    # NULLABLE on purpose — legacy rows need no backfill (see migration docstring).
    assert col.nullable is True
    assert indexes == [("ix_conversations_user_id", "conversations", ["user_id"])]


def test_migration_019_downgrade_drops_index_then_column() -> None:
    mod = _load_migration()
    order: list[str] = []

    with patch.object(
        mod.op, "drop_index", side_effect=lambda name, **k: order.append(f"index:{name}")
    ), patch.object(
        mod.op,
        "drop_column",
        side_effect=lambda table, col, **k: order.append(f"column:{col}"),
    ):
        mod.downgrade()

    assert order == ["index:ix_conversations_user_id", "column:user_id"]


def test_migration_019_user_id_round_trips_on_sqlite() -> None:
    """The added column behaves: a legacy NULL-user row AND a stamped row both
    insert and read back. Proves the schema the per-user repo relies on is sound."""
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        # 018 base + the 019 column.
        conn.execute(
            sa.text(
                "CREATE TABLE conversations ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  user_id VARCHAR(64),"  # NULLABLE (the 019 add)
                "  title VARCHAR(256)"
                ")"
            )
        )
        # Legacy row: no user_id (pre-#42).
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id, customer_id) "
                "VALUES ('legacy', 'org_a')"
            )
        )
        # New row: stamped owner.
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id, customer_id, user_id) "
                "VALUES ('owned', 'org_a', 'user_x')"
            )
        )

    with engine.connect() as conn:
        rows = {
            r.id: r.user_id
            for r in conn.execute(
                sa.text("SELECT id, user_id FROM conversations ORDER BY id")
            )
        }
    assert rows == {"legacy": None, "owned": "user_x"}
