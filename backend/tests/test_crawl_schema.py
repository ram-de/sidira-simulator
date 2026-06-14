"""CrawlCapability name validation.

A capability name is a slug: it becomes a URL path segment (the Library's
/personas/capability/<name> detail route, #207) and an artifact storage path
segment, so it must stay single-segment and URL-safe.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sidira_simulator.schemas.crawl import CrawlCapability

_URLS = ["https://sandbox.example.com/start"]


@pytest.mark.parametrize(
    "name",
    ["reorder", "account_plan", "browse-recommendations", "ABC123", "a"],
)
def test_valid_slugs_accepted(name: str) -> None:
    assert CrawlCapability(name=name, entry_urls=_URLS).name == name


def test_surrounding_whitespace_is_stripped() -> None:
    assert CrawlCapability(name="  reorder  ", entry_urls=_URLS).name == "reorder"


@pytest.mark.parametrize(
    "name",
    [
        "account/plan",  # path separator — the bug this guards (would 404 the route)
        "back\\slash",
        "has space",
        "emoji😀",
        "dot.name",
        "percent%20",
    ],
)
def test_non_slug_names_rejected(name: str) -> None:
    with pytest.raises(ValidationError):
        CrawlCapability(name=name, entry_urls=_URLS)
