"""#268 Phase 2: persist the BuildConfig on persona_build_runs.

Moving the persona-pack build off the in-process FastAPI BackgroundTask onto a
separate triggered worker means the dispatch row must carry everything the
worker needs to reconstruct the job — the request-scoped BuildConfig no longer
lives in the process that claims the build. ``config_json`` stores the
serialized :class:`BuildConfig` (Option B: a single JSONB column). Nullable so
pre-worker rows (created before this column existed) remain valid; the worker
treats a NULL config as un-runnable and fails the build cleanly.

Revision ID: 013
Revises: 012
Create Date: 2026-06-15
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "013"
down_revision: str | Sequence[str] | None = "012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "persona_build_runs",
        sa.Column(
            "config_json",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("persona_build_runs", "config_json")
