"""#24: persona_build_runs — one row per persona-pack build.

The build runs as a BackgroundTask (load the saved feature-store connection's
creds → run the source query → invoke the sidira-personas pipeline → write the
pack to R2 at ``customers/<id>/personas/v_<N>/persona_pack.json``). This table
is the dispatch record + last observed status; live progress and the JSONL
event log live in R2 (RunStateStore). ``pack_version`` is set only on success;
``error`` carries the failure reason (incl. a stability-gate failure).

Revision ID: 012
Revises: 011
Create Date: 2026-06-15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012"
down_revision: str | Sequence[str] | None = "011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "persona_build_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False, index=True),
        sa.Column("connection_id", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("pack_version", sa.String(64), nullable=True),
        sa.Column("stability_score", sa.Float(), nullable=True),
        sa.Column("persona_count", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("persona_build_runs")
