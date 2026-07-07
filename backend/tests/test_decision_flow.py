"""Decision-flow orchestrator tests (Epic #538, ticket #542).

Pure: no R2, no live LLM, no ML deps. A fake ``chat_client`` drives the
translator, a fake :class:`Council` supplies the LLM take + agreement signal, and
hand-built ``EstimabilityManifest`` / ``CandidateEffect`` fixtures feed the
grounded predictor + watchdog. Covers the three §5e branches end-to-end plus the
never-raises contract and the off-by-default flag.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import pytest

from sidira_simulator.schemas.estimability import CandidateEffect, EstimabilityManifest
from sidira_simulator.schemas.lever_review import LeverReview, LeverReviewLog
from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.decision_flow import (
    CouncilAssessment,
    DecisionResult,
    NullCouncil,
    decide,
    decision_flow_enabled,
)
from sidira_simulator.services.negative_control_watchdog import (
    WatchdogResult,
    apply_lever_review_override,
)

TREATMENT = "gate_level"
OUTCOME = "day7_retention"
AVAILABLE = [TREATMENT, OUTCOME, "recency", "prior_sessions"]


# ── fakes ─────────────────────────────────────────────────────────────────────


@dataclass
class _FakeTranslatorOutput:
    """A stand-in for the translator's strict-JSON output object."""

    treatment_column: str | None = TREATMENT
    treatment_contrast: str = "gate at 30 vs gate at 40"
    outcome_column: str | None = OUTCOME
    mediator: str | None = None
    covariates: list = field(default_factory=lambda: ["recency"])
    negative_controls: list = field(default_factory=lambda: ["prior_sessions"])
    sibling_metric: str | None = None
    estimand: str = "ATE on day7_retention"
    confidence: str = "high"
    notes: str | None = None


class _FakeChat:
    """A fake ChatClient: ``chat_json`` returns a preset translator output."""

    def __init__(self, output=None):
        self._output = output if output is not None else _FakeTranslatorOutput()

    def chat_json(self, messages, schema):  # noqa: ANN001 — test double
        return self._output


class _ExplodingChat:
    def chat_json(self, messages, schema):  # noqa: ANN001 — test double
        raise RuntimeError("boom in chat_json")


class _FakeCouncil:
    """A council that returns a preset assessment (ignores its inputs)."""

    def __init__(self, *, agreement: bool, llm_direction: Literal["positive", "negative"] | None):
        self._assessment = CouncilAssessment(
            agreement=agreement,
            llm_direction=llm_direction,
            votes=["a", "b", "c"],
            rationale="fake council",
        )

    def assess(self, hypothesis: str, spec: MechanismSpec) -> CouncilAssessment:
        return self._assessment


class _ExplodingCouncil:
    def assess(self, hypothesis: str, spec: MechanismSpec) -> CouncilAssessment:
        raise RuntimeError("boom in council.assess")


# ── fixtures ────────────────────────────────────────────────────────────────


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="difficulty_gate",
        prose="Moving the difficulty gate earlier will lift day-7 retention.",
    )


def _candidate(
    *,
    supportable: bool = True,
    sign: Literal["positive", "negative"] | None = "positive",
    guard_trips: bool | None = False,
    guard_reason: str | None = None,
) -> CandidateEffect:
    return CandidateEffect(
        treatment=TREATMENT,
        outcome=OUTCOME,
        covariates=["recency"],
        supportable=supportable,
        support_reasons=[] if supportable else ["overlap too weak"],
        n_treat=5000,
        n_control=5000,
        naive_ate=0.03 if supportable else None,
        t_learner_ate=0.031 if supportable else None,
        ipw_ate=0.029 if supportable else None,
        overlap_fraction=1.0 if supportable else 0.02,
        naive_adjusted_gap=0.001 if supportable else None,
        sign_adjusted=sign,
        guard_trips=guard_trips,
        guard_reason=guard_reason,
    )


def _manifest(candidates: list[CandidateEffect]) -> EstimabilityManifest:
    return EstimabilityManifest(
        manifest_version="1",
        customer_id="cust_1",
        setup_id="default",
        pack_version="v_1",
        feature_store="STREAMLY.SYNTHETIC.USERS",
        candidate_effects=candidates,
    )


