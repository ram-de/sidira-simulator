"""Phase 5a (#68): agent_instances.materialization_index.

INTEGER NULL -- legacy rows pre-dating #68 round-trip with NULL. New rows
persist the runner's gather/input order so Postgres-backed agent lists match
the in-memory/allocation order the UI relies on.

Revision ID: 008
Revises: 007
Create Date: 2026-05-29
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "008"
down_revision: str | Sequence[str] | None = "007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_instances",
        sa.Column("materialization_index", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_agent_instances_simulation_materialization",
        "agent_instances",
        ["simulation_id", "materialization_index"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_instances_simulation_materialization",
        table_name="agent_instances",
    )
    op.drop_column("agent_instances", "materialization_index")
