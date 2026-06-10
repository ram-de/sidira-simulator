"""Clerk webhook ingestion — #31.

Clerk delivers account lifecycle events as Svix-signed server-to-server POSTs.
This endpoint is the one Clerk surface that is **not** session-authenticated: it
is public (so Clerk can reach it) but every request is verified against the Svix
signing secret before any side effect. It is exempted from both the Clerk session
gate and the internal-API-key gate in ``main.py`` for exactly this reason.

Tenancy model (Phase 5): a *customer* is a Clerk **organization**. When an org is
created we materialize the matching ``customers`` row so that, the moment a user's
session carries the ``org_id`` claim, the auth gate resolves it to a concrete
tenant (see :func:`sidira_simulator.api.auth._extract_customer_id`). The customer
id is the Clerk org id itself, which is also the R2 prefix root
(``customers/<org_id>/…``), so a globally-unique org id can never collide.
That equality is a value coincidence, not a semantic dependency: ``id`` is
permanent and opaque, and ``clerk_org_id`` (persisted alongside) is the
provider mapping column an auth-provider swap would resolve against. See
docs/auth-provider-portability.md for the full contract.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from sidira_simulator.api import auth
from sidira_simulator.api.deps import get_customer_repo
from sidira_simulator.adapters.repositories import CustomerRepo

log = structlog.get_logger()

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

_SVIX_HEADERS = ("svix-id", "svix-timestamp", "svix-signature")


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    customer_repo: CustomerRepo = Depends(get_customer_repo),
) -> JSONResponse:
    """Verify a Svix-signed Clerk event and provision tenants from it.

    Returns 503 when no signing secret is configured (we refuse to act on an
    unverifiable delivery), 401 when the signature is invalid, and 200 otherwise
    — including for event types we don't act on, so Clerk stops retrying.
    """
    secret = auth.clerk_webhook_secret()
    if secret is None:
        return JSONResponse({"detail": "Webhook not configured"}, status_code=503)

    body = await request.body()
    headers = {h: request.headers.get(h, "") for h in _SVIX_HEADERS}

    from svix.webhooks import Webhook, WebhookVerificationError

    try:
        event = Webhook(secret).verify(body, headers)
    except (WebhookVerificationError, ValueError):
        # Any failure to verify a public-endpoint delivery is a security signal,
        # not a server bug — reject with 401. ValueError covers svix raising
        # binascii.Error (a ValueError subclass) on a malformed signature header,
        # which would otherwise surface as an unhandled 500 on hostile input.
        log.warning("clerk_webhook.invalid_signature", svix_id=headers["svix-id"] or None)
        return JSONResponse({"detail": "Invalid signature"}, status_code=401)

    event_type = event.get("type")
    data = event.get("data") or {}

    if event_type == "organization.created":
        org_id = data.get("id")
        if not org_id:
            log.warning("clerk_webhook.org_created_missing_id")
            return JSONResponse({"detail": "Missing organization id"}, status_code=400)
        name = data.get("name") or org_id
        # Idempotent: re-delivery of the same event is a no-op (ON CONFLICT DO
        # NOTHING / setdefault), so Clerk retries never duplicate a tenant.
        await customer_repo.ensure_exists(str(org_id), name=str(name), clerk_org_id=str(org_id))
        log.info("clerk_webhook.customer_provisioned", customer_id=str(org_id))
        return JSONResponse({"status": "ok", "customer_id": str(org_id)})

    # Ack everything else so Clerk doesn't retry events we intentionally ignore.
    return JSONResponse({"status": "ignored", "event": event_type})