def _decide(*, manifest, council, chat=None) -> DecisionResult:
    return decide(
        _hypothesis(),
        AVAILABLE,
        "cust_1",
        "v_1",
        chat_client=chat if chat is not None else _FakeChat(),
        council=council,
        manifest=manifest,
    )


# ── Step 1: trustworthy grounded verdict ──────────────────────────────────────


def test_confirms_gives_grounded_verdict_no_caution():
    """Guard-clean + no LLM contradiction → CONFIRMS → authoritative grounded."""
    manifest = _manifest([_candidate(sign="positive", guard_trips=False)])
    result = _decide(manifest=manifest, council=NullCouncil())

    assert result.source == "grounded"
    assert result.direction == "positive"
    assert result.caution == "none"
    assert result.label == "verified verdict"
    assert result.watchdog_verdict == "CONFIRMS"
    assert result.grounded is not None and result.grounded.covered is True


def test_confirms_when_council_agrees_with_grounded():
    """A council take that MATCHES the grounded sign still CONFIRMS."""
    manifest = _manifest([_candidate(sign="positive", guard_trips=False)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="positive"),
    )
    assert result.source == "grounded"
    assert result.watchdog_verdict == "CONFIRMS"
    assert result.caution == "none"


def test_contradicts_data_overrides_intuition():
    """Guard-clean grounded sign OPPOSES the LLM take → CONTRADICTS → grounded wins."""
    manifest = _manifest([_candidate(sign="positive", guard_trips=False)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="negative"),
    )
    assert result.source == "grounded"
    assert result.direction == "positive"  # the grounded sign, not the LLM's
    assert result.caution == "none"
    assert result.label == "verified — data overrides intuition"
    assert result.watchdog_verdict == "CONTRADICTS"


# ── Step 2: grounded-abstain → council-calibrated LLM fallback ─────────────────


def test_abstain_council_agree_moderate_unverified():
    """Guard tripped → CANT_VALIDATE; council AGREES → moderate, surface direction."""
    manifest = _manifest(
        [_candidate(guard_trips=True, guard_reason="hidden confounding")]
    )
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="positive"),
    )
    assert result.source == "llm_fallback"
    assert result.direction == "positive"
    assert result.caution == "moderate"
    assert result.label == "unverified — hypothesis, not verdict"
    assert result.watchdog_verdict == "CANT_VALIDATE"


def test_abstain_council_disagree_hard_inconclusive():
    """Guard tripped → CANT_VALIDATE; council DISAGREES → hard, NO arrow."""
    manifest = _manifest([_candidate(guard_trips=True)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=False, llm_direction="positive"),
    )
    assert result.source == "llm_fallback"
    assert result.direction is None
    assert result.caution == "hard"
    assert result.label == "inconclusive — test it"
    assert result.watchdog_verdict == "CANT_VALIDATE"


def test_not_supportable_is_abstain():
    """Covered but not supportable → CANT_VALIDATE → Step 2 (disagree → hard)."""
    manifest = _manifest([_candidate(supportable=False, sign=None, guard_trips=None)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=False, llm_direction=None),
    )
    assert result.source == "llm_fallback"
    assert result.caution == "hard"


def test_no_nc_evidence_is_abstain():
    """Supportable but guard_trips is None (no NC evidence) → CANT_VALIDATE → Step 2."""
    manifest = _manifest([_candidate(guard_trips=None)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="negative"),
    )
    assert result.source == "llm_fallback"
    assert result.caution == "moderate"
    assert result.direction == "negative"


# ── not-covered → Step 2 ──────────────────────────────────────────────────────


def test_manifest_none_is_not_covered_step2():
    """No manifest at all → not covered → Step 2. NullCouncil → moderate, no arrow."""
    result = _decide(manifest=None, council=NullCouncil())
    assert result.source == "llm_fallback"
    assert result.caution == "moderate"
    assert result.direction is None  # NullCouncil abstains on direction
    assert result.label == "unverified — hypothesis, not verdict"
    assert result.watchdog_verdict == "CANT_VALIDATE"
    assert result.grounded is not None and result.grounded.covered is False


