"""Postgres async engine + session factory.

Production uses Neon (per architecture spec). Local dev points DATABASE_URL at
a docker-compose Postgres. When `DATABASE_URL` is unset, callers should fall
back to the in-memory repos in `repositories.py` (no Postgres dependency for
unit tests or the demo).
"""

from __future__ import annotations

import os
from typing import AsyncIterator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from sidira_simulator.services.runtime_config import resolve_sidira_env

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _normalize_database_url(raw: str) -> str:
    """Normalize common provider URLs for SQLAlchemy's asyncpg dialect."""
    parsed = urlsplit(raw)
    scheme = parsed.scheme
    if scheme in {"postgres", "postgresql"}:
        scheme = "postgresql+asyncpg"

    query_pairs: list[tuple[str, str]] = []
    for key, value in parse_qsl(parsed.query, keep_blank_values=True):
        if key == "channel_binding":
            continue
        if key == "sslmode":
            query_pairs.append(("ssl", value))
        else:
            query_pairs.append((key, value))

    return urlunsplit(
        (
            scheme,
            parsed.netloc,
            parsed.path,
            urlencode(query_pairs, doseq=True),
            parsed.fragment,
        )
    )


def database_url() -> str | None:
    """Resolve the configured Postgres URL, including legacy rename fallback."""
    raw = os.environ.get("DATABASE_URL")
    if raw is not None and raw.strip():
        return _normalize_database_url(raw)
    resolved = resolve_sidira_env("DATABASE_URL")
    if resolved is None:
        return None
    return _normalize_database_url(resolved)


def database_configured() -> bool:
    return database_url() is not None


def get_engine() -> AsyncEngine:
    """Lazy-init the async engine from DATABASE_URL."""
    global _engine
    if _engine is None:
        url = database_url()
        if not url:
            raise RuntimeError(
                "DATABASE_URL not set. For dev without Postgres, use the in-memory "
                "repositories from adapters.repositories.InMemorySimulationRepo etc."
            )
        _engine = create_async_engine(url, pool_pre_ping=True, future=True)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(
            bind=get_engine(), expire_on_commit=False, class_=AsyncSession
        )
    return _sessionmaker


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: yield an async session per request."""
    async with get_sessionmaker()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
