"""Initial schema: customers + simulations + agent_instances + agent_feedback.

Revision ID: 001
Revises:
Create Date: 2026-05-21
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "customers",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("clerk_org_id", sa.String(128), nullable=True, unique=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    op.create_table(
        "simulations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "customer_id",
            sa.String(64),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("persona_pack_version", sa.String(64), nullable=False),
        sa.Column("feature_pack_version", sa.String(64), nullable=False),
        sa.Column("hypothesis_json", JSONB, nullable=False),
        sa.Column("result_json", JSONB, nullable=True),
        sa.Column(
            "parent_simulation_id",
            sa.String(64),
            sa.ForeignKey("simulations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_simulations_customer_id", "simulations", ["customer_id"])
    op.create_index("ix_simulations_status", "simulations", ["status"])
    op.create_index(
        "ix_simulations_parent_simulation_id", "simulations", ["parent_simulation_id"]
    )

    op.create_table(
        "agent_instances",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column(
            "customer_id",
            sa.String(64),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "simulation_id",
            sa.String(64),
            sa.ForeignKey("simulations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("persona_id", sa.String(64), nullable=False),
        sa.Column("persona_pack_version", sa.String(64), nullable=False),
        sa.Column("persona_name", sa.String(256), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("message_count", sa.Integer, server_default="0", nullable=False),
    )
    op.create_index("ix_agent_instances_customer_id", "agent_instances", ["customer_id"])
    op.create_index("ix_agent_instances_simulation_id", "agent_instances", ["simulation_id"])
    op.create_index("ix_agent_instances_persona_id", "agent_instances", ["persona_id"])

    op.create_table(
        "agent_feedback",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False),
        sa.Column(
            "agent_id",
            sa.String(64),
            sa.ForeignKey("agent_instances.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("turn_index", sa.Integer, nullable=False),
        sa.Column("realistic_flag", sa.Boolean, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_agent_feedback_customer_id", "agent_feedback", ["customer_id"])
    op.create_index("ix_agent_feedback_agent_id", "agent_feedback", ["agent_id"])


def downgrade() -> None:
    op.drop_table("agent_feedback")
    op.drop_table("agent_instances")
    op.drop_table("simulations")
    op.drop_table("customers")
