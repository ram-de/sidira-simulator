"""Persona-build worker (#268 Phase 2).

Moves the persona-pack build off the in-process FastAPI BackgroundTask onto a
separate long-running process. It polls Postgres for PENDING
``persona_build_runs``, atomically claims the oldest (``SELECT ... FOR UPDATE
SKIP LOCKED`` so multiple workers don't collide), reconstructs the BuildConfig
from the persisted ``config_json``, and drives the build to COMPLETE/FAILED via
:class:`PersonaBuilderService` — the same service the API used in-process.

Run it as ``python -m sidira_simulator.worker``. It requires Postgres (the
claim is a DB-level lock); without ``DATABASE_URL`` it exits non-zero rather
than silently polling an in-memory store no API process shares.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from datetime import datetime, timezone

from sidira_simulator.adapters.postgres import database_configured, get_sessionmaker
from sidira_simulator.adapters.r2 import ArtifactStore, get_store
from sidira_simulator.adapters.repositories import (
    PostgresFeatureStoreConnectionRepo,
    PostgresPersonaBuildRepo,
)
from sidira_simulator.services.persona_builder import BuildConfig, PersonaBuilderService
from sidira_simulator.services.runtime_config import resolve_sidira_env

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL_SECONDS = 5.0


def _resolve_poll_interval() -> float:
    """Seconds to sleep between polls when the queue is empty. Malformed env
    values fail open to the default; non-positive values clamp to the default so
    a bad deploy can't spin the worker hot."""
    raw = resolve_sidira_env("PERSONA_WORKER_POLL_SECONDS", str(DEFAULT_POLL_INTERVAL_SECONDS))
    assert raw is not None
    try:
        parsed = float(raw)
    except ValueError:
        return DEFAULT_POLL_INTERVAL_SECONDS
    if parsed <= 0:
        return DEFAULT_POLL_INTERVAL_SECONDS
    return parsed


POLL_INTERVAL_SECONDS = _resolve_poll_interval()


def worker_should_claim() -> bool:
    """True only when ``SIDIRA_PERSONA_BUILD_MODE=worker`` (the prod default).

    In the documented rollback (mode ``inprocess``) the API runs builds in its
    own BackgroundTask; if the worker also claimed the same PENDING row the build
    would run twice — duplicate Snowflake/pipeline work and racing status/pack
    writes. So the worker honours the same knob the API does: when it isn't in
    worker mode it idles instead of claiming, and stays alive (rather than
    exiting into compose's ``restart: always`` loop) so the next deploy that
    flips the knob back picks it up."""
    return resolve_sidira_env("PERSONA_BUILD_MODE", "inprocess") == "worker"


async def claim_and_run_once(store: ArtifactStore) -> bool:
    """Claim and run at most one pending build. Returns True if a build was
    claimed (and run, or marked failed), False if the queue was empty.

    Opens a fresh Postgres session per call so a long-running build doesn't hold
    a session open across polls. The claimed row carries its ``config_json``; a
    NULL config is a pre-worker row that can't be reconstructed, so it's failed
    cleanly rather than crashing the worker."""
    async with get_sessionmaker()() as session:
        repo = PostgresPersonaBuildRepo(session)
        claimed = await repo.claim_next_pending()
        if claimed is None:
            return False

        build_id = claimed["id"]
        customer_id = claimed["customer_id"]
        logger.info("claimed persona build %s (customer %s)", build_id, customer_id)

        if claimed.get("config_json") is None:
            logger.warning(
                "persona build %s has no persisted config_json; marking failed", build_id
            )
            await repo.update_status(
                build_id,
                customer_id,
                "failed",
                error="build config not persisted (pre-worker row); resubmit the build",
                completed_at=datetime.now(timezone.utc),
            )
            return True

        try:
            config = BuildConfig.model_validate(claimed["config_json"])
        except Exception as exc:
            # Non-null but invalid/stale config (e.g. a row queued before a
            # schema change, or a manual DB edit). The row is already committed
            # RUNNING by the claim, so a raised ValidationError here would escape
            # the poll loop and strand the row RUNNING on the compose restart.
            # Fail it cleanly instead — same handling as the NULL-config row.
            logger.warning(
                "persona build %s has invalid config_json (%s); marking failed", build_id, exc
            )
            await repo.update_status(
                build_id,
                customer_id,
                "failed",
                error=f"persisted build config is invalid; resubmit the build ({exc})",
                completed_at=datetime.now(timezone.utc),
            )
            return True
        service = PersonaBuilderService(
            store=store,
            build_repo=repo,
            connection_repo=PostgresFeatureStoreConnectionRepo(session),
        )
        try:
            await service.run(build_id, customer_id, config)
        except Exception:
            # The service already records the failure on the row + run-state;
            # swallow so one bad build doesn't take the worker down (it logs and
            # moves on to the next claim).
            logger.exception("persona build %s raised; failure recorded on the row", build_id)
        return True


async def recover_orphaned_running() -> int:
    """Fail any build still RUNNING when the worker boots.

    In worker mode the single worker is the only thing that flips a row RUNNING,
    so a row found RUNNING at startup is one whose build process died mid-flight
    (deploy recreate, OOM, host restart). The claim query only looks at PENDING
    rows, so without this sweep those rows hang RUNNING forever in the UI. Run
    ONLY in worker mode — in the inprocess rollback the API runs builds and a row
    may be legitimately RUNNING there. Returns the count reaped."""
    async with get_sessionmaker()() as session:
        repo = PostgresPersonaBuildRepo(session)
        reaped = await repo.fail_orphaned_running(
            error="worker restarted while this build was running; resubmit the build"
        )
    if reaped:
        logger.warning("reaped %d orphaned RUNNING persona build(s) at startup", reaped)
    return reaped


async def run_forever(store: ArtifactStore | None = None) -> None:
    """Poll-claim-run loop. Drains the queue back-to-back (loops immediately
    after a successful claim) and only sleeps when there's nothing pending."""
    if store is None:
        store = get_store()
    if not worker_should_claim():
        mode = resolve_sidira_env("PERSONA_BUILD_MODE", "inprocess")
        logger.warning(
            "SIDIRA_PERSONA_BUILD_MODE=%s (not 'worker'); the API runs builds "
            "in-process. Idling without claiming so a build never runs twice.",
            mode,
        )
        while True:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    await recover_orphaned_running()
    logger.info("persona-build worker started; poll interval %.1fs", POLL_INTERVAL_SECONDS)
    while True:
        processed = await claim_and_run_once(store)
        if not processed:
            await asyncio.sleep(POLL_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    # Check the mode BEFORE the Postgres requirement. In the inprocess rollback
    # the API runs builds and the worker only idles (no DB access), so exiting
    # non-zero here would restart-loop the `restart: always` container on a
    # compose box that has no DATABASE_URL. The Postgres requirement applies only
    # when the worker will actually claim.
    if worker_should_claim() and not database_configured():
        print(
            "persona-build worker requires Postgres: set DATABASE_URL "
            "(the worker claims builds via a DB-level lock).",
            file=sys.stderr,
        )
        sys.exit(1)
    asyncio.run(run_forever())
