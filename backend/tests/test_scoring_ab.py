"""Tests for `services.scoring.aggregate_ab` — Phase 4.6 #90 paired lift.

Six known-answer fixtures pin the formula per `docs/4.6-ab-experiment-mode.md`
§ Test fixtures:

1. zero-lift balanced pairs                — lift ≈ 0, CI tight
2. positive lift, all pairs positive       — lift > 0, CI excludes 0
3. negative lift, all pairs negative       — lift < 0, CI excludes 0
4. mixed lift, CI crosses zero
5. single matched pair (N=1 degenerate)    — lift_ci = (lift, lift)
6. partial-failure: unmatched + sentiment_failed drops
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.scoring import (
    ABLiftResult,
    AgentAnalysis,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.scoring import (
    AgentReaction,
    ScoringService,
    _agent_delta,
    aggregate_ab,
)


def _a(
    *,
    agent_id: str,
    persona_id: str,
    sample_index: int,
    sentiment: Sentiment,
    confidence: float = 1.0,
    categories: list[str] | None = None,
    sentiment_failed: bool = False,
) -> AgentAnalysis:
    return AgentAnalysis(
        agent_id=agent_id,
        persona_id=persona_id,
        persona_name=persona_id,
        sample_index=sample_index,
        weakness=WeaknessClassification(categories=categories or []),
        sentiment=SentimentClassification(
            sentiment=sentiment, confidence=confidence, one_line_summary=""
        ),
        sentiment_failed=sentiment_failed,
    )


# Disable bootstrap when we want to focus on the point estimate or drop counts;
# CI-aware tests opt into a non-zero bootstrap explicitly.
_NO_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
_CI_CFG = ScoringConfig(min_sample_size=1, bootstrap_resamples=500)


# ── Helpers ───────────────────────────────────────────────────────────


def _matched_pairs(
    n: int,
    *,
    t_sentiment: Sentiment,
    c_sentiment: Sentiment,
    confidence: float = 1.0,
) -> tuple[list[AgentAnalysis], list[AgentAnalysis]]:
    """Build N matched (persona_id, sample_index) pairs across two arms."""
    treatment = [
        _a(
            agent_id=f"t{i}",
            persona_id=f"p{i}",
            sample_index=0,
            sentiment=t_sentiment,
            confidence=confidence,
        )
        for i in range(n)
    ]
    control = [
        _a(
            agent_id=f"c{i}",
            persona_id=f"p{i}",
            sample_index=0,
            sentiment=c_sentiment,
            confidence=confidence,
        )
        for i in range(n)
    ]
    return treatment, control


# ── 1. Zero-lift balanced pairs ───────────────────────────────────────


def test_zero_lift_balanced_pairs() -> None:
    treatment, control = _matched_pairs(
        10, t_sentiment=Sentiment.NEUTRAL, c_sentiment=Sentiment.NEUTRAL
    )
    t_result, c_result, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)

    assert isinstance(lift, ABLiftResult)
    assert lift.paired_n == 10
    assert lift.unpaired_treatment == 0
    assert lift.unpaired_control == 0
    assert lift.sentiment_failure_drops == 0
    assert lift.lift == pytest.approx(0.0, abs=1e-6)
    assert lift.lift_ci is not None
    # CI should bracket zero and be tight (both arms identical)
    assert lift.lift_ci[0] == pytest.approx(0.0, abs=1e-6)
    assert lift.lift_ci[1] == pytest.approx(0.0, abs=1e-6)
    # Per-arm SimulationResults still populated
    assert t_result.confidence_score == pytest.approx(c_result.confidence_score, abs=1e-6)


# ── 2. Positive lift, all pairs positive ──────────────────────────────


def test_positive_lift_all_pairs_positive() -> None:
    treatment, control = _matched_pairs(
        10, t_sentiment=Sentiment.POSITIVE, c_sentiment=Sentiment.NEGATIVE
    )
    t_result, c_result, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)

    assert lift.paired_n == 10
    assert lift.lift is not None
    assert lift.lift > 0
    # Per-arm scores include weakness signal + shrinkage; lift is the
    # locked Q2 paired sentiment-delta statistic (codex R2-P2 fix). They
    # only agree in degenerate cases — check direction only.
    assert t_result.confidence_score > c_result.confidence_score
    # Each pair delta = 1.0 × 1.0 − 1.0 × 0.0 = 1.0; mean=1.0;
    # scaled = 1.0 × 0.6 × 100 = 60.0.
    assert lift.lift == pytest.approx(60.0, abs=1e-6)
    # CI should exclude zero on the positive side AND bracket the point.
    assert lift.lift_ci is not None
    assert lift.lift_ci[0] > 0
    assert lift.lift_ci[0] <= lift.lift <= lift.lift_ci[1]


# ── 3. Negative lift, all pairs negative ──────────────────────────────


def test_negative_lift_all_pairs_negative() -> None:
    treatment, control = _matched_pairs(
        10, t_sentiment=Sentiment.NEGATIVE, c_sentiment=Sentiment.POSITIVE
    )
    t_result, c_result, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)

    assert lift.paired_n == 10
    assert lift.lift is not None
    assert lift.lift < 0
    assert lift.lift_ci is not None
    # CI should exclude zero on the negative side
    assert lift.lift_ci[1] < 0


# ── 4. Mixed lift, CI crosses zero ────────────────────────────────────


def test_mixed_lift_ci_crosses_zero() -> None:
    # Half positive deltas, half negative — symmetric around zero.
    treatment: list[AgentAnalysis] = []
    control: list[AgentAnalysis] = []
    for i in range(10):
        t_sent = Sentiment.POSITIVE if i < 5 else Sentiment.NEGATIVE
        c_sent = Sentiment.NEGATIVE if i < 5 else Sentiment.POSITIVE
        treatment.append(_a(agent_id=f"t{i}", persona_id=f"p{i}", sample_index=0, sentiment=t_sent))
        control.append(_a(agent_id=f"c{i}", persona_id=f"p{i}", sample_index=0, sentiment=c_sent))

    _t, _c, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)
    assert lift.paired_n == 10
    assert lift.lift is not None
    assert lift.lift == pytest.approx(0.0, abs=1e-6)
    assert lift.lift_ci is not None
    # The mixed-sign distribution should yield a CI that brackets zero.
    assert lift.lift_ci[0] < 0 < lift.lift_ci[1]


# ── 5. Single matched pair (N=1 degenerate) ───────────────────────────


def test_single_matched_pair_degenerate_ci() -> None:
    treatment, control = _matched_pairs(
        1, t_sentiment=Sentiment.POSITIVE, c_sentiment=Sentiment.NEUTRAL
    )
    _t, _c, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)

    assert lift.paired_n == 1
    assert lift.lift is not None
    assert lift.lift > 0
    # N=1 bootstrap always picks the same element → CI collapses to a point.
    # The point need not equal `lift` exactly: `lift` is the per-arm
    # confidence_score diff (incl. shrinkage + weakness signal), while the
    # CI is anchored on the sentiment-only delta bootstrap. They differ
    # whenever the two arms' weakness / shrinkage contributions diverge.
    assert lift.lift_ci is not None
    assert lift.lift_ci[0] == lift.lift_ci[1]


# ── 6. Partial-failure: unmatched + sentiment_failed drops ────────────


def test_partial_failure_drop_counters() -> None:
    # 5 treatment + 5 control, but only 3 matched pairs; 2 treatment unmatched,
    # 2 control unmatched. Of the 3 matched, one has sentiment_failed=True on
    # the treatment side and gets dropped from the bootstrap.
    treatment = [
        _a(agent_id="t0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(agent_id="t1", persona_id="p1", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(
            agent_id="t2",
            persona_id="p2",
            sample_index=0,
            sentiment=Sentiment.NEUTRAL,
            sentiment_failed=True,
        ),
        _a(agent_id="t3", persona_id="p3", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(agent_id="t4", persona_id="p4", sample_index=0, sentiment=Sentiment.POSITIVE),
    ]
    control = [
        _a(agent_id="c0", persona_id="p0", sample_index=0, sentiment=Sentiment.NEGATIVE),
        _a(agent_id="c1", persona_id="p1", sample_index=0, sentiment=Sentiment.NEGATIVE),
        _a(agent_id="c2", persona_id="p2", sample_index=0, sentiment=Sentiment.NEGATIVE),
        # p5 / p6 unmatched on control side (no treatment with persona_id p5/p6
        # would be needed; instead p3/p4 unmatched on control side).
    ]
    # treatment has p0..p4; control has p0..p2 → matched on p0/p1/p2.
    # Unmatched: t3, t4 (2 treatment), no unmatched controls.
    # Sentiment-failed: p2 matched but t2.sentiment_failed=True → dropped.
    # Surviving paired_n = 2 (p0, p1).
    _t, _c, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)
    assert lift.paired_n == 2
    assert lift.unpaired_treatment == 2
    assert lift.unpaired_control == 0
    assert lift.sentiment_failure_drops == 1
    assert lift.lift is not None
    assert lift.lift > 0  # the 2 surviving pairs are POS − NEG


# ── Degenerate: zero usable pairs ─────────────────────────────────────


def test_zero_usable_pairs_returns_none() -> None:
    treatment = [_a(agent_id="t0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE)]
    control = [_a(agent_id="c0", persona_id="p1", sample_index=0, sentiment=Sentiment.NEGATIVE)]
    _t, _c, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)
    assert lift.paired_n == 0
    assert lift.lift is None
    assert lift.lift_ci is None
    assert lift.unpaired_treatment == 1
    assert lift.unpaired_control == 1


# ── bootstrap_resamples=0 → lift but no CI ────────────────────────────


def test_bootstrap_zero_leaves_lift_ci_none() -> None:
    treatment, control = _matched_pairs(
        5, t_sentiment=Sentiment.POSITIVE, c_sentiment=Sentiment.NEGATIVE
    )
    _t, _c, lift = aggregate_ab(treatment, control, _NO_CI_CFG, run_seed=42)
    assert lift.paired_n == 5
    assert lift.lift is not None
    assert lift.lift_ci is None


# ── Determinism ───────────────────────────────────────────────────────


def test_aggregate_ab_deterministic_with_run_seed() -> None:
    treatment, control = _matched_pairs(
        8, t_sentiment=Sentiment.POSITIVE, c_sentiment=Sentiment.NEGATIVE
    )
    _t1, _c1, lift1 = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)
    _t2, _c2, lift2 = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)
    assert lift1.lift == lift2.lift
    assert lift1.lift_ci == lift2.lift_ci


# ── score_ab composition (end-to-end through analyze) ────────────────


class _ScriptedChat:
    """Returns positive sentiment for treatment-arm reactions, negative for
    control-arm reactions. Drives a deterministic lift > 0 case so the
    composition assertions are stable."""

    def __init__(self) -> None:
        self.calls = 0

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls += 1
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="ok")
        # Sentiment: marker tokens in the reaction_text drive the canned bucket.
        if "TREATMENT_REACTION" in user_msg:
            return SentimentClassification(
                sentiment=Sentiment.POSITIVE, confidence=1.0, one_line_summary=""
            )
        return SentimentClassification(
            sentiment=Sentiment.NEGATIVE, confidence=1.0, one_line_summary=""
        )

    def chat(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.asyncio
async def test_score_ab_composes_lift_fields_onto_result() -> None:
    svc = ScoringService(chat_client=_ScriptedChat())
    hypothesis = Hypothesis(capability_name="reorder", prose="test")

    treatment = [
        AgentReaction(
            agent_id=f"t{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="TREATMENT_REACTION",
            sample_index=0,
            arm="treatment",
        )
        for i in range(5)
    ]
    control = [
        AgentReaction(
            agent_id=f"c{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="CONTROL_REACTION",
            sample_index=0,
            arm="control",
        )
        for i in range(5)
    ]

    result, analyses = await svc.score_ab(
        hypothesis,
        treatment,
        control,
        run_seed=42,
        config=_CI_CFG,
    )

    assert len(analyses) == 10
    # Per-arm scores populated and ordered correctly (treatment > control)
    assert result.treatment_score is not None
    assert result.control_score is not None
    assert result.treatment_score > result.control_score
    # Lift fields populated
    assert result.lift is not None
    assert result.lift > 0
    assert result.lift_ci is not None
    assert result.lift_paired_n == 5
    assert result.lift_unpaired_treatment == 0
    assert result.lift_unpaired_control == 0
    assert result.lift_sentiment_failure_drops == 0
    # Headline confidence_score is the treatment arm (the proposed change)
    assert result.confidence_score == pytest.approx(result.treatment_score)


@pytest.mark.asyncio
async def test_score_ab_empty_inputs_returns_placeholder() -> None:
    svc = ScoringService(chat_client=object())  # not called
    result, analyses = await svc.score_ab(
        Hypothesis(capability_name="reorder", prose="test"),
        treatment_reactions=[],
        control_reactions=[],
    )
    assert analyses == []
    assert result.confidence_score == 0.0
    assert result.lift is None
    # No reactions at all → never entered aggregate_ab; field stays at
    # schema default None, matching single-arm sims.
    assert result.lift_paired_n is None


@pytest.mark.asyncio
async def test_score_ab_treatment_arm_empty_returns_degraded_placeholder() -> None:
    """Codex R5-P2: A/B run with no successful treatment agents must
    surface an underpowered_design warning naming the missing arm,
    NOT silently report confidence_score=0 as if treatment was
    legitimately terrible. Same for empty control arm. Saves the
    LLM-budget by skipping the analyze fan-out for the broken run."""
    svc = ScoringService(chat_client=object())  # not called — short-circuits
    result, analyses = await svc.score_ab(
        Hypothesis(capability_name="reorder", prose="test"),
        treatment_reactions=[],
        control_reactions=[
            AgentReaction(
                agent_id="c0",
                persona_id="p0",
                persona_name="P0",
                reaction_text="r",
                sample_index=0,
                arm="control",
            )
        ],
    )
    assert analyses == []
    assert result.confidence_score == 0.0
    assert result.lift is None
    assert result.lift_paired_n == 0
    assert any(
        w.category == "underpowered_design" and "treatment" in (w.summary or "")
        for w in result.weaknesses
    ), f"missing-arm warning absent: {result.weaknesses}"


@pytest.mark.asyncio
async def test_score_ab_control_arm_empty_returns_degraded_placeholder() -> None:
    """Symmetric to the treatment-empty case."""
    svc = ScoringService(chat_client=object())
    result, analyses = await svc.score_ab(
        Hypothesis(capability_name="reorder", prose="test"),
        treatment_reactions=[
            AgentReaction(
                agent_id="t0",
                persona_id="p0",
                persona_name="P0",
                reaction_text="r",
                sample_index=0,
                arm="treatment",
            )
        ],
        control_reactions=[],
    )
    assert analyses == []
    assert result.confidence_score == 0.0
    assert result.lift_paired_n == 0
    assert any(
        w.category == "underpowered_design" and "control" in (w.summary or "")
        for w in result.weaknesses
    )


@pytest.mark.asyncio
async def test_score_ab_zero_matched_pairs_preserves_paired_n_zero() -> None:
    """Codex R3-P2b: when A/B mode runs but no pairs match (all unpaired
    or all sentiment-failed), the serialized result must distinguish
    'A/B attempted, lift not computable' (lift_paired_n=0) from
    'single-arm sim, no A/B at all' (lift_paired_n=None)."""
    svc = ScoringService(chat_client=_ScriptedChat())
    hypothesis = Hypothesis(capability_name="reorder", prose="test")
    # Treatment on persona p0; control on persona p1 → zero matched pairs.
    treatment = [
        AgentReaction(
            agent_id="t0",
            persona_id="p0",
            persona_name="P0",
            reaction_text="TREATMENT_REACTION",
            sample_index=0,
            arm="treatment",
        )
    ]
    control = [
        AgentReaction(
            agent_id="c0",
            persona_id="p1",
            persona_name="P1",
            reaction_text="CONTROL_REACTION",
            sample_index=0,
            arm="control",
        )
    ]
    result, _ = await svc.score_ab(hypothesis, treatment, control, config=_NO_CI_CFG, run_seed=42)
    assert result.lift is None
    assert result.lift_paired_n == 0  # NOT None
    assert result.lift_unpaired_treatment == 1
    assert result.lift_unpaired_control == 1


# ── Codex R4-P1 (PR #96): confidence weighting applies to negative too ──


def test_agent_delta_low_confidence_negative_shrinks_toward_neutral() -> None:
    """Codex R4-P1: prior formula was `confidence × value`, which silently
    dropped confidence for NEGATIVE (value=0) since c × 0 = 0. A
    low-confidence negative carried the same weight as a high-confidence
    one. Post-fix: each side shrinks toward neutral (0.5) by (1 −
    confidence), so low confidence collapses the contribution toward 0
    delta regardless of bucket."""
    treatment_hi = _a(
        agent_id="t",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.POSITIVE,
        confidence=1.0,
    )
    control_low = _a(
        agent_id="c",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.NEGATIVE,
        confidence=0.1,
    )
    control_hi = _a(
        agent_id="c2",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.NEGATIVE,
        confidence=1.0,
    )

    delta_low_conf = _agent_delta(treatment_hi, control_low)
    delta_hi_conf = _agent_delta(treatment_hi, control_hi)

    # Hi-conf NEG: t_shrunk = 1.0, c_shrunk = 0.0 → delta = 1.0
    assert delta_hi_conf == pytest.approx(1.0, abs=1e-6)
    # Low-conf NEG (c=0.1): c_shrunk = 0.1*0 + 0.9*0.5 = 0.45 → delta = 1.0 - 0.45 = 0.55
    assert delta_low_conf == pytest.approx(0.55, abs=1e-6)
    # Low-conf NEG MUST contribute less than hi-conf NEG (this is the bug)
    assert delta_low_conf < delta_hi_conf


def test_agent_delta_low_confidence_positive_also_shrinks() -> None:
    """Symmetry check: confidence weighting must apply to POSITIVE as
    well (was already partially working in the buggy formula since
    c × 1.0 differs by c, but the new formula must preserve this)."""
    control = _a(
        agent_id="c",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.NEUTRAL,
        confidence=1.0,
    )
    treatment_low = _a(
        agent_id="t",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.POSITIVE,
        confidence=0.1,
    )
    treatment_hi = _a(
        agent_id="t2",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.POSITIVE,
        confidence=1.0,
    )
    delta_low = _agent_delta(treatment_low, control)
    delta_hi = _agent_delta(treatment_hi, control)
    assert delta_hi > delta_low
    # Low-conf POS (c=0.1): t_shrunk = 0.1*1 + 0.9*0.5 = 0.55; control NEU c=1 → c_shrunk=0.5
    # delta = 0.55 - 0.5 = 0.05
    assert delta_low == pytest.approx(0.05, abs=1e-6)


def test_agent_delta_zero_confidence_both_sides_yields_zero() -> None:
    """Pathological floor: if both classifiers report confidence=0, neither
    side contributes any signal — paired delta must be exactly zero."""
    treatment = _a(
        agent_id="t",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.POSITIVE,
        confidence=0.0,
    )
    control = _a(
        agent_id="c",
        persona_id="p",
        sample_index=0,
        sentiment=Sentiment.NEGATIVE,
        confidence=0.0,
    )
    assert _agent_delta(treatment, control) == pytest.approx(0.0, abs=1e-6)


# ── Codex R2-P1 (PR #96): arm-aware scoring prompts ──────────────────


class _PromptRecorder:
    """Records every system prompt + user-message pair sent to chat_json,
    so tests can assert which scoring prompt was used for which arm."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, type]] = []

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        system = next(m["content"] for m in messages if m["role"] == "system")
        user = next(m["content"] for m in messages if m["role"] == "user")
        self.calls.append((system, user, schema))
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="ok")
        return SentimentClassification(
            sentiment=Sentiment.POSITIVE, confidence=0.8, one_line_summary=""
        )

    def chat(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


@pytest.mark.asyncio
async def test_analyze_routes_control_arm_to_status_quo_sentiment_prompt() -> None:
    """Control reactions must NOT be classified with the treatment-arm
    sentiment prompt (codex R2-P1). The treatment prompt frames the
    reaction as reception-of-a-proposed-change; a control reaction is
    about the current product."""
    recorder = _PromptRecorder()
    svc = ScoringService(chat_client=recorder)

    await svc.analyze(
        Hypothesis(capability_name="reorder", prose="test change"),
        AgentReaction(
            agent_id="c0",
            persona_id="p0",
            persona_name="P0",
            reaction_text="status-quo feedback",
            sample_index=0,
            arm="control",
        ),
    )
    # Control arm → exactly one chat_json call (sentiment only).
    assert len(recorder.calls) == 1
    system, user, schema = recorder.calls[0]
    assert schema is SentimentClassification
    assert "STATUS-QUO" in system or "status-quo" in user
    assert "proposed product change" not in system.lower()


@pytest.mark.asyncio
async def test_analyze_routes_current_state_arm_to_status_quo_sentiment_prompt() -> None:
    """#221 §3.3.1 delta-mode (codex P1): the `current_state` shadow arm is
    control-equivalent — the same personas reacting to TODAY's product, composed
    with the control task block. It MUST be scored with the status-quo sentiment
    prompt and skip weakness classification, exactly like `arm="control"`.
    Before the fix `analyze()` keyed only on `arm == "control"`, so current-state
    shadows were scored with the treatment ('reception-of-a-change') prompt,
    corrupting current_state_score and the delta."""
    recorder = _PromptRecorder()
    svc = ScoringService(chat_client=recorder)

    analysis = await svc.analyze(
        Hypothesis(capability_name="reorder", prose="test change"),
        AgentReaction(
            agent_id="cs0",
            persona_id="p0",
            persona_name="P0",
            reaction_text="status-quo feedback",
            sample_index=0,
            arm="current_state",
        ),
    )
    # Control-equivalent → exactly one chat_json call (sentiment only), routed
    # to the status-quo prompt, and weakness classification skipped.
    assert len(recorder.calls) == 1
    system, user, schema = recorder.calls[0]
    assert schema is SentimentClassification
    assert "STATUS-QUO" in system or "status-quo" in user
    assert "proposed product change" not in system.lower()
    assert analysis.weakness.categories == []
    assert analysis.weakness_failed is False


@pytest.mark.asyncio
async def test_analyze_routes_treatment_arm_to_change_sentiment_prompt() -> None:
    """Treatment arm keeps the original 'reception of a proposed product
    change' prompt — backwards-compat with single-arm sims."""
    recorder = _PromptRecorder()
    svc = ScoringService(chat_client=recorder)

    await svc.analyze(
        Hypothesis(capability_name="reorder", prose="test change"),
        AgentReaction(
            agent_id="t0",
            persona_id="p0",
            persona_name="P0",
            reaction_text="reaction to change",
            sample_index=0,
            arm="treatment",
        ),
    )
    # Treatment arm → two chat_json calls (weakness + sentiment).
    assert len(recorder.calls) == 2
    schemas = {schema for _system, _user, schema in recorder.calls}
    assert schemas == {WeaknessClassification, SentimentClassification}
    sentiment_call = next(c for c in recorder.calls if c[2] is SentimentClassification)
    assert "proposed product change" in sentiment_call[0].lower()


@pytest.mark.asyncio
async def test_analyze_skips_weakness_classification_for_control_arm() -> None:
    """The 6 weakness categories describe experiment-design weaknesses in
    the proposed change. They're undefined for the control arm — skip the
    LLM call and return empty categories."""
    recorder = _PromptRecorder()
    svc = ScoringService(chat_client=recorder)

    analysis = await svc.analyze(
        Hypothesis(capability_name="reorder", prose="test change"),
        AgentReaction(
            agent_id="c0",
            persona_id="p0",
            persona_name="P0",
            reaction_text="status-quo feedback",
            sample_index=0,
            arm="control",
        ),
    )
    weakness_calls = [c for c in recorder.calls if c[2] is WeaknessClassification]
    assert weakness_calls == []
    assert analysis.weakness.categories == []
    assert analysis.weakness_failed is False


def test_aggregate_control_arm_degradation_uses_attempted_count() -> None:
    """Codex R3-P2a: control-arm agents skip weakness classification, so
    `aggregate()`'s degradation rate must divide by ATTEMPTED
    classifications, not by 2N. Without this, a fully-failed
    control-sentiment run reports 50% (N/2N) and never trips the
    strict `> degradation_threshold` gate."""
    from sidira_simulator.schemas.simulation import SimulationResult

    # 4 control agents, all with sentiment_failed=True. Weakness not
    # attempted (control-arm flow). Failure rate should be 4/4 = 100%,
    # not 4/8 = 50%.
    control_analyses = [
        AgentAnalysis(
            agent_id=f"c{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            sample_index=0,
            weakness=WeaknessClassification(categories=[]),
            sentiment=SentimentClassification(
                sentiment=Sentiment.NEUTRAL, confidence=0.0, one_line_summary=""
            ),
            weakness_failed=False,
            weakness_attempted=False,
            sentiment_failed=True,
        )
        for i in range(4)
    ]
    result: SimulationResult = ScoringService.aggregate(
        control_analyses, ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
    )
    # Degradation gate must fire → underpowered_design weakness prepended.
    assert any(
        w.category == "underpowered_design"
        and "100%" in (w.summary or "")
        and "4/4" in (w.summary or "")
        for w in result.weaknesses
    ), f"degradation gate did not fire correctly: {result.weaknesses}"


def test_aggregate_treatment_arm_degradation_unchanged() -> None:
    """Sanity: treatment-arm agents still attempt both classifications,
    so the 2N denominator is preserved. Mirrors the pre-#90 behavior."""
    from sidira_simulator.schemas.simulation import SimulationResult

    # 4 treatment agents, all sentiment fails, weakness succeeds.
    # Total attempted = 2N = 8; failures = 4; rate = 50% — at the
    # strict-`>` threshold, no degradation.
    treatment_analyses = [
        AgentAnalysis(
            agent_id=f"t{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            sample_index=0,
            weakness=WeaknessClassification(categories=[]),
            sentiment=SentimentClassification(
                sentiment=Sentiment.NEUTRAL, confidence=0.0, one_line_summary=""
            ),
            weakness_failed=False,
            weakness_attempted=True,
            sentiment_failed=True,
        )
        for i in range(4)
    ]
    result: SimulationResult = ScoringService.aggregate(
        treatment_analyses, ScoringConfig(min_sample_size=1, bootstrap_resamples=0)
    )
    # 50% exactly → no degradation message
    assert not any("discounted" in (w.summary or "") for w in result.weaknesses)


@pytest.mark.asyncio
async def test_analyze_single_arm_arm_none_keeps_treatment_prompts() -> None:
    """Single-arm sims (arm=None, pre-#90 callers) keep the original
    two-classification flow with the treatment-style prompts. Backwards
    compatibility check."""
    recorder = _PromptRecorder()
    svc = ScoringService(chat_client=recorder)

    await svc.analyze(
        Hypothesis(capability_name="reorder", prose="test change"),
        AgentReaction(
            agent_id="x0",
            persona_id="p0",
            persona_name="P0",
            reaction_text="reaction",
            sample_index=0,
            arm=None,
        ),
    )
    assert len(recorder.calls) == 2  # weakness + sentiment as before


# ── Codex P1 fix (PR #96): CI must bracket lift, always ──────────────


def test_lift_ci_brackets_point_estimate_with_shrinkage() -> None:
    """Codex P1: prior version computed lift as full per-arm score diff
    but bootstrapped only the sentiment-delta CI. At small N + default
    shrinkage that produced cases where the CI excluded the point
    estimate (e.g. lift=15, ci=(30,30)). Post-fix: both numbers come from
    the same matched-subset statistic, so CI brackets lift by construction.
    """
    treatment, control = _matched_pairs(
        1, t_sentiment=Sentiment.POSITIVE, c_sentiment=Sentiment.NEUTRAL
    )
    _t, _c, lift = aggregate_ab(treatment, control, _CI_CFG, run_seed=42)
    assert lift.lift is not None
    assert lift.lift_ci is not None
    assert (
        lift.lift_ci[0] <= lift.lift <= lift.lift_ci[1]
    ), f"CI {lift.lift_ci} must bracket point estimate {lift.lift}"


# ── Pairing key uses (persona_id, sample_index), not persona alone ────


def test_pairing_distinguishes_sample_index() -> None:
    # Two treatment agents on same persona at sample_index 0 and 1;
    # control has only sample_index 0 → one matched, one unmatched.
    treatment = [
        _a(agent_id="t0", persona_id="p0", sample_index=0, sentiment=Sentiment.POSITIVE),
        _a(agent_id="t1", persona_id="p0", sample_index=1, sentiment=Sentiment.POSITIVE),
    ]
    control = [
        _a(agent_id="c0", persona_id="p0", sample_index=0, sentiment=Sentiment.NEGATIVE),
    ]
    _t, _c, lift = aggregate_ab(treatment, control, _NO_CI_CFG, run_seed=42)
    assert lift.paired_n == 1
    assert lift.unpaired_treatment == 1
    assert lift.unpaired_control == 0


# ── Metric↔sentiment disagreement guardrail (#321) ───────────────────────


class _SentimentArmChat:
    """Scripted chat: returns a chosen sentiment for treatment-arm reactions and
    another for control-arm reactions, keyed off the marker token in the reaction
    text. Drives a deterministic, separable sentiment lift sign so the guardrail's
    composition is testable end-to-end through `score_ab`."""

    def __init__(self, *, treatment: Sentiment, control: Sentiment) -> None:
        self._treatment = treatment
        self._control = control

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        user_msg = next(m["content"] for m in messages if m["role"] == "user")
        if schema is WeaknessClassification:
            return WeaknessClassification(categories=[], primary_reason="ok")
        bucket = self._treatment if "TREATMENT_REACTION" in user_msg else self._control
        return SentimentClassification(sentiment=bucket, confidence=1.0, one_line_summary="")

    def chat(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


def _metric_hypothesis() -> Hypothesis:
    """A conversion-metric Hypothesis (carries the required template fields)."""
    return Hypothesis(
        capability_name="reorder",
        prose="Add a one-tap reorder button to the home tab.",
        metric_name="conversion",
        conversion_action="tap reorder and check out",
        conversion_action_label="check out now",
        decision_point="you opened the home tab with a past order visible",
    )


def _metric_arms(
    n: int,
    *,
    treatment_metric_p: float,
    control_metric_p: float,
) -> tuple[list[AgentReaction], list[AgentReaction]]:
    """N matched treatment/control reactions carrying a fixed `metric_p` per arm.

    A constant per-arm `metric_p` makes every paired delta identical, so the
    paired-bootstrap CI collapses onto the point estimate (zero variance) — it
    cleanly excludes zero whenever the delta is non-zero, exercising the
    separability gate deterministically.
    """
    treatment = [
        AgentReaction(
            agent_id=f"t{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="TREATMENT_REACTION",
            sample_index=0,
            arm="treatment",
            metric_p=treatment_metric_p,
        )
        for i in range(n)
    ]
    control = [
        AgentReaction(
            agent_id=f"c{i}",
            persona_id=f"p{i}",
            persona_name=f"P{i}",
            reaction_text="CONTROL_REACTION",
            sample_index=0,
            arm="control",
            metric_p=control_metric_p,
        )
        for i in range(n)
    ]
    return treatment, control


@pytest.mark.asyncio
async def test_disagreement_harm_misread_flags_and_adds_guardrail_weakness() -> None:
    """Metric positive-and-separable (+pp) while sentiment is negative-and-separable
    → metric_sentiment_disagreement True, a hidden_guardrail_risk weakness, and a
    caveat that says to trust sentiment for harm."""
    # Treatment metric_p high (0.62) vs control low (0.50) → metric +sep.
    # Treatment sentiment NEGATIVE, control POSITIVE → sentiment lift -sep.
    treatment, control = _metric_arms(6, treatment_metric_p=0.62, control_metric_p=0.50)
    svc = ScoringService(
        chat_client=_SentimentArmChat(treatment=Sentiment.NEGATIVE, control=Sentiment.POSITIVE)
    )
    result, _ = await svc.score_ab(
        _metric_hypothesis(), treatment, control, config=_CI_CFG, run_seed=42
    )

    # Sanity: the two signals are separable and opposite.
    assert result.metric_lift_ci_pp is not None and result.metric_lift_ci_pp[0] > 0
    assert result.lift_ci is not None and result.lift_ci[1] < 0

    assert result.metric_sentiment_disagreement is True
    assert result.metric_sentiment_disagreement_caveat is not None
    caveat = result.metric_sentiment_disagreement_caveat
    assert "harm-misread" in caveat
    assert "trust sentiment for harm" in caveat.lower()
    assert "#222" in caveat
    # The hidden_guardrail_risk weakness was appended.
    guardrails = [w for w in result.weaknesses if w.category == "hidden_guardrail_risk"]
    assert len(guardrails) == 1
    assert "sentiment" in guardrails[0].summary.lower()
    # Purely additive: headline + lift values untouched.
    assert result.confidence_score == pytest.approx(result.treatment_score)
    assert result.metric_lift_pp is not None and result.metric_lift_pp > 0


@pytest.mark.asyncio
async def test_disagreement_hidden_improvement_flags_without_weakness() -> None:
    """Metric negative-and-separable while sentiment is positive-and-separable →
    flag True, caveat set, but NO hidden_guardrail_risk weakness (not a risk)."""
    # Treatment metric_p low (0.40) vs control high (0.55) → metric -sep.
    # Treatment sentiment POSITIVE, control NEGATIVE → sentiment lift +sep.
    treatment, control = _metric_arms(6, treatment_metric_p=0.40, control_metric_p=0.55)
    svc = ScoringService(
        chat_client=_SentimentArmChat(treatment=Sentiment.POSITIVE, control=Sentiment.NEGATIVE)
    )
    result, _ = await svc.score_ab(
        _metric_hypothesis(), treatment, control, config=_CI_CFG, run_seed=42
    )

    assert result.metric_lift_ci_pp is not None and result.metric_lift_ci_pp[1] < 0
    assert result.lift_ci is not None and result.lift_ci[0] > 0

    assert result.metric_sentiment_disagreement is True
    assert result.metric_sentiment_disagreement_caveat is not None
    assert "hidden-improvement" in result.metric_sentiment_disagreement_caveat
    # No guardrail weakness for a hidden improvement.
    assert [w for w in result.weaknesses if w.category == "hidden_guardrail_risk"] == []


@pytest.mark.asyncio
async def test_agreement_same_sign_no_disagreement() -> None:
    """Both metric and sentiment positive-and-separable (they agree) → no flag."""
    treatment, control = _metric_arms(6, treatment_metric_p=0.62, control_metric_p=0.50)
    svc = ScoringService(
        chat_client=_SentimentArmChat(treatment=Sentiment.POSITIVE, control=Sentiment.NEGATIVE)
    )
    result, _ = await svc.score_ab(
        _metric_hypothesis(), treatment, control, config=_CI_CFG, run_seed=42
    )
    assert result.metric_lift_ci_pp is not None and result.metric_lift_ci_pp[0] > 0
    assert result.lift_ci is not None and result.lift_ci[0] > 0
    assert result.metric_sentiment_disagreement is False
    assert result.metric_sentiment_disagreement_caveat is None
    assert [w for w in result.weaknesses if w.category == "hidden_guardrail_risk"] == []


@pytest.mark.asyncio
async def test_one_sided_non_separable_no_disagreement() -> None:
    """Metric separable-positive but sentiment NOT separable (treatment/control
    sentiment equal → lift CI straddles zero) → no flag, even though signs differ
    nominally. Separability is the gate."""
    treatment, control = _metric_arms(6, treatment_metric_p=0.62, control_metric_p=0.50)
    # Both arms NEUTRAL → sentiment lift ≈ 0, CI straddles zero (not separable).
    svc = ScoringService(
        chat_client=_SentimentArmChat(treatment=Sentiment.NEUTRAL, control=Sentiment.NEUTRAL)
    )
    result, _ = await svc.score_ab(
        _metric_hypothesis(), treatment, control, config=_CI_CFG, run_seed=42
    )
    assert result.metric_lift_ci_pp is not None and result.metric_lift_ci_pp[0] > 0
    # sentiment not separable
    assert result.lift_ci is not None and result.lift_ci[0] <= 0 <= result.lift_ci[1]
    assert result.metric_sentiment_disagreement is False
    assert result.metric_sentiment_disagreement_caveat is None


@pytest.mark.asyncio
async def test_metric_ci_none_no_disagreement() -> None:
    """When the metric CI is None (bootstrap disabled → cannot assess metric
    separability), the guardrail is conservative: no flag."""
    treatment, control = _metric_arms(6, treatment_metric_p=0.62, control_metric_p=0.50)
    svc = ScoringService(
        chat_client=_SentimentArmChat(treatment=Sentiment.NEGATIVE, control=Sentiment.POSITIVE)
    )
    # bootstrap_resamples=0 → metric_lift_ci_pp is None.
    result, _ = await svc.score_ab(
        _metric_hypothesis(), treatment, control, config=_NO_CI_CFG, run_seed=42
    )
    assert result.metric_lift_ci_pp is None
    assert result.metric_sentiment_disagreement is False
    assert result.metric_sentiment_disagreement_caveat is None
    assert [w for w in result.weaknesses if w.category == "hidden_guardrail_risk"] == []


@pytest.mark.asyncio
async def test_no_metric_name_keeps_disagreement_defaults() -> None:
    """A non-metric hypothesis never enters the metric branch → both guardrail
    fields stay at their defaults (byte-identical, backwards-compatible)."""
    treatment, control = _metric_arms(6, treatment_metric_p=0.62, control_metric_p=0.50)
    svc = ScoringService(
        chat_client=_SentimentArmChat(treatment=Sentiment.NEGATIVE, control=Sentiment.POSITIVE)
    )
    plain = Hypothesis(capability_name="reorder", prose="test")
    result, _ = await svc.score_ab(plain, treatment, control, config=_CI_CFG, run_seed=42)
    assert result.metric_name is None
    assert result.metric_sentiment_disagreement is False
    assert result.metric_sentiment_disagreement_caveat is None
    assert [w for w in result.weaknesses if w.category == "hidden_guardrail_risk"] == []
