"""Phase 4.6 (#88): simulations.treatment_fraction for A/B experiment mode.

FLOAT NULL -- legacy rows pre-dating #88 round-trip with NULL (single-arm
sim, today's default). New A/B runs persist `treatment_fraction` in
(0.0, 1.0) so a result-page reload knows the request was A/B.

Revision ID: 004
Revises: 003
Create Date: 2026-05-26
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str | Sequence[str] | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("treatment_fraction", sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "treatment_fraction")
