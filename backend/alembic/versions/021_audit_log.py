"""#48: audit_log — append-only, per-org workspace audit events.

The DURABLE, customer-visible audit log the admin-console council asked for
("emit audit EVENTS from day one"). One row per workspace-MUTATING action
(experiment source connected/tested/deleted/reimported, feature store
created/deleted, crawl config created/updated/deleted, persona rebuild
triggered), capturing actor + action + target + timestamp, scoped to the tenant
by ``customer_id``.

APPEND-ONLY: the repository over this table exposes INSERT + list only — no
update/delete. NO SECRETS land in ``audit_metadata`` (target ids / non-secret
labels only). Distinct from the per-access credential audit CHANNEL in
adapters/credentials.py (structured logs to a sink); this is the queryable table.

A SINGLE FK to ``customers.id`` (cascade on tenant delete) and no ORM
relationship, so configure_mappers() stays unambiguous (#499). Indexed on
``customer_id`` (every read is tenant-scoped) and ``created_at`` (newest-first
pagination).

Revision ID: 021
Revises: 020
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "021"
down_revision: str | Sequence[str] | None = "020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False, index=True),
        # Clerk session `sub` of the actor; nullable for future system events.
        sa.Column("actor_user_id", sa.String(64), nullable=True),
        # Dotted verb, e.g. 'experiment_source.created'.
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", sa.String(128), nullable=True),
        # OPTIONAL non-secret context only — NEVER a credential.
        sa.Column("audit_metadata", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
            index=True,
        ),
        # Single, unambiguous FK to customers (cascade on tenant delete). No ORM
        # relationship rides this — it is a DB-level integrity guard only (#499).
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    op.drop_table("audit_log")
