"""#42: per-USER (private) conversation scoping — conversations.user_id.

Today conversations are scoped by ``customer_id`` (the Clerk ORG) only, so every
member of an org shares the same threads. This migration makes them PRIVATE per
user by adding ``user_id`` (the Clerk session ``sub``), so list/get/rename/
delete/append all scope by BOTH (customer_id, user_id): a user can never see or
touch another user's thread even inside the same tenant.

``user_id`` is NULLABLE on purpose. The table already holds a little real data
(a pre-#42 demo thread) created before per-user scoping existed; a NOT NULL
column would require backfilling a synthetic owner for those rows. Instead:

  * Every NEW row always stamps a concrete ``user_id`` (the route fills it from
    the Clerk session / dev fallback).
  * LEGACY NULL-user rows are treated as ORG-VISIBLE — visible to (and editable
    by) ANY user in the owning tenant — so the pre-existing demo thread is not
    orphaned. The read/write predicate that encodes this lives in
    ``ConversationRepo`` (``user_id == current OR user_id IS NULL``); the tenant
    (``customer_id``) stays the hard outer boundary regardless.

Indexed because every conversation query now filters on it alongside
``customer_id``.

Revision ID: 019
Revises: 018
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "019"
down_revision: str | Sequence[str] | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULLABLE so existing rows (the legacy demo thread) need no backfill; new
    # rows always set it. Legacy NULL = org-visible (see module docstring).
    op.add_column(
        "conversations",
        sa.Column("user_id", sa.String(64), nullable=True),
    )
    op.create_index(
        "ix_conversations_user_id", "conversations", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_conversations_user_id", table_name="conversations")
    op.drop_column("conversations", "user_id")
