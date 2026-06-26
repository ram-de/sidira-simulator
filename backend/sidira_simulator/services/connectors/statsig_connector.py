"""Statsig connector (#19) — structured to pull from Statsig's Console API.

HONEST by construction: without a Statsig API key this connector reports a
``needs_credentials`` state and returns NO data. With a key supplied by the
customer it calls Statsig's Console experiments API, normalizes each experiment
into a ``{column -> value}`` row, and hands those rows to the shared field
mapping (:mod:`mapping`) — the same firewall every connector crosses.

The network call is isolated in :func:`_fetch_experiments` so the suite can
exercise the normalization + needs-credentials behavior without a live key. We
do NOT fabricate results: if no key is configured, the only output is the
"needs credentials" signal.
"""

from __future__ import annotations

from typing import Any

import httpx

# Statsig Console API. The experiments list endpoint; the key rides the
# STATSIG-API-KEY header per Statsig's Console API auth.
STATSIG_API_BASE = "https://statsigapi.net/console/v1"
_API_KEY_FIELD = "api_key"

NEEDS_MESSAGE = (
    "Connect Statsig by supplying your Statsig Console API key. We pull your "
    "experiment results read-only via the Statsig Console API — no key, no data "
    "(we never fabricate imported results)."
)


class StatsigCredentialError(RuntimeError):
    """No usable Statsig credentials were supplied."""


class StatsigFetchError(RuntimeError):
    """The Statsig Console API call failed (auth / network / shape)."""


def has_credentials(config: dict[str, str]) -> bool:
    """True when the customer supplied a non-empty Statsig API key."""
    return bool((config.get(_API_KEY_FIELD) or "").strip())


def _fetch_experiments(api_key: str, *, timeout: float = 20.0) -> list[dict[str, Any]]:
    """Call the Statsig Console API and return its raw experiment objects.

    Isolated for testability (the suite patches this, never hits the network).
    Raises :class:`StatsigFetchError` on any non-200 / transport failure so the
    caller surfaces an honest error instead of a fabricated import.
    """
    try:
        resp = httpx.get(
            f"{STATSIG_API_BASE}/experiments",
            headers={"STATSIG-API-KEY": api_key},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:  # pragma: no cover - network failure path
        raise StatsigFetchError(f"Statsig request failed: {exc}") from exc
    if resp.status_code == 401:
        raise StatsigFetchError("Statsig rejected the API key (401 Unauthorized)")
    if resp.status_code != 200:
        raise StatsigFetchError(
            f"Statsig Console API returned {resp.status_code}"
        )
    body = resp.json()
    data = body.get("data") if isinstance(body, dict) else body
    if not isinstance(data, list):
        raise StatsigFetchError("unexpected Statsig response shape (no experiment list)")
    return data


def _to_row(exp: dict[str, Any], delimiter: str) -> dict[str, str]:
    """Normalize ONE Statsig experiment object into a string-keyed source row.

    Maps Statsig's experiment shape onto our canonical column names so the
    standard :mod:`mapping` step (and the customer's confirmed FieldMapping) does
    the firewall crossing. This is a transport-shape normalization only — it does
    not infer an outcome from an input or vice versa.
    """
    groups = exp.get("groups") or []
    variant_names = [str(g.get("name", "")).strip() for g in groups if g.get("name")]

    # Statsig surfaces the decided variant + result on the experiment record.
    decision = exp.get("decision") or {}
    winner = str(decision.get("winningGroup") or exp.get("winner") or "").strip()
    # `decisionReason` / `status` describes the outcome; pass through verbatim and
    # let the mapping's result-alias table coerce it (win/loss/flat).
    result = str(
        decision.get("result") or exp.get("result") or exp.get("status") or ""
    ).strip()

    return {
        "change_description": str(
            exp.get("description") or exp.get("name") or exp.get("id") or ""
        ).strip(),
        "variants": delimiter.join(variant_names),
        "primary_metric": str(
            exp.get("primaryMetrics", [{}])[0].get("name", "")
            if exp.get("primaryMetrics")
            else (exp.get("primaryMetric") or "")
        ).strip(),
        "category": str(exp.get("category") or exp.get("layerID") or "ui").strip(),
        "winner": winner,
        "result": result,
        "effect_size_pct": str(decision.get("effectSizePct") or exp.get("effectSizePct") or ""),
        "n": str(exp.get("sampleSize") or exp.get("size") or ""),
        "date": str(exp.get("endTime") or exp.get("lastModifiedTime") or "")[:10],
    }


def fetch_rows(config: dict[str, str], *, delimiter: str = "|") -> list[dict[str, str]]:
    """Pull Statsig experiments as normalized source rows (requires a key).

    Raises :class:`StatsigCredentialError` when no key is configured — the caller
    turns that into a ``needs_credentials`` result, never a fake import.
    """
    api_key = (config.get(_API_KEY_FIELD) or "").strip()
    if not api_key:
        raise StatsigCredentialError(NEEDS_MESSAGE)
    raw = _fetch_experiments(api_key)
    return [_to_row(exp, delimiter) for exp in raw]
