"""Phase 2.5 (#5): simulations.run_seed for identity_seed reproducibility.

BIGINT NULL -- legacy rows pre-dating #5 round-trip with NULL. New rows persist
the run_seed pinned by SimulationRunner so re-running the same SimulationRequest
with the same run_seed reproduces identical agent identities.

Revision ID: 003
Revises: 002
Create Date: 2026-05-22
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | Sequence[str] | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("simulations", sa.Column("run_seed", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("simulations", "run_seed")
