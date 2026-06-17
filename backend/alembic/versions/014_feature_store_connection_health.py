"""#328: per-connection HEALTH / last-tested status on feature_store_connections.

Users report "some connections don't work" but nothing signalled WHICH until the
Test step ran. This migration adds the columns the saved-connections register
(#327) reads to render a last-known state in words (OK · TESTED JUN 15 /
FAILED · AUTH / UNTESTED). The route POST /{id}/test now records its outcome
here so the state persists across reloads.

All four columns are NULLABLE so every pre-existing row reads as UNTESTED — no
backfill, no default. ``last_test_status`` carries 'ok' | 'failed';
``last_error_kind`` mirrors the connectivity-error classification
('auth' | 'permission' | 'network' | 'unknown') and ``last_error_message`` the
human-readable reason. The password column is untouched — health is metadata,
never a credential.

Revision ID: 014
Revises: 013
Create Date: 2026-06-16
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "014"
down_revision: str | Sequence[str] | None = "013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "feature_store_connections",
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "feature_store_connections",
        sa.Column("last_test_status", sa.String(16), nullable=True),
    )
    op.add_column(
        "feature_store_connections",
        sa.Column("last_error_kind", sa.String(32), nullable=True),
    )
    op.add_column(
        "feature_store_connections",
        sa.Column("last_error_message", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("feature_store_connections", "last_error_message")
    op.drop_column("feature_store_connections", "last_error_kind")
    op.drop_column("feature_store_connections", "last_test_status")
    op.drop_column("feature_store_connections", "last_tested_at")
