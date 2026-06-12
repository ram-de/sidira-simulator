"""#193: crawl_runs — dispatch record per product-triggered crawl.

One row per Start-crawl click. The crawl executes in sidira-crawler CI
(GitHub workflow_dispatch); the row carries the generated crawl_id (PK,
also the workflow input that names the run), the correlated GitHub run id
once found, and the last observed status. Terminal states are persisted by
the first poll that observes them.

Revision ID: 010
Revises: 009
Create Date: 2026-06-12
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: str | Sequence[str] | None = "009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
        sa.Column("crawl_date", sa.String(10), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=True),
        sa.Column("run_url", sa.String(512), nullable=True),
        sa.Column("snapshot_version", sa.String(64), nullable=True),
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
    op.create_index("ix_crawl_runs_customer_id", "crawl_runs", ["customer_id"])


def downgrade() -> None:
    op.drop_index("ix_crawl_runs_customer_id", table_name="crawl_runs")
    op.drop_table("crawl_runs")
