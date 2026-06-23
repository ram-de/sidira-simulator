"""#215/#245 (PR 3a): persist setup_id on a simulation.

A simulation now records WHICH crawl setup's Feature Pack it resolved its
capability from. Before this PR a sim carried no setup_id and the orchestrator
always resolved the DEFAULT setup's pack; a sim built from a NAMED setup's
capabilities would silently resolve the default pack. PR 3a threads setup_id
through sim creation → orchestrator → loader; this migration persists it so
re-runs and the detail view resolve the SAME pack the run actually used.

Fully backward-compatible:

  * ``setup_id`` is NOT NULL with server_default ``'default'``, so every
    EXISTING simulation row is backfilled to the reserved ``"default"`` setup in
    one statement — NO data loss. The loader resolves the EXACT legacy R2 prefix
    (``customers/<id>/featurepacks``) for ``"default"``, so a backfilled row's
    re-run / detail is byte-identical to pre-#215 behavior.
  * New runs persist the request's ``setup_id`` (defaulting to ``"default"`` for
    every existing caller / wizard that does not send one).

The column mirrors the existing dedicated ``feature_pack_version`` column.

Revision ID: 017
Revises: 016
Create Date: 2026-06-23
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "017"
down_revision: str | Sequence[str] | None = "016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NOT NULL with a server default backfills every existing simulation to the
    # reserved "default" setup in one statement — no data loss, the prior runs
    # become default-setup runs (which resolve the exact legacy pack prefix).
    op.add_column(
        "simulations",
        sa.Column(
            "setup_id",
            sa.String(length=64),
            nullable=False,
            server_default="default",
        ),
    )


def downgrade() -> None:
    op.drop_column("simulations", "setup_id")
