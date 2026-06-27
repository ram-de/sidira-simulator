"""Alembic 018 (#41): conversations + conversation_turns.

Coverage mirrors test_alembic_017:

  * Revision chain — 018 chains 017 ← 018 and is the lone head (a fork would
    make `alembic upgrade head` ambiguous and break the prod SIDIRA_AUTO_MIGRATE
    deploy).
  * DDL shape — upgrade() creates both tables; downgrade() drops them.
  * Round-trip safety — running the migration's DDL on a real in-memory SQLite
    engine yields working tables: a conversation + an ordered turn insert and
    read back, with the citations JSON preserved.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from unittest.mock import patch

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory


def _load_migration():
    """Load the 018 migration by file path (alembic.versions isn't a package)."""
    path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "018_conversations.py"
    )
    spec = importlib.util.spec_from_file_location("migration_018", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_migration_018_revision_chain() -> None:
    mod = _load_migration()
    assert mod.revision == "018"
    assert mod.down_revision == "017"


def test_migration_018_is_single_head() -> None:
    cfg = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    script = ScriptDirectory.from_config(cfg)
    assert list(script.get_heads()) == ["018"]
    head = script.get_revision("018")
    assert head.down_revision == "017"


def test_migration_018_upgrade_creates_both_tables() -> None:
    mod = _load_migration()
    created: list[str] = []

    with patch.object(mod.op, "create_table", side_effect=lambda name, *a, **k: created.append(name)), patch.object(
        mod.op, "create_index"
    ):
        mod.upgrade()

    assert created == ["conversations", "conversation_turns"]


def test_migration_018_downgrade_drops_both_tables() -> None:
    mod = _load_migration()
    dropped: list[str] = []

    with patch.object(mod.op, "drop_table", side_effect=dropped.append), patch.object(
        mod.op, "drop_index"
    ):
        mod.downgrade()

    # Children dropped before parents (FK-safe order).
    assert dropped == ["conversation_turns", "conversations"]


def test_migration_018_tables_round_trip_on_sqlite() -> None:
    """The DDL produces working tables: a thread + an ordered turn with citations
    JSON insert and read back. Proves the schema the route relies on is sound."""
    engine = sa.create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(
            sa.text(
                "CREATE TABLE conversations ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  title VARCHAR(256),"
                "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            sa.text(
                "CREATE TABLE conversation_turns ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  conversation_id VARCHAR(64) NOT NULL,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  turn_index INTEGER NOT NULL,"
                "  question TEXT NOT NULL,"
                "  answer TEXT NOT NULL,"
                "  citations_json JSON,"
                "  used_llm BOOLEAN NOT NULL DEFAULT 0,"
                "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP"
                ")"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id, customer_id, title) "
                "VALUES ('c1', 'org_real', 'Pricing deep-dive')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO conversation_turns "
                "(id, conversation_id, customer_id, turn_index, question, answer, "
                " citations_json, used_llm) "
                "VALUES ('t1', 'c1', 'org_real', 0, 'q?', 'a.', "
                "'[{\"id\": \"sim-1\", \"source\": \"predicted\"}]', 0)"
            )
        )

    with engine.connect() as conn:
        thread = conn.execute(
            sa.text("SELECT id, customer_id, title FROM conversations")
        ).one()
        turn = conn.execute(
            sa.text(
                "SELECT conversation_id, turn_index, question, citations_json "
                "FROM conversation_turns"
            )
        ).one()

    assert thread.id == "c1"
    assert thread.title == "Pricing deep-dive"
    assert turn.conversation_id == "c1"
    assert turn.turn_index == 0
    assert "sim-1" in turn.citations_json
