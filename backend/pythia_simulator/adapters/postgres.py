"""Postgres async engine + session factory.

Production uses Neon (per architecture spec). Local dev points DATABASE_URL at
a docker-compose Postgres. When `DATABASE_URL` is unset, callers should fall
back to the in-memory repos in `repositories.py` (no Postgres dependency for
unit tests or the demo).
"""

from __future__ import annotations

import os
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Lazy-init the async engine from DATABASE_URL."""
    global _engine
    if _engine is None:
        url = os.environ.get("DATABASE_URL")
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
        yield session