def test_no_matching_pair_is_not_covered_step2():
    """Manifest present but no candidate for (T, Y) → not covered → Step 2."""
    other = CandidateEffect(treatment="unrelated", outcome="other", supportable=True)
    result = _decide(
        manifest=_manifest([other]),
        council=_FakeCouncil(agreement=False, llm_direction=None),
    )
    assert result.source == "llm_fallback"
    assert result.caution == "hard"
    assert result.direction is None


def test_unmappable_spec_is_not_covered_step2():
    """Translator can't ground the outcome → not-mappable spec → not covered → Step 2."""
    chat = _FakeChat(_FakeTranslatorOutput(outcome_column=None))
    manifest = _manifest([_candidate(guard_trips=False)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="positive"),
        chat=chat,
    )
    assert result.mechanism_spec.mappable is False
    assert result.source == "llm_fallback"
    assert result.caution == "moderate"


# ── never raises ──────────────────────────────────────────────────────────────


def test_decide_never_raises_on_exploding_council():
    """A council whose assess() throws → safe hard-caution result, no exception."""
    manifest = _manifest([_candidate(guard_trips=False)])
    result = _decide(manifest=manifest, council=_ExplodingCouncil())
    assert isinstance(result, DecisionResult)
    assert result.caution == "hard"
    assert result.label == "inconclusive — test it"
    assert result.direction is None
    assert result.watchdog_verdict is None
    assert result.mechanism_spec is not None  # fallback spec is always present


def test_decide_survives_exploding_chat_client():
    """An exploding chat_client is swallowed by the translator (unmapped) → Step 2."""
    manifest = _manifest([_candidate(guard_trips=False)])
    result = _decide(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="positive"),
        chat=_ExplodingChat(),
    )
    assert isinstance(result, DecisionResult)
    assert result.mechanism_spec.mappable is False
    assert result.source == "llm_fallback"


def test_default_council_is_nullcouncil():
    """Omitting council uses NullCouncil (degrade-safe): manifest None → moderate."""
    result = decide(_hypothesis(), AVAILABLE, "cust_1", "v_1", chat_client=_FakeChat(), manifest=None)
    assert result.source == "llm_fallback"
    assert result.caution == "moderate"
    assert result.direction is None


# ── manifest injection: known-absent None must not re-read R2 ─────────────────


def test_injected_none_manifest_does_not_reload():
    """Passing manifest=None asserts KNOWN-ABSENT → no second R2 read."""
    from unittest.mock import patch

    from sidira_simulator.services import decision_flow as df

    with patch.object(df, "load_estimability_manifest") as loader:
        result = df.decide(
            _hypothesis(), AVAILABLE, "cust_1", "v_1", chat_client=_FakeChat(), manifest=None
        )
    assert loader.called is False
    assert result.source == "llm_fallback"  # not covered → Step 2


def test_omitted_manifest_loads_from_r2():
    """Omitting manifest triggers the R2 load exactly once."""
    from unittest.mock import patch

    from sidira_simulator.services import decision_flow as df

    with patch.object(df, "load_estimability_manifest", return_value=None) as loader:
        df.decide(_hypothesis(), AVAILABLE, "cust_1", "v_1", chat_client=_FakeChat())
    assert loader.call_count == 1


# ── flag helper ───────────────────────────────────────────────────────────────


def test_flag_on_by_default(monkeypatch):
    """Default ON — pre-launch the grounded flow runs everywhere (no live users)."""
    monkeypatch.delenv("SIDIRA_DECISION_FLOW_ENABLED", raising=False)
    assert decision_flow_enabled() is True


# On unless explicitly disabled: truthy tokens, unknown values, and an empty
# string all leave it ON. Only the explicit off-tokens (next test) disable it.
@pytest.mark.parametrize(
    "val", ["1", "true", "TRUE", "yes", "on", " On ", "Yes", "", "maybe", "2"]
)
def test_flag_on_unless_explicitly_disabled(monkeypatch, val):
    monkeypatch.setenv("SIDIRA_DECISION_FLOW_ENABLED", val)
    assert decision_flow_enabled() is True


