"""#46: experiment_connections + experiment_import_runs — persisted, admin-managed
experiment SOURCES (Statsig / SQL / CSV) per customer.

Mirrors the feature_store_connections pattern (migration 011/014): one row per
saved experiment source the admin connects. Non-secret display config
(host/database/project/query) lives in its own JSONB ``display_config`` column;
the source credentials are stored ONLY as the serialized envelope-encrypted blob
in ``credentials_enc`` (JSONB), AAD-bound to ``customer_id:connection_id`` — never
in cleartext, and never returned by GET/list. The connectivity test and the
on-demand re-import decrypt the blob fresh on each call (adapters/credentials.py).

``experiment_import_runs`` is the per-connection import-history ledger: one row
per re-import (or the initial import on connect), recording start/finish, row
counts, status, and a customer-safe error. It cascades when its parent connection
is deleted (delete = remove the cred blob + the import history).

Revision ID: 020
Revises: 019
Create Date: 2026-06-26
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import op

revision: str = "020"
down_revision: str | Sequence[str] | None = "019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "experiment_connections",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("customer_id", sa.String(64), nullable=False, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        # statsig | sql | csv — the connector kind this source pulls from.
        sa.Column("kind", sa.String(32), nullable=False),
        # Non-secret display config (host/database/project/query/variant
        # delimiter + the confirmed field mapping). NEVER a credential.
        sa.Column("display_config", JSONB(), nullable=False),
        # Serialized credentials.EncryptedBlob (base64'd byte fields), AAD-bound
        # to customer_id:connection_id. NULL for the CSV kind (no secret).
        sa.Column("credentials_enc", JSONB(), nullable=True),
        # connected | error — the last-known state of the source.
        sa.Column("status", sa.String(16), nullable=False, server_default="connected"),
        sa.Column("created_by", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("last_import_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )
    op.create_table(
        "experiment_import_runs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("connection_id", sa.String(64), nullable=False, index=True),
        sa.Column("customer_id", sa.String(64), nullable=False, index=True),
        # running | succeeded | failed
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("imported_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        # Customer-safe error message ONLY (never a raw driver/transport string
        # that could carry a connection string / API key — see #488 invariant).
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["connection_id"], ["experiment_connections.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    # Drop the child (import runs) before the parent (connections) — FK-safe order.
    op.drop_table("experiment_import_runs")
    op.drop_table("experiment_connections")
