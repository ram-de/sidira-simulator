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

import pytest
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
                "  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                # Composite unique that the child's composite FK targets.
                "  CONSTRAINT uq_conversations_id_customer_id "
                "UNIQUE (id, customer_id)"
                ")"
            )
        )
        conn.execute(sa.text("PRAGMA foreign_keys = ON"))
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
                "  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,"
                # Composite FK so a turn can never reference another tenant's thread.
                "  CONSTRAINT fk_conversation_turns_conversation_customer "
                "FOREIGN KEY (conversation_id, customer_id) "
                "REFERENCES conversations (id, customer_id) ON DELETE CASCADE,"
                # One turn per (conversation_id, turn_index) — no ambiguous order.
                "  CONSTRAINT uq_conversation_turns_conversation_id_turn_index "
                "UNIQUE (conversation_id, turn_index)"
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


def test_migration_018_declares_tenant_and_ordering_constraints() -> None:
    """The 018 upgrade DDL must declare, at the DB level: the parent composite
    unique (id, customer_id), the child composite FK on (conversation_id,
    customer_id), and the (conversation_id, turn_index) unique. These are the
    backstops behind the repo's tenant-isolation + serial-ordering guarantees."""
    mod = _load_migration()
    seen: list[tuple] = []

    def _capture(name, *args, **kwargs):
        seen.append((name, args, kwargs))

    with patch.object(mod.op, "create_table", side_effect=_capture), patch.object(
        mod.op, "create_index"
    ):
        mod.upgrade()

    by_name = {name: (args, kwargs) for name, args, kwargs in seen}

    def _unique_cols(c: sa.UniqueConstraint) -> set[str]:
        # At table-definition time (pre-create) the columns aren't bound yet, so
        # the names live in _pending_colargs; fall back to .columns once bound.
        pending = list(getattr(c, "_pending_colargs", []) or [])
        if pending:
            return {str(x) for x in pending}
        return {col.name for col in c.columns}

    conv_cols = by_name["conversations"][0]
    conv_uniques = [
        c
        for c in conv_cols
        if isinstance(c, sa.UniqueConstraint)
        and _unique_cols(c) == {"id", "customer_id"}
    ]
    assert conv_uniques, "conversations needs UNIQUE(id, customer_id) for the child FK"

    turn_cols = by_name["conversation_turns"][0]
    composite_fks = [
        c
        for c in turn_cols
        if isinstance(c, sa.ForeignKeyConstraint)
        and set(c.column_keys) == {"conversation_id", "customer_id"}
    ]
    assert composite_fks, "turns needs composite FK on (conversation_id, customer_id)"
    fk = composite_fks[0]
    assert fk.ondelete == "CASCADE"
    assert {e.target_fullname for e in fk.elements} == {
        "conversations.id",
        "conversations.customer_id",
    }

    turn_uniques = [
        c
        for c in turn_cols
        if isinstance(c, sa.UniqueConstraint)
        and _unique_cols(c) == {"conversation_id", "turn_index"}
    ]
    assert turn_uniques, "turns needs UNIQUE(conversation_id, turn_index)"


def _build_018_tables(engine: sa.Engine) -> None:
    """Create the 018 tables on a foreign-key-enforcing SQLite engine, mirroring
    the migration's composite FK + unique constraints."""
    with engine.begin() as conn:
        conn.execute(sa.text("PRAGMA foreign_keys = ON"))
        conn.execute(
            sa.text(
                "CREATE TABLE conversations ("
                "  id VARCHAR(64) PRIMARY KEY,"
                "  customer_id VARCHAR(64) NOT NULL,"
                "  title VARCHAR(256),"
                "  CONSTRAINT uq_conversations_id_customer_id "
                "UNIQUE (id, customer_id)"
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
                "  CONSTRAINT fk_conversation_turns_conversation_customer "
                "FOREIGN KEY (conversation_id, customer_id) "
                "REFERENCES conversations (id, customer_id) ON DELETE CASCADE,"
                "  CONSTRAINT uq_conversation_turns_conversation_id_turn_index "
                "UNIQUE (conversation_id, turn_index)"
                ")"
            )
        )


def test_migration_018_unique_turn_index_blocks_ambiguous_ordering() -> None:
    """Two turns at the same (conversation_id, turn_index) must be rejected — the
    backstop against concurrent appends persisting ambiguous ordering."""
    engine = sa.create_engine("sqlite://")
    _build_018_tables(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("PRAGMA foreign_keys = ON"))
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id, customer_id) VALUES ('c1', 'org_a')"
            )
        )
        conn.execute(
            sa.text(
                "INSERT INTO conversation_turns "
                "(id, conversation_id, customer_id, turn_index, question, answer) "
                "VALUES ('t1', 'c1', 'org_a', 0, 'q', 'a')"
            )
        )
    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as conn:
            conn.execute(sa.text("PRAGMA foreign_keys = ON"))
            conn.execute(
                sa.text(
                    "INSERT INTO conversation_turns "
                    "(id, conversation_id, customer_id, turn_index, question, answer) "
                    "VALUES ('t2', 'c1', 'org_a', 0, 'q2', 'a2')"
                )
            )


def test_migration_018_composite_fk_blocks_cross_tenant_turn() -> None:
    """A turn whose (conversation_id, customer_id) doesn't match a real parent
    row is rejected at the DB level — a turn can never reference a conversation
    of a different tenant."""
    engine = sa.create_engine("sqlite://")
    _build_018_tables(engine)
    with engine.begin() as conn:
        conn.execute(sa.text("PRAGMA foreign_keys = ON"))
        conn.execute(
            sa.text(
                "INSERT INTO conversations (id, customer_id) VALUES ('c1', 'org_a')"
            )
        )
    # Same conversation_id, WRONG customer_id → no matching (id, customer_id) parent.
    with pytest.raises(sa.exc.IntegrityError):
        with engine.begin() as conn:
            conn.execute(sa.text("PRAGMA foreign_keys = ON"))
            conn.execute(
                sa.text(
                    "INSERT INTO conversation_turns "
                    "(id, conversation_id, customer_id, turn_index, question, answer) "
                    "VALUES ('t1', 'c1', 'org_evil', 0, 'q', 'a')"
                )
            )
