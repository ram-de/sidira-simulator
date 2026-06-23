"""#215/#245 (PR 1/3): re-key crawl_configs to (customer_id, setup_id).

An org may hold multiple crawl targets ("setups", one per product) instead of
exactly one. This migration re-keys the table from the single-column PK
``(customer_id)`` to the composite PK ``(customer_id, setup_id)`` and adds a
``name`` display label — fully backward-compatible:

  * ``setup_id`` is NOT NULL with server_default ``'default'``; the single prod
    row each org already has is preserved verbatim as its ``"default"`` setup
    (the server default fills the new column on every existing row).
  * ``name`` is backfilled to ``'Default'`` for those rows.
  * Every existing endpoint keeps operating on the ``"default"`` setup, so a
    single-target tenant sees identical behavior. Multi-setup routes land in
    PR 2.

The table is tiny (~one row per org), so a straightforward PK swap is safe.
Table 009 created the PK via ``primary_key=True`` on a single column, which
Postgres auto-named ``crawl_configs_pkey``; we drop that and add the named
composite ``pk_crawl_configs``.

Revision ID: 016
Revises: 015
Create Date: 2026-06-23
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "016"
down_revision: str | Sequence[str] | None = "015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add setup_id NOT NULL with a server default so every existing row is
    #    backfilled to the reserved "default" setup in one statement — no data
    #    loss, the prior single config becomes the org's default setup.
    op.add_column(
        "crawl_configs",
        sa.Column(
            "setup_id",
            sa.String(64),
            nullable=False,
            server_default="default",
        ),
    )
    # 2. Add the display label. Nullable in general; backfill existing rows to
    #    "Default" so the migrated default setup has a sensible label.
    op.add_column(
        "crawl_configs",
        sa.Column("name", sa.String(255), nullable=True),
    )
    op.execute("UPDATE crawl_configs SET name = 'Default' WHERE name IS NULL")

    # 3. Swap the single-column PK for the composite PK. The old constraint is
    #    the Postgres-auto-named crawl_configs_pkey (009 declared it implicitly).
    op.drop_constraint("crawl_configs_pkey", "crawl_configs", type_="primary")
    op.create_primary_key(
        "pk_crawl_configs",
        "crawl_configs",
        ["customer_id", "setup_id"],
    )


def downgrade() -> None:
    # Reverse order: restore the single-column PK, then drop the new columns.
    # Reversible only while each customer has a single setup (true on the
    # forward path's data); a customer with multiple setups would violate the
    # restored single-column PK — acceptable, this only runs to undo PR 1.
    op.drop_constraint("pk_crawl_configs", "crawl_configs", type_="primary")
    op.create_primary_key(
        "crawl_configs_pkey",
        "crawl_configs",
        ["customer_id"],
    )
    op.drop_column("crawl_configs", "name")
    op.drop_column("crawl_configs", "setup_id")
