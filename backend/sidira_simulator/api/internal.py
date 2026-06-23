"""Internal service-to-service routes (#206 Slice C).

The sidira-crawler CI pulls per-customer login credentials from here at run
start — the PULL model: passwords are entered in the crawl-setup window,
encrypted at rest, and delivered to CI only over this authenticated channel,
never via the workflow_dispatch payload and never as GitHub secrets. This is
the ONE place decrypted passwords leave the backend.

Auth is a single dedicated CI-only shared secret,
``SIDIRA_CRAWLER_CREDENTIALS_TOKEN`` (sibling to
``SIDIRA_CRAWLER_DISPATCH_TOKEN``), presented as a bearer token and compared in
constant time — it is the SOLE authority on this path. ``/internal/`` routes
bypass BOTH ``main.py`` gates: the Clerk session gate (CI carries no browser
session) and the internal-key gate (the crawler reaches api.sidira.ai directly,
and Caddy only staples ``X-Sidira-Internal-Key`` on the ``/_sidira_web_proxy/*``
paths, never on the fallthrough that serves this route — see
``deploy/Caddyfile.api``). So the bearer token is the only thing standing in
front of decrypted credentials: it must fail closed.
"""

from __future__ import annotations

import hmac

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from sidira_simulator.adapters import credentials
from sidira_simulator.adapters.repositories import DEFAULT_SETUP_ID, CrawlConfigRepo
from sidira_simulator.api.crawls import (
    CRAWLER_CREDENTIALS_TOKEN_SUFFIX,
    CREDENTIALS_ENC_KEY,
)
from sidira_simulator.api.deps import get_crawl_config_repo
from sidira_simulator.schemas.crawl import CrawlSetup, is_safe_setup_id
from sidira_simulator.services.runtime_config import resolve_sidira_env

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])

# Sibling to SIDIRA_CRAWLER_DISPATCH_TOKEN; resolve_sidira_env applies the
# SIDIRA_ → PYTHIA_ fallback automatically. Shared with the crawls dispatch
# preflight (api/crawls.py) so both gate on the same env var.
_TOKEN_SUFFIX = CRAWLER_CREDENTIALS_TOKEN_SUFFIX


def require_crawler_credentials_token(request: Request) -> None:
    """Gate the credential pull on the CI-only shared secret.

    - No token configured → 503: the pull channel isn't enabled (don't pretend
      it works).
    - Missing / malformed / wrong token → 404: never confirm the endpoint
      exists to an unauthenticated caller (mirrors the internal_api_key_gate's
      404-on-miss philosophy)."""
    expected = resolve_sidira_env(_TOKEN_SUFFIX)
    if not expected:
        raise HTTPException(status_code=503, detail="crawler credential pull is not configured")
    scheme, _, presented = request.headers.get("authorization", "").partition(" ")
    if scheme.lower() != "bearer" or not presented or not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=404, detail="Not found")


class CrawlRoleLogin(BaseModel):
    """One decrypted role login delivered to CI. Maps onto the crawler's
    RoleCredential env-var pattern (role → username/password)."""

    role: str
    username: str
    password: str


class CrawlCredentialsResponse(BaseModel):
    customer_id: str
    setup_id: str
    logins: list[CrawlRoleLogin]


@router.get(
    "/crawl-credentials/{customer}",
    response_model=CrawlCredentialsResponse,
    dependencies=[Depends(require_crawler_credentials_token)],
)
async def get_crawl_credentials(
    customer: str,
    setup_id: str = DEFAULT_SETUP_ID,
    repo: CrawlConfigRepo = Depends(get_crawl_config_repo),
) -> CrawlCredentialsResponse:
    """Return decrypted role→{username,password} for one customer's crawl setup.

    ``?setup_id=`` selects which of the customer's setups to pull (#215/#245),
    defaulting to ``"default"`` so a setup_id-less pull is byte-identical to
    pre-#215 prod (the legacy single setup). The crawl dispatch carries the
    chosen setup_id so CI pulls the matching setup's credentials.

    404 when the customer has no saved setup (for that setup_id) or no stored
    credentials. The usernames come from the password-free CrawlSetup; the
    passwords are decrypted from the at-rest blob and joined by role."""
    if not is_safe_setup_id(setup_id):
        # A malformed setup_id never names a real setup — 404 (the 404-wall
        # convention), and never echo it back into logs as a valid segment.
        raise HTTPException(status_code=404, detail="no crawl setup for customer")
    row = await repo.get(customer, setup_id)
    if row is None:
        raise HTTPException(status_code=404, detail="no crawl setup for customer")
    enc = row["config_json"].get(CREDENTIALS_ENC_KEY)
    if not enc:
        # Setup saved before Slice C (or with no logins) — re-save to add
        # passwords. Nothing to deliver.
        raise HTTPException(status_code=404, detail="no credentials saved for customer")
    try:
        setup = CrawlSetup.model_validate(row["config_json"])
        secrets = credentials.decrypt(credentials.deserialize_blob(enc), customer_id=customer)
    except credentials.CredentialError as exc:
        raise HTTPException(
            status_code=503, detail="credential storage is not configured"
        ) from exc

    missing = [u.role for u in setup.test_users if u.role not in secrets]
    if missing:
        # The stored blob doesn't cover every configured role (a role added
        # without a matching secret, corrupt/partial data). Delivering a partial
        # set would let the crawler start half-authenticated — fail closed, the
        # same invariant the dispatch preflight enforces (#206 Slice C).
        log.warning("crawl_credentials.incomplete", customer=customer, missing_roles=missing)
        raise HTTPException(
            status_code=409,
            detail="stored credentials are incomplete — re-save the crawl setup",
        )
    logins = [
        CrawlRoleLogin(role=u.role, username=u.username, password=secrets[u.role])
        for u in setup.test_users
    ]
    # Log the access for audit — role names only, never the secrets themselves.
    log.info(
        "crawl_credentials.pulled",
        customer=customer,
        setup_id=setup_id,
        roles=[lg.role for lg in logins],
    )
    return CrawlCredentialsResponse(customer_id=customer, setup_id=setup_id, logins=logins)
