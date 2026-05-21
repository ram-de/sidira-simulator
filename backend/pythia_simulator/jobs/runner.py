"""JobRunner — abstracts how background work is dispatched.

MVP: direct in-process invocation via asyncio. Phase 2: swap for Cloud Tasks /
SQS / Celery without changing callers.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Protocol


class JobRunner(Protocol):
    def submit(self, fn: Callable[..., Awaitable[Any]], /, *args: Any, **kwargs: Any) -> None: ...


class InProcessJobRunner:
    """Runs jobs as background asyncio tasks in the same process as the API.

    Fine for MVP; fan-out is bounded by FastAPI's worker concurrency. Phase 2
    replacement should preserve the same `submit(fn, *args)` shape.
    """

    def submit(self, fn: Callable[..., Awaitable[Any]], /, *args: Any, **kwargs: Any) -> None:
        asyncio.create_task(fn(*args, **kwargs))
