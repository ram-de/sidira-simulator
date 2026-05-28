"""Phase 5 (#103): simulations.model_id nullable.

VARCHAR(64) NULL -- legacy rows pre-dating #103 round-trip with NULL
(read as backend default). New runs persist the resolved model id that
powered sim-time agent reactions and classifiers.

Revision ID: 007
Revises: 006
Create Date: 2026-05-27
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "007"
down_revision: str | Sequence[str] | None = "006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("model_id", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "model_id")
