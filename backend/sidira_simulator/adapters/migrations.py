"""Startup migration helper for optional Postgres deployments."""

from __future__ import annotations

from pathlib import Path

import structlog
from alembic import command
from alembic.config import Config

from sidira_simulator.adapters.postgres import database_configured
from sidira_simulator.services.runtime_config import resolve_sidira_env

log = structlog.get_logger()

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def auto_migrate_enabled() -> bool:
    raw = resolve_sidira_env("AUTO_MIGRATE", "0")
    assert raw is not None
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def run_startup_migrations() -> None:
    """Run `alembic upgrade head` when explicitly enabled.

    Disabled by default: local dev without Postgres should keep starting fast,
    and production should opt in only after a database URL is configured.
    """
    if not auto_migrate_enabled():
        return
    if not database_configured():
        log.warning("postgres.auto_migrate_skipped", reason="database_url_missing")
        return

    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    command.upgrade(config, "head")
