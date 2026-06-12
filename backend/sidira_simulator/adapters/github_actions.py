"""GitHub Actions dispatcher for product-triggered crawls (#193).

The crawl itself runs in ram-de/sidira-crawler CI (workflow ``crawl.yml``) —
R2 and Groq credentials live on that repo's secrets and NEVER on this
backend. This adapter only needs a fine-grained PAT with ``actions: write``
on the crawler repo (``SIDIRA_CRAWLER_DISPATCH_TOKEN``).

Correlation contract (crawl.yml owns the other half): ``workflow_dispatch``
returns no run id, so we pass a generated ``crawl_id`` input and the
workflow surfaces it as ``run-name: "crawl <crawl_id> · <customer>"``; the
run is found by that ``display_title`` prefix. Phase progress comes from
the run's job names (``walk`` / ``synthesize``). Renaming either side
breaks the contract.

Queueing contract: the workflow's per-customer concurrency group holds at
most ONE pending run — GitHub cancels the previously pending run when a
newer dispatch queues behind a running one. A run that concluded
``cancelled`` is therefore reported as superseded, not crashed.
"""

from __future__ import annotations

from dataclasses import dataclass

import httpx
import structlog

from sidira_simulator.services.runtime_config import resolve_sidira_env

log = structlog.get_logger(__name__)

_API = "https://api.github.com"

# Job names inside crawl.yml, in execution order — used to read phase.
_PHASE_BY_JOB = {"walk": "walking", "synthesize": "synthesizing"}


class CrawlDispatchError(Exception):
    """A GitHub API call needed to dispatch or observe a crawl failed."""


@dataclass(frozen=True)
class WorkflowRunState:
    """The slice of a workflow run the crawl API cares about."""

    run_id: int
    status: str  # queued | waiting | requested | pending (concurrency-held) | in_progress | completed
    conclusion: str | None  # success | failure | cancelled | timed_out | ...
    html_url: str


def dispatch_configured() -> bool:
    return resolve_sidira_env("CRAWLER_DISPATCH_TOKEN") is not None


class GitHubCrawlDispatcher:
    """Thin async client over the three GitHub endpoints a crawl needs:
    create a workflow_dispatch event, find the run it created, read a run's
    jobs for phase progress."""

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        token = resolve_sidira_env("CRAWLER_DISPATCH_TOKEN")
        if token is None:
            raise CrawlDispatchError(
                "SIDIRA_CRAWLER_DISPATCH_TOKEN is not configured — cannot dispatch crawls"
            )
        self._repo = resolve_sidira_env("CRAWLER_REPO", "ram-de/sidira-crawler")
        self._workflow = resolve_sidira_env("CRAWL_WORKFLOW", "crawl.yml")
        self._ref = resolve_sidira_env("CRAWL_WORKFLOW_REF", "main")
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        # An injected client (tests) brings its own transport; headers are
        # still ours so fakes never need to fabricate auth.
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self._headers = headers

    async def aclose(self) -> None:
        await self._client.aclose()

    async def dispatch(self, *, crawl_id: str, customer_id: str, crawl_date: str) -> None:
        """Fire crawl.yml. crawl_date is passed explicitly (CI dates are UTC;
        resolving "today" on the runner can disagree with the caller)."""
        url = f"{_API}/repos/{self._repo}/actions/workflows/{self._workflow}/dispatches"
        payload = {
            "ref": self._ref,
            "inputs": {
                "crawl_id": crawl_id,
                "customer": customer_id,
                "crawl_date": crawl_date,
            },
        }
        resp = await self._request("POST", url, json=payload)
        if resp.status_code != 204:
            raise CrawlDispatchError(
                f"workflow dispatch returned {resp.status_code}: {_error_detail(resp)}"
            )
        log.info(
            "crawl.dispatched",
            crawl_id=crawl_id,
            customer_id=customer_id,
            crawl_date=crawl_date,
            repo=self._repo,
        )

    async def find_run(self, crawl_id: str) -> WorkflowRunState | None:
        """Find the run a dispatch created, by display_title prefix.

        Returns None while GitHub has not materialized the run yet (it can
        take a few seconds after the 204) — callers treat that as still
        pending, not as an error.
        """
        url = f"{_API}/repos/{self._repo}/actions/workflows/{self._workflow}/runs"
        # Widest single page GitHub allows. A run only needs to be found once
        # (the run_id is persisted after); the route's materialization cutoff
        # handles the pathological case where it falls out of this window.
        resp = await self._request(
            "GET", url, params={"event": "workflow_dispatch", "per_page": 100}
        )
        if resp.status_code != 200:
            raise CrawlDispatchError(
                f"run lookup returned {resp.status_code}: {_error_detail(resp)}"
            )
        prefix = f"crawl {crawl_id} "
        for run in resp.json().get("workflow_runs", []):
            title = run.get("display_title") or ""
            if title.startswith(prefix) or title == f"crawl {crawl_id}":
                return _run_state(run)
        return None

    async def get_run(self, run_id: int) -> WorkflowRunState:
        url = f"{_API}/repos/{self._repo}/actions/runs/{run_id}"
        resp = await self._request("GET", url)
        if resp.status_code != 200:
            raise CrawlDispatchError(
                f"run fetch returned {resp.status_code}: {_error_detail(resp)}"
            )
        return _run_state(resp.json())

    async def get_phase(self, run_id: int) -> str | None:
        """Map the run's in-flight job to a phase name; None if between jobs."""
        url = f"{_API}/repos/{self._repo}/actions/runs/{run_id}/jobs"
        resp = await self._request("GET", url, params={"per_page": 10})
        if resp.status_code != 200:
            # Phase is decoration on top of status — never fail a poll on it.
            log.warning("crawl.phase_lookup_failed", run_id=run_id, status=resp.status_code)
            return None
        for job in resp.json().get("jobs", []):
            if job.get("status") == "in_progress":
                return _PHASE_BY_JOB.get(job.get("name", ""))
        return None

    async def _request(self, method: str, url: str, **kwargs: object) -> httpx.Response:
        try:
            return await self._client.request(method, url, headers=self._headers, **kwargs)  # type: ignore[arg-type]
        except httpx.HTTPError as exc:
            raise CrawlDispatchError(f"GitHub API unreachable: {exc}") from exc


def _run_state(run: dict[str, object]) -> WorkflowRunState:
    return WorkflowRunState(
        run_id=int(run["id"]),  # type: ignore[arg-type]
        status=str(run.get("status")),
        conclusion=run["conclusion"] if run.get("conclusion") is not None else None,  # type: ignore[arg-type]
        html_url=str(run.get("html_url", "")),
    )


def _error_detail(resp: httpx.Response) -> str:
    try:
        return str(resp.json().get("message", resp.text[:200]))
    except ValueError:
        return resp.text[:200]
