"""Clerk session authentication for the API edge.

Phase 5 auth: validate the Clerk session token carried by browser requests and
resolve the authenticated user + their customer (tenant). This is wired in as a
FastAPI middleware (see ``main.py``) that, when Clerk is configured, populates
``request.state.user_id`` and ``request.state.customer_id``.

The whole layer is **gated on ``CLERK_SECRET_KEY``**: when it is unset (local dev
and the test suite) every helper here reports "not configured" and the gate
becomes a pass-through. This mirrors the ``internal_api_key_gate`` precedent and
keeps the existing suite green without auth fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request

from sidira_simulator.services.runtime_config import resolve_sidira_env

# Token claim chain that may carry the tenant id. The canonical claim is locked
# down in #31 (customer signup); reading a documented chain keeps this ticket
# self-contained and forward-compatible with whatever signup writes.
_CUSTOMER_CLAIMS = ("customer_id", "org_id")


@dataclass(frozen=True)
class AuthState:
    """Identity resolved from a validated Clerk session token."""

    user_id: str
    customer_id: str | None


def clerk_secret() -> str | None:
    """Clerk backend API secret, or ``None`` when auth is disabled."""
    return resolve_sidira_env("CLERK_SECRET_KEY")


def clerk_configured() -> bool:
    """True when a Clerk secret is present and the auth gate should be active."""
    return clerk_secret() is not None


def clerk_webhook_secret() -> str | None:
    """Clerk webhook signing secret (``whsec_…``), or ``None`` when unset.

    Distinct from :func:`clerk_secret`: the session gate validates browser JWTs
    with the backend API secret, while the ``/webhooks/clerk`` endpoint validates
    Svix-signed server-to-server deliveries with this signing secret. When unset
    the webhook cannot verify a delivery and refuses to process it.
    """
    return resolve_sidira_env("CLERK_WEBHOOK_SECRET")


def _authorized_parties() -> list[str] | None:
    raw = resolve_sidira_env("CLERK_AUTHORIZED_PARTIES")
    if raw is None:
        return None
    parties = [p.strip() for p in raw.split(",") if p.strip()]
    return parties or None


# Lazily-built singleton so importing this module never requires the SDK or a
# secret to be present (keeps import-time cheap for the no-auth test path).
_client = None


def _get_client():
    global _client
    if _client is None:
        from clerk_backend_api import Clerk

        _client = Clerk(bearer_auth=clerk_secret())
    return _client


def _extract_customer_id(payload: dict) -> str | None:
    """Resolve session claims → tenant id. THE provider-portability seam.

    Today this is a passthrough: the claim value IS the customer id, because
    the webhook provisions tenants keyed by Clerk org id. In an auth-provider
    swap this function (and nothing else) becomes a mapping lookup against the
    provider's external-id column on ``customers`` — no other code may read
    tenant claims off a token. See docs/auth-provider-portability.md.
    """
    for claim in _CUSTOMER_CLAIMS:
        value = payload.get(claim)
        if value:
            return str(value)
    # Clerk v2 session tokens (clerk-backend-api >=5) drop the top-level
    # ``org_id`` and nest the active org under a compact ``o`` claim
    # ({"o": {"id": "org_…", "rol": …, "slg": …}}). Networkless verification
    # returns the raw payload, and which shape arrives is an instance/dashboard
    # setting, not an SDK one — so accept both. Without this, a v2 instance
    # resolves to None and the gate silently falls back to SIDIRA_CUSTOMER_ID.
    org = payload.get("o")
    if isinstance(org, dict):
        value = org.get("id")
        if value:
            return str(value)
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        value = metadata.get("customer_id")
        if value:
            return str(value)
    return None


def authenticate(request: Request) -> AuthState | None:
    """Validate the request's Clerk session token.

    Returns an :class:`AuthState` when the token is valid and the user is signed
    in, otherwise ``None``. Performs networkless verification via the Clerk SDK;
    callers must guard with :func:`clerk_configured` first.
    """
    from clerk_backend_api.security.types import AuthenticateRequestOptions

    options = AuthenticateRequestOptions(authorized_parties=_authorized_parties())
    request_state = _get_client().authenticate_request(request, options)
    if not request_state.is_signed_in:
        return None

    payload = request_state.payload or {}
    user_id = payload.get("sub")
    if not user_id:
        return None
    return AuthState(user_id=str(user_id), customer_id=_extract_customer_id(payload))