@pytest.mark.parametrize("val", ["0", "false", "FALSE", "no", "off", " Off "])
def test_flag_off_for_explicit_off_tokens(monkeypatch, val):
    """The kill-switch: only these explicit off-tokens disable the flow."""
    monkeypatch.setenv("SIDIRA_DECISION_FLOW_ENABLED", val)
    assert decision_flow_enabled() is False


# ── human lever-review override (the honesty asymmetry) ───────────────────────


def _review(
    *,
    treatment: str = TREATMENT,
    outcome: str = OUTCOME,
    decision: Literal["vouched", "rejected"],
    note: str | None = None,
) -> LeverReview:
    return LeverReview(
        treatment=treatment,
        outcome=outcome,
        decision=decision,
        note=note,
        reviewer="user_abc",
        reviewed_at="2026-07-06T00:00:00Z",
    )


def _review_log(*reviews: LeverReview) -> LeverReviewLog:
    return LeverReviewLog(pack_version="v_1", reviews=list(reviews))


def _decide_reviews(*, manifest, council, reviews, chat=None) -> DecisionResult:
    return decide(
        _hypothesis(),
        AVAILABLE,
        "cust_1",
        "v_1",
        chat_client=chat if chat is not None else _FakeChat(),
        council=council,
        manifest=manifest,
        lever_reviews=reviews,
    )


def test_lever_review_rejected_forces_abstain():
    """A human 'rejected' review force-abstains a guard-CLEAN (trustworthy) lever."""
    manifest = _manifest([_candidate(sign="positive", guard_trips=False)])
    result = _decide_reviews(
        manifest=manifest,
        council=NullCouncil(),
        reviews=_review_log(_review(decision="rejected", note="confounded by promo")),
    )
    assert result.source == "llm_fallback"
    assert result.watchdog_verdict == "CANT_VALIDATE"
    assert "human reviewer REJECTED" in result.reason
    assert "confounded by promo" in result.reason


def test_lever_review_vouched_is_noop():
    """A 'vouched' review leaves a guard-CLEAN CONFIRMS verdict UNCHANGED."""
    manifest = _manifest([_candidate(sign="positive", guard_trips=False)])
    result = _decide_reviews(
        manifest=manifest,
        council=NullCouncil(),
        reviews=_review_log(_review(decision="vouched")),
    )
    assert result.source == "grounded"
    assert result.direction == "positive"
    assert result.caution == "none"
    assert result.watchdog_verdict == "CONFIRMS"


def test_lever_review_vouched_does_not_upgrade_abstain():
    """A 'vouched' review NEVER upgrades a guard-TRIPPED CANT_VALIDATE into trust."""
    manifest = _manifest(
        [_candidate(guard_trips=True, guard_reason="hidden confounding")]
    )
    result = _decide_reviews(
        manifest=manifest,
        council=_FakeCouncil(agreement=True, llm_direction="positive"),
        reviews=_review_log(_review(decision="vouched")),
    )
    assert result.watchdog_verdict == "CANT_VALIDATE"
    assert result.source == "llm_fallback"


def test_lever_review_nonmatching_ignored():
    """A review for a DIFFERENT (treatment, outcome) leaves the verdict unchanged."""
    manifest = _manifest([_candidate(sign="positive", guard_trips=False)])
    result = _decide_reviews(
        manifest=manifest,
        council=NullCouncil(),
        reviews=_review_log(
            _review(treatment="other_t", outcome="other_y", decision="rejected")
        ),
    )
    assert result.source == "grounded"
    assert result.watchdog_verdict == "CONFIRMS"


def test_apply_lever_review_override_noop_paths():
    """Direct unit test: None-candidate / None-reviews / empty-reviews are all no-ops."""
    wd = WatchdogResult(
        verdict="CONFIRMS",
        trustworthy=True,
        grounded_direction="positive",
        llm_direction=None,
        reason="guard clear",
    )
    cand = _candidate(sign="positive", guard_trips=False)

    # No candidate → untouched.
    assert apply_lever_review_override(wd, None, _review_log(_review(decision="rejected"))) is wd
    # No reviews object → untouched.
    assert apply_lever_review_override(wd, cand, None) is wd
    # Empty review list → untouched.
    assert apply_lever_review_override(wd, cand, _review_log()) is wd
