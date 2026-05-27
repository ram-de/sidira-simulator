"""Phase 4.6 (#89): agent_instances.arm for A/B experiment mode.

VARCHAR(16) NULL -- legacy rows pre-dating #89 round-trip with NULL
(single-arm sim, today's default). A/B runs persist "treatment" or
"control" so the scoring service in #90 can match pairs by
(persona_id, sample_index) per arm.

Revision ID: 005
Revises: 004
Create Date: 2026-05-26
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "005"
down_revision: str | Sequence[str] | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_instances",
        sa.Column("arm", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_instances", "arm")
