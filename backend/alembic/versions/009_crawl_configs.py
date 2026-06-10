"""#171: crawl_configs — saved crawl setup per customer.

One row per customer; config_json carries the CrawlSetup payload
(capabilities + entry URLs, sandbox tenant, test users per role,
cadence, walk depth) validated at the API boundary. The setup form
and saved config land before the walker does (sidira-crawler #1–#3);
crawl-run rows arrive with the trigger endpoint in the follow-up.

Revision ID: 009
Revises: 008
Create Date: 2026-06-10
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "009"
down_revision: str | Sequence[str] | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "crawl_configs",
        sa.Column("customer_id", sa.String(64), primary_key=True),
        sa.Column("config_json", JSONB(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("crawl_configs")
