"""#214: archived_feature_packs — soft-delete (hide-from-Library) for pack versions.

Feature packs live in R2 (``customers/<id>/featurepacks/<version>/``), not in a DB
row, because they are GENERATED, NEVER AUTHORED. Removing a capability is already a
recrawl (the crawl-setup window), and hand-editing a pack is forbidden (it corrupts
the control arm). What was missing was a way to HIDE a stale pack VERSION from the
Library WITHOUT deleting it — a historical simulation that froze that version must
still resolve and replay.

This table is that marker. One row per (customer, version) means "archived/hidden";
its absence means "visible". The Library-listing endpoints filter on it; pack
resolution for running a simulation never reads it, so archiving can never break a
historical sim. Unarchive deletes the row.

``customer_id`` references ``customers`` and cascades on tenant delete, matching the
other per-tenant tables. The composite PK (customer_id, pack_version) makes a row
naturally idempotent — re-archiving the same version is a no-op upsert.

Revision ID: 015
Revises: 014
Create Date: 2026-06-22
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "015"
down_revision: str | Sequence[str] | None = "014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "archived_feature_packs",
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("pack_version", sa.String(64), nullable=False),
        sa.Column(
            "archived_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["customer_id"], ["customers.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("customer_id", "pack_version"),
    )


def downgrade() -> None:
    op.drop_table("archived_feature_packs")
