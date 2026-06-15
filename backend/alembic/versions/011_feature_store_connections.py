"""#22: feature_store_connections — saved feature-store connections per customer.

One row per connection the data-source wizard creates (today: Snowflake only).
Sanitized connection fields live in their own columns; the password is stored
ONLY as the serialized envelope-encrypted blob in ``password_enc`` (JSONB) —
never in cleartext, and never returned by GET/list. The connectivity test and
table preview decrypt the blob fresh on each call (adapters/credentials.py).

Revision ID: 011
Revises: 010
Create Date: 2026-06-15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "011"
down_revision: str | Sequence[str] | None = "010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feature_store_connections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("account", sa.String(256), nullable=False),
        sa.Column("user", sa.String(256), nullable=False),
        sa.Column("warehouse", sa.String(256), nullable=False),
        sa.Column("role", sa.String(256), nullable=False),
        sa.Column("database", sa.String(256), nullable=False),
        sa.Column("schema", sa.String(256), nullable=True),
        sa.Column("password_enc", JSONB(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("feature_store_connections")
