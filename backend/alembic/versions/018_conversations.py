"""#41: conversations + conversation_turns — persistent multi-thread "Ask the archive".

Today the /memory "Ask the archive" thread is ephemeral client state — navigating
away or reloading loses everything. This pair of tables makes the conversation a
real PERSISTENT, MULTI-THREAD assistant (ChatGPT / Claude style), scoped to the
customer (tenant):

- ``conversations`` — one row per thread (id, customer_id, title, timestamps).
  ``title`` is NULL until the first turn auto-derives a Claude-style default from
  the question (editable via PATCH). ``updated_at`` bumps on every appended turn +
  rename, so listing newest-first surfaces the most recently touched thread (the
  "restore last-active" anchor on reload).
- ``conversation_turns`` — ordered (question, answer) exchanges. ``citations_json``
  persists the per-answer fused citations verbatim (the MEASURED/PREDICTED source
  word + pre-formatted effect label) so a reloaded thread re-renders byte-identical
  evidence — the honesty firewall rides the stored JSON, never recomputed. A
  0-based ``turn_index`` replays history in ask-order.

Both ``customer_id`` columns reference (turns: denormalized, conversations: FK)
the tenant and cascade on tenant delete, matching every other per-tenant table.
A turn cascades on its parent conversation's delete.

Revision ID: 018
Revises: 017
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "018"
down_revision: str | Sequence[str] | None = "017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversations_customer_id", "conversations", ["customer_id"]
    )

    op.create_table(
        "conversation_turns",
        sa.Column("id", sa.String(64), nullable=False),
        sa.Column("conversation_id", sa.String(64), nullable=False),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("citations_json", JSONB(), nullable=True),
        sa.Column("used_llm", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["conversation_id"], ["conversations.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_conversation_turns_conversation_id",
        "conversation_turns",
        ["conversation_id"],
    )
    op.create_index(
        "ix_conversation_turns_customer_id",
        "conversation_turns",
        ["customer_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_conversation_turns_customer_id", table_name="conversation_turns"
    )
    op.drop_index(
        "ix_conversation_turns_conversation_id", table_name="conversation_turns"
    )
    op.drop_table("conversation_turns")
    op.drop_index("ix_conversations_customer_id", table_name="conversations")
    op.drop_table("conversations")
