"""Crawl setup schema — the customer-supplied inputs for sidira-crawler (#171).

Mirrors the crawler's MVP-scope contract (sidira-crawler README): priority
capabilities with entry-point URLs, a sandbox tenant + one test login per
role, and run parameters. The window that collects this configures and
triggers the crawler; it never edits pack content — the pack itself stays
GENERATED, NEVER AUTHORED (the as-built pack is the control arm).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator


def _require_http_url(value: str, label: str) -> str:
    value = value.strip()
    parts = urlsplit(value)
    # A scheme-only value like "https://" parses but has no host — the walker
    # could never navigate it, so reject at the API boundary (codex P2).
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError(f"{label} must be an http(s) URL with a host")
    # Embedded userinfo (user:pass@host) would be serialized into config_json
    # and cross the workflow_dispatch boundary, leaking login secrets into the
    # crawler repo/run metadata despite the payload being secret-free (codex P2,
    # #206). Reject it at the API boundary.
    if parts.username or parts.password:
        raise ValueError(f"{label} must not embed credentials (user:pass@host)")
    return value


class CrawlCapability(BaseModel):
    """One priority capability the walker documents (reverse-PRD + reverse-Figma)."""

    name: str = Field(min_length=1, max_length=64, description="Capability slug, e.g. onboarding-checklist")
    entry_urls: list[str] = Field(
        min_length=1,
        max_length=3,
        description="1–3 URLs the walker authenticates into and walks ~3 hops deep",
    )

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("capability name must be non-empty")
        return v

    @field_validator("entry_urls")
    @classmethod
    def _validate_urls(cls, v: list[str]) -> list[str]:
        return [_require_http_url(u, "entry url") for u in v]


class CrawlRoleCredential(BaseModel):
    """One test login per role — role gating is captured in the reverse-Figma spec.

    This is the password-FREE projection: it is what persists in config_json,
    what ``GET /crawl-setup`` returns, and what the dispatch payload names. The
    password lives only on the write-path :class:`CrawlRoleCredentialInput` and
    is encrypted at rest (#206 Slice C), never echoed back."""

    role: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=256)


class CrawlRoleCredentialInput(CrawlRoleCredential):
    """PUT-only login that also carries the secret password (#206 Slice C).

    The password is split out, encrypted at rest, and delivered to CI only via
    the authenticated crawler pull — it is never persisted in cleartext, never
    returned by ``GET /crawl-setup`` (that returns the bare
    :class:`CrawlRoleCredential`), and never crosses the dispatch boundary.
    ``repr=False`` keeps it out of tracebacks and log lines."""

    password: str = Field(min_length=1, max_length=256, repr=False)

    @field_validator("password")
    @classmethod
    def _non_blank_password(cls, v: str) -> str:
        # Reject all-whitespace, but do NOT strip — a password's surrounding
        # whitespace can be significant, so persist it byte-for-byte.
        if not v.strip():
            raise ValueError("password must not be blank")
        return v


class CrawlSetup(BaseModel):
    """Saved crawl configuration for one customer. The crawler contract caps
    priority capabilities at 10; partial drafts below the recommended 5 save
    fine — the 5–10 guidance lives in UI copy, not validation."""

    capabilities: list[CrawlCapability] = Field(min_length=1, max_length=10)
    sandbox_url: str = Field(description="Staging/sandbox tenant — the walker never touches production")
    test_users: list[CrawlRoleCredential] = Field(min_length=1, max_length=8)
    ip_allowlist_note: str = Field(
        default="",
        max_length=1024,
        description="Where/how the walker's egress IPs were allowlisted",
    )
    cadence: Literal["weekly", "on_demand"] = "weekly"
    walk_depth: int = Field(default=3, ge=2, le=4)

    @field_validator("sandbox_url")
    @classmethod
    def _validate_sandbox(cls, v: str) -> str:
        return _require_http_url(v, "sandbox url")

    def dispatch_payload(self, product_id: str = "default") -> dict:
        """The non-secret projection sent to the crawler via workflow_dispatch
        (#206 Slice A). This is the ONE place that decides what crosses the
        dispatch boundary — keep it secret-free.

        Login credentials (the per-role username + the password carried on
        :class:`CrawlRoleCredentialInput`) are deliberately excluded: the
        crawler pulls them at run start from an authenticated backend endpoint,
        never from this payload. Only role *names* travel here, so the crawler
        knows which logins to request.

        ``product_id`` is forward-compat for the product-as-sub-entity model
        (#215): it namespaces the R2 pack path. Defaults to "default" until a
        customer has more than one product.
        """
        return {
            "product_id": product_id,
            "sandbox_url": self.sandbox_url,
            "walk_depth": self.walk_depth,
            "cadence": self.cadence,
            "capabilities": [
                {"name": c.name, "entry_urls": list(c.entry_urls)} for c in self.capabilities
            ],
            "roles": [u.role for u in self.test_users],
        }


class CrawlSetupInput(CrawlSetup):
    """The ``PUT /crawl-setup`` request body: a CrawlSetup whose test logins
    also carry passwords (#206 Slice C).

    The route splits this into two destinations: :meth:`to_setup` (the
    password-free CrawlSetup persisted in config_json and returned by GET) and
    :meth:`credential_secrets` (the role→password map encrypted at rest). The
    two never recombine except behind the authenticated crawler pull."""

    test_users: list[CrawlRoleCredentialInput] = Field(min_length=1, max_length=8)

    @field_validator("test_users")
    @classmethod
    def _unique_roles(cls, v: list[CrawlRoleCredentialInput]) -> list[CrawlRoleCredentialInput]:
        roles = [u.role for u in v]
        if len(set(roles)) != len(roles):
            # The secret store is keyed by role; duplicates would make the
            # role→password map ambiguous (and the crawler maps one login per
            # role anyway).
            raise ValueError("each role may have only one test login")
        return v

    def credential_secrets(self) -> dict[str, str]:
        """The secret projection: role → password. Encrypted at rest; reaches
        CI only via the authenticated pull. Kept apart from :meth:`to_setup`
        so the persisted config_json stays password-free."""
        return {u.role: u.password for u in self.test_users}

    def to_setup(self) -> CrawlSetup:
        """The password-free projection persisted in config_json and echoed by
        ``GET /crawl-setup`` — drops passwords, keeps role + username."""
        data = self.model_dump(exclude={"test_users"})
        data["test_users"] = [{"role": u.role, "username": u.username} for u in self.test_users]
        return CrawlSetup.model_validate(data)


class CrawlSetupEnvelope(BaseModel):
    """GET/PUT response: the saved setup (None when never saved) + provenance."""

    customer_id: str
    setup: CrawlSetup | None = None
    updated_at: datetime | None = None
