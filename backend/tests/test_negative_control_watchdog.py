"""Negative-control watchdog tests (Epic #538, #541).

Pure: no ML deps, no R2, no live LLM. Constructs ``GroundedPrediction`` +
``CandidateEffect`` fixtures directly and asserts the three-verdict trust stamp.
"""

from __future__ import annotations

from typing import Literal

from sidira_simulator.schemas.estimability import CandidateEffect
from sidira_simulator.services.grounded_predictor import GroundedPrediction
from sidira_simulator.services.negative_control_watchdog import (
    WatchdogResult,
    watchdog_classify,
)


def _candidate(
    *,
    supportable: bool = True,
    sign: Literal["positive", "negative"] | None = "positive",
    guard_trips: bool | None,
    guard_reason: str | None = None,
    grounding_complete: bool | None = None,
    grounding_gaps: list[str] | None = None,
) -> CandidateEffect:
    """A CandidateEffect carrying a chosen NC-guard verdict."""
    return CandidateEffect(
        grounding_complete=grounding_complete,
        grounding_gaps=grounding_gaps or [],
        treatment="womens_email",
        outcome="visit",
        covariates=["recency", "loghist"],
        supportable=supportable,
        support_reasons=[] if supportable else ["overlap too weak"],
        n_treat=21387,
        n_control=21306,
        naive_ate=0.0452 if supportable else None,
        t_learner_ate=0.0453 if supportable else None,
        ipw_ate=0.0454 if supportable else None,
        overlap_fraction=1.0 if supportable else 0.02,
        naive_adjusted_gap=0.00013 if supportable else None,
        sign_adjusted=sign,
        neg_control_effect=0.001 if guard_trips is False else (0.12 if guard_trips else None),
        neg_control_effects=(
            {"pre_visit": 0.001} if guard_trips is False else ({"pre_visit": 0.12} if guard_trips else {})
        ),
        guard_floor=0.05 if guard_trips is not None else None,
        guard_ratio=1.5 if guard_trips is not None else None,
        guard_trips=guard_trips,
        guard_confidence=(
            None if guard_trips is None else ("low/abstain" if guard_trips else "high")
        ),
        guard_reason=guard_reason,
    )


def _covered(
    candidate: CandidateEffect | None,
    *,
    supportable: bool = True,
    direction: Literal["positive", "negative"] | None = "positive",
) -> GroundedPrediction:
    return GroundedPrediction(
        covered=True,
        direction=direction,
        supportable=supportable,
        candidate=candidate,
        reason="matched precomputed effect",
    )


def test_clean_guard_agreeing_llm_confirms() -> None:
    pred = _covered(_candidate(guard_trips=False, sign="positive"), direction="positive")
    res = watchdog_classify(pred, llm_direction="positive")
    assert isinstance(res, WatchdogResult)
    assert res.verdict == "CONFIRMS"
    assert res.trustworthy is True
    assert res.grounded_direction == "positive"
    assert res.llm_direction == "positive"


def test_clean_guard_opposing_llm_contradicts() -> None:
    """The flagship: trustworthy grounded data opposes the LLM's fluent take."""
    pred = _covered(_candidate(guard_trips=False, sign="negative"), direction="negative")
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CONTRADICTS"
    assert res.trustworthy is True
    assert res.grounded_direction == "negative"
    assert res.llm_direction == "positive"


def test_clean_guard_no_llm_confirms() -> None:
    pred = _covered(_candidate(guard_trips=False, sign="positive"), direction="positive")
    res = watchdog_classify(pred)
    assert res.verdict == "CONFIRMS"
    assert res.trustworthy is True
    assert res.llm_direction is None


def test_guard_trips_confounded_cant_validate() -> None:
    reason = "negative control 'pre_visit' residual +0.1200 > |0.05|: hidden confounding"
    pred = _covered(_candidate(guard_trips=True, guard_reason=reason))
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False
    assert "pre_visit" in res.reason
    assert "hidden confounding" in res.reason


def test_covered_not_supportable_cant_validate() -> None:
    pred = _covered(
        _candidate(supportable=False, sign=None, guard_trips=None),
        supportable=False,
        direction=None,
    )
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False
    assert "not supportable" in res.reason


def test_guard_none_no_nc_evidence_cant_validate() -> None:
    pred = _covered(_candidate(guard_trips=None, sign="positive"), direction="positive")
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False
    assert "no negative-control evidence precomputed" in res.reason


def test_not_covered_cant_validate() -> None:
    pred = GroundedPrediction(
        covered=False,
        direction=None,
        supportable=False,
        candidate=None,
        reason="no precomputed effect for (T='x', Y='y')",
    )
    res = watchdog_classify(pred, llm_direction="negative")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False
    assert res.llm_direction == "negative"


def test_raw_guarded_estimate_key_aliases_parse() -> None:
    """A producer that flattens the raw GuardedEstimate (floor/trips/confidence/
    reason) parses into the canonical guard_* fields, so the watchdog can read it."""
    raw = {
        "treatment": "womens_email",
        "outcome": "visit",
        "supportable": True,
        "sign_adjusted": "negative",
        "neg_control_effect": 0.001,
        "neg_control_effects": {"pre_visit": 0.001},
        "floor": 0.05,
        "trips": False,
        "confidence": "high",
        "reason": "main effect clears the bias: estimate trusted",
    }
    cand = CandidateEffect.model_validate(raw)
    assert cand.guard_trips is False
    assert cand.guard_floor == 0.05
    assert cand.guard_confidence == "high"
    assert cand.guard_reason == "main effect clears the bias: estimate trusted"

    pred = _covered(cand, direction="negative")
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CONTRADICTS"
    assert res.trustworthy is True


