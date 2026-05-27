"""Phase 5 (#101): simulations.selected_personas JSONB nullable.

JSONB NULL -- legacy rows pre-dating #101 round-trip with NULL (sim ran
against all personas in the active pack, today's default). New filtered
runs persist the list of persona_ids the PM selected, denormalized so
the result-page cohort banner survives even if the Persona Pack version
changes after the sim completes.

Revision ID: 006
Revises: 005
Create Date: 2026-05-27
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "006"
down_revision: str | Sequence[str] | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "simulations",
        sa.Column("selected_personas", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("simulations", "selected_personas")
