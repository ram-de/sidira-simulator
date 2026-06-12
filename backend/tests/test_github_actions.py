"""GitHubCrawlDispatcher (#193) against httpx.MockTransport.

These pin the wire-level half of the dispatch contract: the workflow inputs
crawl.yml validates, the display_title prefix used for dispatch→run
correlation, and the job-name→phase mapping.
"""

from __future__ import annotations

import json

import httpx
import pytest

from sidira_simulator.adapters.github_actions import (
    CrawlDispatchError,
    GitHubCrawlDispatcher,
    dispatch_configured,
)


@pytest.fixture(autouse=True)
def token_env(monkeypatch):
    monkeypatch.setenv("SIDIRA_CRAWLER_DISPATCH_TOKEN", "github_pat_test")
    monkeypatch.delenv("PYTHIA_CRAWLER_DISPATCH_TOKEN", raising=False)


def _dispatcher(handler):
    return GitHubCrawlDispatcher(client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def test_dispatch_configured_reflects_env(monkeypatch):
    assert dispatch_configured()
    monkeypatch.delenv("SIDIRA_CRAWLER_DISPATCH_TOKEN")
    assert not dispatch_configured()


def test_missing_token_raises_at_construction(monkeypatch):
    monkeypatch.delenv("SIDIRA_CRAWLER_DISPATCH_TOKEN")
    with pytest.raises(CrawlDispatchError, match="not configured"):
        GitHubCrawlDispatcher()


@pytest.mark.asyncio
async def test_dispatch_sends_the_inputs_crawl_yml_validates():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(204)

    d = _dispatcher(handler)
    await d.dispatch(crawl_id="cr-abc123", customer_id="streamly-sandbox", crawl_date="2026-06-12")

    assert seen["url"].endswith("/repos/ram-de/sidira-crawler/actions/workflows/crawl.yml/dispatches")
    assert seen["auth"] == "Bearer github_pat_test"
    assert seen["body"]["ref"] == "main"
    assert seen["body"]["inputs"] == {
        "crawl_id": "cr-abc123",
        "customer": "streamly-sandbox",
        "crawl_date": "2026-06-12",
    }


@pytest.mark.asyncio
async def test_dispatch_non_204_raises_with_github_message():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "No ref found for: main"})

    with pytest.raises(CrawlDispatchError, match="422.*No ref found"):
        await _dispatcher(handler).dispatch(
            crawl_id="cr-x", customer_id="streamly-sandbox", crawl_date="2026-06-12"
        )


@pytest.mark.asyncio
async def test_find_run_matches_display_title_prefix():
    runs = {
        "workflow_runs": [
            # Another crawl whose id shares a prefix with ours — the trailing
            # space in the match prefix is what keeps this from colliding.
            {
                "id": 1,
                "display_title": "crawl cr-abc1234 · streamly-sandbox",
                "status": "queued",
                "conclusion": None,
                "html_url": "https://x/1",
            },
            {
                "id": 2,
                "display_title": "crawl cr-abc · streamly-sandbox",
                "status": "in_progress",
                "conclusion": None,
                "html_url": "https://x/2",
            },
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["event"] == "workflow_dispatch"
        return httpx.Response(200, json=runs)

    state = await _dispatcher(handler).find_run("cr-abc")
    assert state is not None
    assert state.run_id == 2
    assert state.status == "in_progress"


@pytest.mark.asyncio
async def test_find_run_returns_none_before_the_run_materializes():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"workflow_runs": []})

    assert await _dispatcher(handler).find_run("cr-abc") is None


@pytest.mark.asyncio
async def test_get_phase_maps_job_names():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "jobs": [
                    {"name": "walk", "status": "completed"},
                    {"name": "synthesize", "status": "in_progress"},
                ]
            },
        )

    assert await _dispatcher(handler).get_phase(7) == "synthesizing"


@pytest.mark.asyncio
async def test_get_phase_failure_is_swallowed():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    assert await _dispatcher(handler).get_phase(7) is None


@pytest.mark.asyncio
async def test_network_error_wraps_as_dispatch_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("nope")

    with pytest.raises(CrawlDispatchError, match="unreachable"):
        await _dispatcher(handler).get_run(7)
