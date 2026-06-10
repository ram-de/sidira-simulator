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

from pydantic import BaseModel, Field, field_validator


def _require_http_url(value: str, label: str) -> str:
    value = value.strip()
    if not value.startswith(("https://", "http://")):
        raise ValueError(f"{label} must be an http(s) URL")
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
    """One test login per role — role gating is captured in the reverse-Figma spec."""

    role: str = Field(min_length=1, max_length=64)
    username: str = Field(min_length=1, max_length=256)


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


class CrawlSetupEnvelope(BaseModel):
    """GET/PUT response: the saved setup (None when never saved) + provenance."""

    customer_id: str
    setup: CrawlSetup | None = None
    updated_at: datetime | None = None
