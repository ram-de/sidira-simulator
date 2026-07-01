"""Negative-control watchdog — the runtime TRUST GATE (Epic #538, #541).

Phase-1c of the engine rewire:

    LLM-as-translator (#539) → grounded predictor (#540) →
    **negative-control watchdog (#541, THIS)** → router / LLM fallback (#542).

Given a :class:`~sidira_simulator.services.grounded_predictor.GroundedPrediction`
(the direction-only match from #540) and — optionally — the LLM's fluent take on
the same lever, this stamps a three-verdict trust verdict:

    CONFIRMS       — grounded data is trustworthy (and, if an LLM take is given,
                     agrees with it). The grounded sign stands.
    CONTRADICTS    — grounded data is trustworthy and its sign OPPOSES the LLM's
                     take. THE FLAGSHIP: trustworthy empirical data beats fluent
                     intuition; the router surfaces the grounded sign, not the LLM.
    CANT_VALIDATE  — our own data on this exact lever cannot certify a trustworthy
                     answer (not covered / not supportable / no NC evidence
                     precomputed / the guard tripped on hidden confounding).

**Precedence.** trustworthy-empirical > LLM > untrustworthy-empirical. A
CANT_VALIDATE verdict on a COVERED lever tells the router (#542) to ABSTAIN — our
data on this exact lever can't support a trustworthy answer, so we must NOT
launder an LLM guess through it. A CANT_VALIDATE on a NOT-covered lever just means
the router falls through to the LLM (we simply have nothing grounded to say).

**ML-FREE.** The negative-control GUARD compute (sklearn LogisticRegression, see
``research/empirical-uplift-spike/causal_estimator.py::negative_control_guard``)
runs ONCE at pack-build time in ``sidira-persona-worker`` and is baked into the
estimability manifest — exactly like #540. This module is a pure READER +
CLASSIFIER of that precomputed NC evidence: it re-ports NONE of the guard. Pure
stdlib; imports NONE of the heavy ML stack. That is what keeps the API image
ML-free.

**Inert.** Nothing in a live request path (api / orchestrator / runner) imports
this yet — wiring is #542. Ships safe in prod. :func:`watchdog_classify` NEVER
raises: every unexpected shape degrades to a CANT_VALIDATE result carrying a
human-readable ``reason`` for the router's audit trail.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import structlog

from sidira_simulator.services.grounded_predictor import GroundedPrediction

log = structlog.get_logger()

WatchdogVerdict = Literal["CONFIRMS", "CONTRADICTS", "CANT_VALIDATE"]


@dataclass(frozen=True)
class WatchdogResult:
    """The three-verdict trust stamp over a grounded prediction.

    - ``verdict``: CONFIRMS / CONTRADICTS / CANT_VALIDATE (see module docstring).
    - ``trustworthy``: True iff ``verdict != "CANT_VALIDATE"`` — i.e. the grounded
      empirical answer can be trusted (the guard did not trip and the lever is
      covered + supportable).
    - ``grounded_direction``: the sign the grounded predictor carried
      (``prediction.direction``), echoed for the router's audit trail. Non-None on
      a trustworthy (CONFIRMS / CONTRADICTS) verdict; may be None on a
      CANT_VALIDATE verdict (e.g. not covered / not supportable).
    - ``llm_direction``: the LLM's take that was compared against (echoed back), or
      None when no LLM take was supplied.
    - ``reason``: human-readable justification for every branch — the router (#542)
      threads this into its decision log.
    """

    verdict: WatchdogVerdict
    trustworthy: bool
    grounded_direction: Literal["positive", "negative"] | None
    llm_direction: Literal["positive", "negative"] | None
    reason: str


def _cant_validate(
    reason: str,
    *,
    grounded_direction: Literal["positive", "negative"] | None = None,
    llm_direction: Literal["positive", "negative"] | None = None,
) -> WatchdogResult:
    """Build a CANT_VALIDATE result (always ``trustworthy=False``)."""
    return WatchdogResult(
        verdict="CANT_VALIDATE",
        trustworthy=False,
        grounded_direction=grounded_direction,
        llm_direction=llm_direction,
        reason=reason,
    )


def watchdog_classify(
    prediction: GroundedPrediction,
    *,
    llm_direction: Literal["positive", "negative"] | None = None,
) -> WatchdogResult:
    """Stamp a grounded prediction with a three-verdict trust verdict. NEVER raises.

    Logic:

    1. ``not prediction.covered`` → **CANT_VALIDATE** — nothing grounded to certify;
       the router falls back to the LLM.
    2. covered but ``not prediction.supportable`` → **CANT_VALIDATE** — the pair was
       in the grid but build-time couldn't support an estimate (weak overlap / thin
       arms).
    3. covered + supportable but ``candidate.guard_trips is None`` → **CANT_VALIDATE**
       — no NC evidence was precomputed (pack predates the guard producer). We
       cannot certify trust, so we abstain honestly rather than assume clean.
    4. covered + supportable + ``guard_trips is True`` → **CANT_VALIDATE** — the guard
       tripped (hidden confounding / effect indistinguishable from bias). Carry the
       precomputed ``guard_reason`` through.
    5. covered + supportable + ``guard_trips is False`` (trustworthy empirical):
       - ``llm_direction is None`` → **CONFIRMS** (no claim to contradict).
       - ``llm_direction == prediction.direction`` → **CONFIRMS**.
       - ``llm_direction != prediction.direction`` → **CONTRADICTS** (flagship).

    Defensive: any unexpected shape (e.g. a covered prediction whose ``candidate``
    is None) degrades to CANT_VALIDATE instead of raising.
    """
    try:
        # 1. Not covered — nothing grounded; router → LLM.
        if not prediction.covered:
            return _cant_validate(
                f"not covered — nothing grounded to certify; router falls back to LLM "
                f"({prediction.reason})",
                llm_direction=llm_direction,
            )

        # 2. Covered but not supportable — build-time couldn't support an estimate.
        if not prediction.supportable:
            return _cant_validate(
                f"covered but not supportable — build-time could not support an estimate "
                f"({prediction.reason}); router abstains on this lever",
                grounded_direction=prediction.direction,
                llm_direction=llm_direction,
            )

        candidate = prediction.candidate
        # Defensive: a covered+supportable prediction should always carry a candidate;
        # if it somehow doesn't, we cannot read NC evidence — abstain, never raise.
        if candidate is None:  # pragma: no cover — defensive
            return _cant_validate(
                "covered + supportable but no candidate attached — cannot read NC "
                "evidence; router abstains on this lever",
                grounded_direction=prediction.direction,
                llm_direction=llm_direction,
            )

        # 3. No NC evidence precomputed — cannot certify trust (honest default).
        if candidate.guard_trips is None:
            return _cant_validate(
                "no negative-control evidence precomputed (pack predates the guard "
                "producer) — cannot certify trust; router abstains on this lever",
                grounded_direction=prediction.direction,
                llm_direction=llm_direction,
            )

        # 4. Guard tripped — untrustworthy empirical (hidden confounding / indistinct).
        if candidate.guard_trips is True:
            detail = candidate.guard_reason or "hidden confounding or effect indistinguishable from bias"
            return _cant_validate(
                f"negative-control guard tripped — empirical estimate untrustworthy: "
                f"{detail}; router abstains on this lever",
                grounded_direction=prediction.direction,
                llm_direction=llm_direction,
            )

        # 5. Guard clean (guard_trips is False) — trustworthy empirical.
        grounded = prediction.direction
        # Defensive: a guard-clean, supportable candidate should carry a real sign,
        # but the manifest defaults ``sign_adjusted`` to None — never certify a
        # verdict we cannot surface a direction for. Abstain instead of raising.
        if grounded not in ("positive", "negative"):
            return _cant_validate(
                "negative-control guard clear but grounded sign is missing/invalid — "
                "cannot certify a trustworthy direction; router abstains on this lever",
                grounded_direction=None,
                llm_direction=llm_direction,
            )
        if llm_direction is None:
            return WatchdogResult(
                verdict="CONFIRMS",
                trustworthy=True,
                grounded_direction=grounded,
                llm_direction=None,
                reason=(
                    f"negative-control guard clear — trustworthy empirical {grounded!r}; "
                    "no LLM take to contradict"
                ),
            )

        if llm_direction == grounded:
            return WatchdogResult(
                verdict="CONFIRMS",
                trustworthy=True,
                grounded_direction=grounded,
                llm_direction=llm_direction,
                reason=(
                    f"negative-control guard clear — trustworthy empirical {grounded!r} "
                    f"agrees with the LLM take {llm_direction!r}"
                ),
            )

        # Flagship: trustworthy data OPPOSES the LLM.
        return WatchdogResult(
            verdict="CONTRADICTS",
            trustworthy=True,
            grounded_direction=grounded,
            llm_direction=llm_direction,
            reason=(
                f"negative-control guard clear — trustworthy empirical {grounded!r} "
                f"OPPOSES the LLM take {llm_direction!r}; grounded sign stands"
            ),
        )
    except Exception as exc:  # noqa: BLE001 — a runtime trust gate must never break a request.
        log.warning(
            "negative_control_watchdog.classify_failed",
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        return _cant_validate(
            f"watchdog classification failed defensively ({type(exc).__name__}); "
            "router abstains",
            llm_direction=llm_direction,
        )


__all__ = [
    "WatchdogVerdict",
    "WatchdogResult",
    "watchdog_classify",
]
