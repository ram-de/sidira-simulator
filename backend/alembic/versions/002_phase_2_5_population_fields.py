"""Phase 2.5: simulations.population_size + sampled_agent_count.

Both nullable -- legacy rows pre-dating Phase 2.5 round-trip with NULLs and the
get_simulation API maps them to None on the response. New rows populated by
api/simulations.create_simulation.

Revision ID: 002
Revises: 001
Create Date: 2026-05-22
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "002"
down_revision: str | Sequence[str] | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("simulations", sa.Column("population_size", sa.Integer(), nullable=True))
    op.add_column("simulations", sa.Column("sampled_agent_count", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("simulations", "sampled_agent_count")
    op.drop_column("simulations", "population_size")
