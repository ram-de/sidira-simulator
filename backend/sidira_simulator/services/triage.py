"""Backlog triage — comparative ranker over the §5e decision flow (Epic #538, #545).

The cost-saving surface: a PM has N candidate product changes and cannot afford to
build/test them all. :func:`triage_backlog` runs the grounded-first decision router
(:func:`decision_flow.decide`) over each hypothesis and RANKS them into three
buckets:

  - ``this-one-loses`` — a grounded, TRUSTWORTHY, NEGATIVE verdict: the engine is
    confident this change fails. **Don't build it** (the cost saver). Ranked to the
    bottom of the test queue.
  - ``test`` — worth a real experiment. Highest priority: a grounded trustworthy
    POSITIVE (a confident win worth confirming/shipping). Then unverified LLM takes
    (a direction, but only a hypothesis) and genuine abstains (inconclusive — the
    engine has no trustworthy answer, so a real test is the only way).
  - ``skip`` — the engine could NOT evaluate the hypothesis at all (the decision
    router errored / never reached the watchdog). No engine signal to triage on;
    deprioritize and handle manually.

**Direction-only.** Every item carries a :class:`DirectionVerdict` (sign +
confidence/abstain, never a magnitude) — the same magnitude-free contract #545
surfaces on a single run.

**Pure orchestration, never raises.** ``decide`` is contractually non-raising, but
we still wrap each call defensively (a monkeypatched / future ``decide`` that
throws must not sink the whole backlog): a throwing decide yields a ``skip`` item
with a synthetic abstain verdict. The estimability manifest is loaded ONCE
(best-effort) and forwarded to every ``decide`` call, so a backlog of N hypotheses
does one manifest read, not N.

**Service-only (no endpoint).** This ships the ranker + tests. A live triage POST
route is a deliberate DEFERRAL — wiring it would widen the request surface and pull
the (flag-gated) decision flow onto a synchronous request path; that can be a clean
follow-on once a consumer exists. Nothing here is reached by any live route today.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import structlog

from sidira_simulator.schemas.estimability import EstimabilityManifest
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.schemas.verdict import DirectionVerdict
from sidira_simulator.services.decision_flow import (
    Council,
    LABEL_INCONCLUSIVE,
    decide,
    verdict_from_decision,
)

log = structlog.get_logger()

Bucket = Literal["test", "this-one-loses", "skip"]

# A sentinel distinguishing "manifest not injected — load it once" from an
# injected ``None`` ("known-absent — do not read R2"). Mirrors decision_flow's own
# _UNSET contract, kept local so triage owns its default.
_MISSING = object()

# Internal rank priority (lower = tested first). Grounded confident wins lead; a
# predicted loser and a no-signal skip sink to the bottom of the queue.
_PRIORITY_TEST_GROUNDED_POSITIVE = 0  # confident win — confirm/ship
_PRIORITY_TEST_UNVERIFIED = 1  # a direction, but only a hypothesis
_PRIORITY_TEST_ABSTAIN = 2  # inconclusive — a real test is the only way
_PRIORITY_THIS_ONE_LOSES = 3  # confident loser — don't build
_PRIORITY_SKIP = 4  # engine could not evaluate


@dataclass(frozen=True)
class TriageItem:
    """One triaged hypothesis: the hypothesis, its verdict, bucket, and why."""

    hypothesis: Hypothesis
    verdict: DirectionVerdict
    bucket: Bucket
    rank_reason: str
    # Internal ordering key (lower = higher priority in the ranked list). Exposed
    # for transparency but the ranked `TriageReport.items` order is the contract.
    priority: int = 0


@dataclass(frozen=True)
class TriageReport:
    """The ranked backlog: `items` ordered highest-priority (most worth a test)
    first, predicted losers and un-evaluable hypotheses last (stable within a
    bucket, preserving the caller's input order)."""

    items: list[TriageItem] = field(default_factory=list)

    def by_bucket(self, bucket: Bucket) -> list[TriageItem]:
        """All items in one bucket, in ranked order (convenience for consumers)."""
        return [it for it in self.items if it.bucket == bucket]


def _abstain_verdict(label: str = LABEL_INCONCLUSIVE) -> DirectionVerdict:
    """A synthetic magnitude-free abstain verdict for the defensive skip path."""
    return DirectionVerdict(
        direction=None,
        caution="hard",
        confidence="low",
        label=label,
        source="llm_fallback",
        watchdog_verdict=None,
        unverified=True,
        guardrails=[],
    )


def _classify(verdict: DirectionVerdict) -> tuple[Bucket, int, str]:
    """Map a :class:`DirectionVerdict` → (bucket, priority, rank_reason)."""
    grounded_trustworthy = verdict.source == "grounded" and verdict.caution == "none"

    if grounded_trustworthy and verdict.direction == "negative":
        return (
            "this-one-loses",
            _PRIORITY_THIS_ONE_LOSES,
            "grounded, trustworthy NEGATIVE verdict — the engine is confident this "
            "loses; don't build it (skip the cost).",
        )
    if grounded_trustworthy and verdict.direction == "positive":
        return (
            "test",
            _PRIORITY_TEST_GROUNDED_POSITIVE,
            "grounded, trustworthy POSITIVE verdict — a confident win worth "
            "confirming with a real test.",
        )
    # Not a trustworthy grounded verdict. Distinguish an engine that COULD NOT
    # evaluate (no watchdog ran → defensive/error path → skip) from a genuine
    # abstain / unverified LLM take (worth a real test).
    if verdict.watchdog_verdict is None and verdict.direction is None:
        return (
            "skip",
            _PRIORITY_SKIP,
            "the decision router could not evaluate this hypothesis (no watchdog "
            "verdict) — no engine signal to triage on; handle manually.",
        )
    if verdict.direction is not None:
        return (
            "test",
            _PRIORITY_TEST_UNVERIFIED,
            "an unverified LLM direction (hypothesis, not a verdict) — worth a real "
            "test to confirm the sign.",
        )
    return (
        "test",
        _PRIORITY_TEST_ABSTAIN,
        "inconclusive — the engine abstained (no trustworthy sign); a real test is "
        "the only way to learn.",
    )


def triage_backlog(
    hypotheses: list[Hypothesis],
    available_columns: list[str],
    customer_id: str,
    pack_version: str,
    *,
    chat_client=None,
    model_id: str | None = None,
    council: Council | None = None,
    manifest: EstimabilityManifest | None | object = _MISSING,
) -> TriageReport:
    """Rank a backlog of hypotheses into skip / test / this-one-loses. Never raises.

    Args mirror :func:`decision_flow.decide` (forwarded per hypothesis). ``manifest``
    is loaded ONCE (best-effort) when not injected and forwarded to every ``decide``
    call, so the whole backlog costs one manifest read. Pass ``manifest=None`` to
    assert it is known-absent (every hypothesis then abstains → test-with-caution).

    Returns a :class:`TriageReport` whose ``items`` are ranked highest-priority
    (most worth a test) first; predicted losers and un-evaluable hypotheses sink to
    the bottom. The sort is stable, so input order is preserved within a bucket.
    """
    # Resolve the manifest once. Not injected → load it (best-effort: a read failure
    # degrades to absent, so decide abstains rather than the whole backlog failing).
    if manifest is _MISSING:
        try:
            from sidira_simulator.services.grounded_predictor import (
                load_estimability_manifest,
            )

            manifest = load_estimability_manifest(customer_id, pack_version)
        except Exception as exc:  # noqa: BLE001 — degrade to absent, never break triage.
            log.warning(
                "triage.manifest_load_failed",
                customer_id=customer_id,
                pack_version=pack_version,
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            manifest = None

    items: list[TriageItem] = []
    for hypothesis in hypotheses:
        try:
            decision = decide(
                hypothesis,
                available_columns,
                customer_id,
                pack_version,
                chat_client=chat_client,
                model_id=model_id,
                council=council,
                manifest=manifest,
            )
            verdict = verdict_from_decision(decision)
        except Exception as exc:  # noqa: BLE001 — one bad hypothesis never sinks the backlog.
            log.warning(
                "triage.decide_failed",
                customer_id=customer_id,
                capability=getattr(hypothesis, "capability_name", "(unknown)"),
                error=str(exc),
                exc_type=type(exc).__name__,
            )
            verdict = _abstain_verdict()

        bucket, priority, rank_reason = _classify(verdict)
        items.append(
            TriageItem(
                hypothesis=hypothesis,
                verdict=verdict,
                bucket=bucket,
                rank_reason=rank_reason,
                priority=priority,
            )
        )

    # Stable sort by priority → ranked queue, input order preserved within a bucket.
    items.sort(key=lambda it: it.priority)
    return TriageReport(items=items)


__all__ = ["Bucket", "TriageItem", "TriageReport", "triage_backlog"]
