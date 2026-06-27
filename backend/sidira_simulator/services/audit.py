"""Workspace audit-log emission (#48).

A thin helper the workspace-mutating routes call AFTER a mutation succeeds to
append one durable, customer-visible audit event (adapters.repositories
``AuditLogRepo``). Centralizes:

  * the action vocabulary (the dotted ``<target_type>.<verb>`` constants), so the
    strings written to the table are spelled in exactly one place; and
  * :func:`record_audit`, which mints the row id, stamps actor + customer, and —
    critically — NEVER raises. An audit write is observability, not part of the
    mutation's contract: a DB hiccup here must not turn a successful create /
    delete into a 500. (Same "logging must never break the action" discipline as
    the credential audit channel in adapters/credentials.py.)

NO SECRETS: ``metadata`` is optional NON-SECRET context only (a label, a name, a
count). Callers pass target ids / non-secret labels — never a credential,
connection string, password, or token.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any
from uuid import uuid4

if TYPE_CHECKING:
    from sidira_simulator.adapters.repositories import AuditLogRepo

logger = logging.getLogger(__name__)

# ── Action vocabulary ──────────────────────────────────────────────────────
# Dotted <target_type>.<verb>. target_type is the leading segment.
EXPERIMENT_SOURCE = "experiment_source"
FEATURE_STORE = "feature_store"
CRAWL_CONFIG = "crawl_config"
PERSONA_BUILD = "persona_build"

# Experiment sources (#46 routes)
EXPERIMENT_SOURCE_CONNECTED = "experiment_source.connected"
EXPERIMENT_SOURCE_TESTED = "experiment_source.tested"
EXPERIMENT_SOURCE_DELETED = "experiment_source.deleted"
EXPERIMENT_SOURCE_REIMPORTED = "experiment_source.reimported"
# Feature stores
FEATURE_STORE_CREATED = "feature_store.created"
FEATURE_STORE_TESTED = "feature_store.tested"
FEATURE_STORE_DELETED = "feature_store.deleted"
# Crawl configs
CRAWL_CONFIG_CREATED = "crawl_config.created"
CRAWL_CONFIG_UPDATED = "crawl_config.updated"
CRAWL_CONFIG_DELETED = "crawl_config.deleted"
# Persona builds
PERSONA_BUILD_TRIGGERED = "persona_build.triggered"


async def record_audit(
    repo: "AuditLogRepo",
    *,
    customer_id: str,
    actor_user_id: str | None,
    action: str,
    target_type: str,
    target_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append one audit event. Best-effort: never raises.

    Call this AFTER the mutation has succeeded — the event records that the action
    happened, so it must not be written before the action commits, and it must not
    be able to fail the action. ``metadata`` is NON-SECRET context only.
    """
    try:
        await repo.record(
            entry_id=f"al-{uuid4().hex[:16]}",
            customer_id=customer_id,
            actor_user_id=actor_user_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            metadata=metadata,
        )
    except Exception:  # noqa: BLE001 — auditing must never break the mutation.
        logger.warning(
            "failed to write audit event %s for customer %s",
            action,
            customer_id,
            exc_info=True,
        )