def test_guard_clean_but_missing_sign_cant_validate() -> None:
    """A guard-clean, supportable candidate with no grounded sign must abstain."""
    pred = _covered(_candidate(guard_trips=False, sign=None), direction=None)
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False
    assert res.grounded_direction is None


def test_defensive_covered_candidate_none_does_not_raise() -> None:
    """A covered+supportable pred with no candidate must degrade, not raise."""
    pred = GroundedPrediction(
        covered=True,
        direction="positive",
        supportable=True,
        candidate=None,
        reason="malformed: covered but no candidate",
    )
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False

# ── grounding-completeness (#564) ─────────────────────────────────────────────


def test_grounding_incomplete_cant_validate_names_gap_tokens() -> None:
    """A grounding-incomplete lever must NEVER get a clean grounded verdict —
    even with a clean NC guard — and the reason must name the producer's gap
    tokens so the frontend can show *why*."""
    pred = _covered(
        _candidate(
            guard_trips=False,
            sign="positive",
            grounding_complete=False,
            grounding_gaps=["no_vouched_negative_control", "structurally_missing_column"],
        ),
        direction="positive",
    )
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert res.trustworthy is False
    assert "grounding-incomplete" in res.reason
    assert "no_vouched_negative_control" in res.reason
    assert "structurally_missing_column" in res.reason


def test_grounding_incomplete_stub_row_gaps_win_over_not_supportable() -> None:
    """The producer's ungroundable STUB rows (supportable=False, zero arms) must
    surface the gap tokens, not the generic 'not supportable' wording."""
    stub = CandidateEffect(
        treatment="womens_email",
        outcome="visit",
        supportable=False,
        support_reasons=[],
        n_treat=0,
        n_control=0,
        guard_confidence="unverified",
        grounding_complete=False,
        grounding_gaps=["no_treatment_column", "structurally_missing_column"],
    )
    pred = _covered(stub, supportable=False, direction=None)
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CANT_VALIDATE"
    assert "grounding-incomplete" in res.reason
    assert "no_treatment_column" in res.reason
    assert "not supportable" not in res.reason


def test_grounding_complete_true_clean_guard_still_confirms() -> None:
    """grounding_complete=True changes nothing on the trustworthy path."""
    pred = _covered(
        _candidate(guard_trips=False, sign="positive", grounding_complete=True),
        direction="positive",
    )
    res = watchdog_classify(pred, llm_direction="positive")
    assert res.verdict == "CONFIRMS"
    assert res.trustworthy is True


def test_grounding_incomplete_empty_gaps_still_abstains() -> None:
    """Inconsistent producer (complete=False, no gaps listed) still abstains."""
    pred = _covered(
        _candidate(guard_trips=False, sign="positive", grounding_complete=False),
        direction="positive",
    )
    res = watchdog_classify(pred)
    assert res.verdict == "CANT_VALIDATE"
    assert "grounding-incomplete" in res.reason


def test_grounding_none_legacy_reason_byte_identical() -> None:
    """A legacy candidate (grounding_complete=None) gets the EXACT pre-#564
    verdict + reason strings — the legacy path is byte-identical."""
    # Legacy trustworthy path: clean guard, no LLM take.
    pred = _covered(_candidate(guard_trips=False, sign="positive"), direction="positive")
    res = watchdog_classify(pred)
    assert res.verdict == "CONFIRMS"
    assert res.reason == (
        "negative-control guard clear — trustworthy empirical 'positive'; "
        "no LLM take to contradict"
    )
    # Legacy no-NC-evidence path.
    pred = _covered(_candidate(guard_trips=None, sign="positive"), direction="positive")
    res = watchdog_classify(pred)
    assert res.reason == (
        "no negative-control evidence precomputed (pack predates the guard "
        "producer) — cannot certify trust; router abstains on this lever"
    )


def test_stub_row_parses_from_raw_producer_dict() -> None:
    """The producer's explicit ungroundable stub row (raw JSON shape) parses."""
    raw = {
        "treatment": "loyalty_tier_upgrade",
        "outcome": "visit",
        "covariates": [],
        "supportable": False,
        "support_reasons": ["ungroundable: structurally missing column(s)"],
        "n_treat": 0,
        "n_control": 0,
        "naive_ate": None,
        "t_learner_ate": None,
        "ipw_ate": None,
        "overlap_fraction": None,
        "naive_adjusted_gap": None,
        "sign_adjusted": None,
        "neg_controls": [],
        "neg_control_effect": None,
        "guard_trips": None,
        "guard_confidence": "unverified",
        "guard_reason": None,
        "grounding_complete": False,
        "grounding_gaps": ["no_treatment_column", "structurally_missing_column"],
    }
    cand = CandidateEffect.model_validate(raw)
    assert cand.supportable is False
    assert cand.n_treat == 0 and cand.n_control == 0
    assert cand.guard_trips is None
    assert cand.grounding_complete is False
    assert cand.grounding_gaps == ["no_treatment_column", "structurally_missing_column"]
