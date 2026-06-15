"""Scoring service — turns N agent reactions into a SimulationResult.

Per-agent: weakness classification + sentiment classification (two `chat_json`
calls in parallel). Aggregation: `0.6 × sentiment_score + 0.4 × (1 − weakness_concentration)`
on a 0–100 scale. This is the locked formula from /plan-eng-review.

The scorer is independent of SimulationRunner so its formula is unit-testable
without driving an end-to-end simulation.
"""

from __future__ import annotations

import asyncio
import random
import secrets
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

import structlog

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.schemas.scoring import (
    ABLiftResult,
    AgentAnalysis,
    ConversionLiftResult,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from sidira_simulator.schemas.simulation import Hypothesis, SimulationResult, Weakness
from sidira_simulator.services.statistics import bootstrap_percentile_ci, wilson_interval

# Arbitrary integer XOR mask used to derive a bootstrap-specific RNG seed
# from the runner's run_seed, so the bootstrap resample stream cannot
# collide with the identity-seed stream (which uses sha256 over a different
# namespace tuple — distinct domain anyway, so this is defense in depth).
_BOOTSTRAP_SEED_MIX = 0xB007_5747_5474

log = structlog.get_logger()


# ─── Per-agent reaction record passed to the scorer ─────────────────────


class AgentReaction:
    """Lightweight DTO so scoring doesn't import SimulationRunner internals.

    `sample_index` + `arm` (Phase 4.6 #90): both default-safe for single-arm
    callers. The pair (persona_id, sample_index) is the lift formula's
    matching key; `arm` partitions the population at the score step.

    `reaction_distribution` (#221 hierarchical scoring): the agent's full
    elicited reaction distribution as (text, probability) pairs, when the run
    used verbalized sampling (`samples > 1`). `reaction_text` always carries
    the modal (highest-probability) reaction — the frozen identity reaction —
    so a None/single-entry distribution leaves the historical path untouched.
    When present and >1 entry, `score()` classifies every reaction and feeds a
    hierarchical bootstrap that propagates within-agent variance into the CI.
    """

    __slots__ = (
        "agent_id",
        "persona_id",
        "persona_name",
        "reaction_text",
        "sample_index",
        "arm",
        "reaction_distribution",
        "conversion_p",
    )

    def __init__(
        self,
        *,
        agent_id: str,
        persona_id: str,
        persona_name: str,
        reaction_text: str,
        sample_index: int = 0,
        arm: str | None = None,
        reaction_distribution: list[tuple[str, float]] | None = None,
        conversion_p: float | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.persona_id = persona_id
        self.persona_name = persona_name
        self.reaction_text = reaction_text
        self.sample_index = sample_index
        self.arm = arm
        self.reaction_distribution = reaction_distribution
        # #221 §3a: the agent's conversion propensity (p_conv) when the run used
        # a conversion metric; None when no metric was set OR the per-agent
        # conversion elicitation failed. Scored as a paired delta, never a level.
        self.conversion_p = conversion_p


# ─── Per-agent classified reaction distribution (#221) ──────────────────


@dataclass
class _AnalysisGroup:
    """One agent's classified reaction distribution (#221 hierarchical scoring).

    `modal` is the analysis of the agent's modal (highest-probability)
    reaction — the canonical row used for the point estimate, the per-agent
    table, and the frozen-identity contract. `distribution` pairs every
    classified reaction with its probability weight (≥1 entry; for the
    k=1 / off path it is just ``[(modal, 1.0)]``). The hierarchical bootstrap
    draws within `distribution`; everything else reads `modal`.
    """

    modal: AgentAnalysis
    distribution: list[tuple[AgentAnalysis, float]]


def _draw_within_agent(
    group: Sequence[tuple[AgentAnalysis, float]],
    rng: random.Random,
) -> AgentAnalysis:
    """Draw one classified reaction from an agent's elicited distribution.

    `group` is a non-empty list of (analysis, probability) for a single agent —
    one entry per verbalized-sampling reaction (#221). The draw is weighted by
    probability so likelier reactions dominate, mirroring the normalized weights
    on `ReactionDistribution`. A single-entry group returns its sole analysis
    without touching the RNG (the k=1 / off path within a mixed run).
    """
    if len(group) == 1:
        return group[0][0]
    analyses, weights = zip(*group)
    return rng.choices(analyses, weights=weights, k=1)[0]


# ─── Prompt templates ──────────────────────────────────────────────────


_VALID_CATEGORIES = {
    "wrong_metric",
    "wrong_cohort",
    "broken_mechanism",
    "untestable_hypothesis",
    "hidden_guardrail_risk",
    "underpowered_design",
}


_WEAKNESS_SYSTEM = """You are an experimentation expert classifying experimental-design weaknesses
that a user's reaction reveals about a proposed product change.

The six weakness categories (use ONLY these exact strings):

1. wrong_metric — primary metric doesn't capture the behavioral change the feature would actually cause
2. wrong_cohort — feature is being tested on users unlikely to respond meaningfully
3. broken_mechanism — feature doesn't address the actual behavioral driver
4. untestable_hypothesis — too vague to produce a falsifiable prediction
5. hidden_guardrail_risk — feature might lift the primary metric while damaging a downstream metric
6. underpowered_design — segment too narrow, MDE too optimistic, duration too short

You will receive ONE user's reaction. Identify which weaknesses this reaction reveals.
A reaction may reveal zero, one, or several weaknesses. If the reaction reveals NO weakness
(the user is enthusiastic, the design seems sound for them), return an empty `categories` list.

Return STRICT JSON: {"categories": ["<cat1>", ...], "primary_reason": "<one sentence>"}.
Use the exact category strings above; any other string is invalid."""


_SENTIMENT_SYSTEM = """You classify a single user's reception of a proposed product change.

Reception buckets:
- positive: the user would welcome / try / engage with the change
- neutral: the user is indifferent or would not change behavior either way
- negative: the user would resist / disengage / churn-risk on the change

Return STRICT JSON:
{"sentiment": "positive|neutral|negative", "confidence": 0.0..1.0, "one_line_summary": "<one sentence>"}.

Use lower confidence (0.4-0.6) when the reaction is genuinely mixed."""


# Phase 4.6 #90 (codex R2-P1): the control arm's reaction is to the
# product AS IT WORKS TODAY, not to a proposed change. Reusing the
# treatment-arm sentiment prompt mislabels the input — the classifier
# would try to read the reaction as reception of a hypothetical change
# the user never saw. This prompt frames the classification correctly.
_SENTIMENT_SYSTEM_CONTROL = """You classify a single user's reception of a product as it works for them today.

This is the STATUS-QUO arm of an A/B simulation — the user is reacting to the CURRENT
product, NOT to any proposed change. Do not speculate about what the user might think
of any change; only classify how they feel about the product as described.

Reception buckets:
- positive: the user welcomes / values / engages with the current product
- neutral: the user uses the product without strong feelings either way
- negative: the user is frustrated / would disengage / churn-risk on the current product

Return STRICT JSON:
{"sentiment": "positive|neutral|negative", "confidence": 0.0..1.0, "one_line_summary": "<one sentence>"}.

Use lower confidence (0.4-0.6) when the reaction is genuinely mixed."""


def _build_weakness_user_prompt(hypothesis: Hypothesis, reaction: str) -> str:
    return (
        f"Proposed change (capability `{hypothesis.capability_name}`):\n"
        f"{hypothesis.prose}\n\n"
        f"User's reaction:\n{reaction}"
    )


def _build_sentiment_user_prompt(hypothesis: Hypothesis, reaction: str) -> str:
    return (
        f"Proposed change (capability `{hypothesis.capability_name}`):\n"
        f"{hypothesis.prose}\n\n"
        f"User's reaction:\n{reaction}"
    )


def _build_sentiment_user_prompt_control(hypothesis: Hypothesis, reaction: str) -> str:
    return (
        f"Capability under evaluation: `{hypothesis.capability_name}` (status-quo arm; "
        f"the user is reacting to the product AS IT WORKS TODAY, not to any proposed change).\n\n"
        f"User's reaction:\n{reaction}"
    )


# ─── ScoringService ────────────────────────────────────────────────────


class ScoringService:
    def __init__(self, chat_client: ChatClient | None = None) -> None:
        self._chat_explicit = chat_client

    @property
    def _chat(self) -> ChatClient:
        if self._chat_explicit is None:
            self._chat_explicit = get_chat_client()
        return self._chat_explicit

    # — Per-agent analysis ——————————————————————————————————————————

    async def analyze(self, hypothesis: Hypothesis, reaction: AgentReaction) -> AgentAnalysis:
        """Run weakness + sentiment classification in parallel for one agent.

        Phase 4.6 #90 (codex R2-P1): when `reaction.arm == "control"`, the
        user reacted to the STATUS-QUO product, not to a proposed change.
        Two consequences:
          - Sentiment uses a control-specific system prompt that frames
            reception as feelings-about-the-current-product, NOT
            reception-of-a-change. Mislabeling there would corrupt
            `control_score` and therefore lift.
          - Weakness classification is SKIPPED. The 6 categories
            (wrong_metric, wrong_cohort, etc.) describe experiment-design
            weaknesses in the proposed change, which is undefined for the
            control arm. Returning empty `categories` keeps the schema
            stable and saves the LLM call.
        Single-arm sims (arm=None) keep the existing treatment-style
        prompts unchanged.

        #221 §3.3.1 delta-mode: the `current_state` shadow arm is the existing
        control framing applied as a 1:1 paired shadow in single-arm mode — the
        same personas reacting to TODAY's product. It is control-equivalent for
        analysis: its reaction was composed with the control task block (see
        SimulationRunner._materialize_agent mapping current_state → control), so
        it MUST be scored with the same status-quo sentiment prompt and weakness
        skip. Scoring it as treatment would frame status-quo reception as
        reception-of-a-change and corrupt current_state_score / the delta. (codex P1)
        """
        is_control = reaction.arm in ("control", "current_state")

        if is_control:
            # No-op weakness coroutine so gather() still works without a
            # second LLM call. Returns a deterministic empty classification.
            async def _noop_weakness() -> WeaknessClassification:
                return WeaknessClassification(
                    categories=[],
                    primary_reason="(control arm — weakness classification not applicable)",
                )

            weakness_task = _noop_weakness()
            sentiment_system = _SENTIMENT_SYSTEM_CONTROL
            sentiment_user = _build_sentiment_user_prompt_control(
                hypothesis, reaction.reaction_text
            )
        else:
            weakness_task = asyncio.to_thread(
                self._chat.chat_json,
                [
                    {"role": "system", "content": _WEAKNESS_SYSTEM},
                    {
                        "role": "user",
                        "content": _build_weakness_user_prompt(hypothesis, reaction.reaction_text),
                    },
                ],
                WeaknessClassification,
            )
            sentiment_system = _SENTIMENT_SYSTEM
            sentiment_user = _build_sentiment_user_prompt(hypothesis, reaction.reaction_text)

        sentiment_task = asyncio.to_thread(
            self._chat.chat_json,
            [
                {"role": "system", "content": sentiment_system},
                {"role": "user", "content": sentiment_user},
            ],
            SentimentClassification,
        )
        weakness, sentiment = await asyncio.gather(
            weakness_task, sentiment_task, return_exceptions=True
        )

        weakness_failed = isinstance(weakness, BaseException)
        sentiment_failed = isinstance(sentiment, BaseException)
        if weakness_failed:
            log.warning(
                "scoring.weakness_classification_failed",
                agent_id=reaction.agent_id,
                persona_id=reaction.persona_id,
                error=str(weakness),
                exc_type=type(weakness).__name__,
            )
            weakness = WeaknessClassification(
                categories=[], primary_reason="(classification failed)"
            )
        if sentiment_failed:
            log.warning(
                "scoring.sentiment_classification_failed",
                agent_id=reaction.agent_id,
                persona_id=reaction.persona_id,
                error=str(sentiment),
                exc_type=type(sentiment).__name__,
            )
            sentiment = SentimentClassification(
                sentiment=Sentiment.NEUTRAL,
                confidence=0.0,
                one_line_summary="(classification failed)",
            )

        # Drop any categories the LLM hallucinated outside the closed set.
        weakness.categories = [c for c in weakness.categories if c in _VALID_CATEGORIES]

        return AgentAnalysis(
            agent_id=reaction.agent_id,
            persona_id=reaction.persona_id,
            persona_name=reaction.persona_name,
            sample_index=reaction.sample_index,
            weakness=weakness,
            sentiment=sentiment,
            weakness_failed=weakness_failed,
            sentiment_failed=sentiment_failed,
            weakness_attempted=not is_control,
        )

    # — Pack-level scoring (A/B mode) ————————————————————————————————

    async def score_ab(
        self,
        hypothesis: Hypothesis,
        treatment_reactions: list[AgentReaction],
        control_reactions: list[AgentReaction],
        *,
        run_seed: int | None = None,
        config: ScoringConfig | None = None,
    ) -> tuple[SimulationResult, list[AgentAnalysis]]:
        """Fan out per-agent analysis across both arms, then aggregate with lift.

        Returns a single composed SimulationResult whose `confidence_score`
        is the treatment arm's score (the headline number PMs read) and
        whose `lift*` / `treatment_score` / `control_score` fields surface
        the paired-bootstrap output. `analyses` includes every successful
        agent across both arms, preserving the per-agent table render.
        """
        if not treatment_reactions and not control_reactions:
            return (
                SimulationResult(
                    confidence_score=0.0,
                    weaknesses=[
                        Weakness(
                            category="underpowered_design",
                            summary="No agent reactions available to score.",
                        )
                    ],
                    refinement_suggestions=[],
                ),
                [],
            )

        # Phase 4.6 #90 (codex R5-P2): single-arm-empty A/B run. If every
        # agent in one arm failed materialization upstream, the runner
        # still hands us a non-empty `all_reactions`, but the empty arm's
        # `aggregate()` returns confidence_score=0 with no weaknesses —
        # which the composition step would surface as "treatment is
        # terrible" or "control is terrible" with no explanation. Treat
        # this as degraded/uncomputable: name the missing arm in an
        # underpowered_design weakness, return paired_n=0, skip the
        # refinement / aggregate fan-out entirely so we don't burn LLM
        # calls on a half-broken run.
        if not treatment_reactions or not control_reactions:
            missing = "treatment" if not treatment_reactions else "control"
            # §3a: a conversion-metric run must surface the same honest
            # uncomputable state on the conversion fields (paired_n=0 + the weak
            # regime), or a missing-arm conversion run would be indistinguishable
            # from a non-conversion run (all conversion_* at schema default None).
            conversion_fields: dict[str, object] = {}
            if hypothesis.metric_name == "conversion":
                regime, relative = conversion_lift_honesty(ConversionLiftResult())
                conversion_fields = {
                    "conversion_lift_paired_n": 0,
                    "conversion_regime": regime,
                    "conversion_lift_relative": relative,
                }
            return (
                SimulationResult(
                    confidence_score=0.0,
                    weaknesses=[
                        Weakness(
                            category="underpowered_design",
                            summary=(
                                f"A/B simulation completed with no successful "
                                f"{missing}-arm agents; lift not computable."
                            ),
                        )
                    ],
                    refinement_suggestions=[],
                    lift_paired_n=0,
                    **conversion_fields,
                ),
                [],
            )

        all_reactions = treatment_reactions + control_reactions
        analyses = await asyncio.gather(
            *(self.analyze(hypothesis, r) for r in all_reactions),
            return_exceptions=False,
        )
        treatment_analyses = analyses[: len(treatment_reactions)]
        control_analyses = analyses[len(treatment_reactions) :]

        treatment_result, control_result, lift = aggregate_ab(
            treatment_analyses,
            control_analyses,
            config,
            run_seed=run_seed,
        )

        # Compose: headline is treatment arm (the change the PM is testing).
        # Lift fields surface the comparison, per-arm scores let the result
        # page split the table. Weaknesses come from the treatment arm —
        # those are the weaknesses in the PROPOSED change. Control-arm
        # weaknesses describe the status quo and aren't shown by default.
        composed = treatment_result.model_copy(
            update={
                "treatment_score": treatment_result.confidence_score,
                "control_score": control_result.confidence_score,
                "lift": lift.lift,
                "lift_ci": lift.lift_ci,
                # Phase 4.6 #90 (codex R3-P2b): pass paired_n through
                # verbatim so the serialized result can distinguish
                # "A/B attempted, no matched pairs" (lift_paired_n=0)
                # from "single-arm sim, no A/B" (lift_paired_n=None,
                # the schema default — single-arm sims never call this
                # composition path).
                "lift_paired_n": lift.paired_n,
                "lift_unpaired_treatment": lift.unpaired_treatment,
                "lift_unpaired_control": lift.unpaired_control,
                "lift_sentiment_failure_drops": lift.sentiment_failure_drops,
            }
        )

        # §3a conversion lift: only when the Hypothesis carried a conversion
        # metric. The per-agent `conversion_p` rides on the AgentReactions
        # (turn-2 elicitation in the runner); aggregate the paired delta and
        # graft the conversion_* fields on. A non-conversion run skips this
        # entirely, leaving every conversion_* field at its schema default —
        # byte-identical to today's A/B path.
        if hypothesis.metric_name == "conversion":
            conv = aggregate_conversion_lift(
                treatment_reactions,
                control_reactions,
                config,
                run_seed=run_seed,
            )
            regime, relative = conversion_lift_honesty(conv)
            composed = composed.model_copy(
                update={
                    "conversion_lift_pp": conv.lift_pp,
                    "conversion_lift_ci_pp": conv.lift_ci_pp,
                    "conversion_lift_paired_n": conv.paired_n,
                    "conversion_lift_unpaired_treatment": conv.unpaired_treatment,
                    "conversion_lift_unpaired_control": conv.unpaired_control,
                    "conversion_lift_elicitation_failure_drops": (conv.elicitation_failure_drops),
                    "conversion_regime": regime,
                    "conversion_lift_relative": relative,
                }
            )
        return composed, list(analyses)

    # — Pack-level scoring ——————————————————————————————————————————

    async def _analyze_group(
        self, hypothesis: Hypothesis, reaction: AgentReaction
    ) -> _AnalysisGroup:
        """Classify an agent's reaction(s) into an `_AnalysisGroup` (#221).

        Default / off path (no distribution, or a single sample): one
        `analyze()` call, exactly as before — the group degenerates to
        ``[(analysis, 1.0)]`` and the modal IS that analysis.

        Distribution path (`samples > 1`): classify EVERY elicited reaction
        (weakness + sentiment per sample, fanned out concurrently), then pair
        each analysis with its sample probability. The modal analysis is the
        one for the highest-probability sample (ties → first), matching
        `ReactionDistribution.modal` and the frozen `initial_reaction`, so the
        point estimate and per-agent table are identical to the modal-only run.
        """
        dist = reaction.reaction_distribution
        if not dist or len(dist) <= 1:
            analysis = await self.analyze(hypothesis, reaction)
            return _AnalysisGroup(modal=analysis, distribution=[(analysis, 1.0)])

        sub_reactions = [
            AgentReaction(
                agent_id=reaction.agent_id,
                persona_id=reaction.persona_id,
                persona_name=reaction.persona_name,
                reaction_text=text,
                sample_index=reaction.sample_index,
                arm=reaction.arm,
            )
            for text, _weight in dist
        ]
        analyses = await asyncio.gather(
            *(self.analyze(hypothesis, sub) for sub in sub_reactions),
            return_exceptions=False,
        )
        paired = [(analysis, weight) for analysis, (_text, weight) in zip(analyses, dist)]
        # max() is stable on ties → first occurrence wins, matching
        # ReactionDistribution.modal (and therefore the frozen reaction_text).
        modal = max(paired, key=lambda pair: pair[1])[0]
        return _AnalysisGroup(modal=modal, distribution=paired)

    async def score(
        self,
        hypothesis: Hypothesis,
        reactions: list[AgentReaction],
        *,
        run_seed: int | None = None,
        config: ScoringConfig | None = None,
    ) -> tuple[SimulationResult, list[AgentAnalysis]]:
        """Fan out per-agent analysis, then aggregate.

        `run_seed` makes the bootstrap CI on confidence_score deterministic
        when the caller wants reproducibility. `config` lets the caller swap
        in a `ScoringConfig(bootstrap_resamples=0)` to skip the CI.

        #221 hierarchical scoring: when any reaction carries a multi-sample
        `reaction_distribution`, every elicited reaction is classified and the
        per-agent distributions feed a hierarchical bootstrap so the CI
        reflects within-agent variance. The headline `confidence_score` (and
        the returned per-agent `analyses`) still come from the modal reactions,
        so the default/off path (no distribution) is byte-identical to before.
        """
        if not reactions:
            return (
                SimulationResult(
                    confidence_score=0.0,
                    weaknesses=[
                        Weakness(
                            category="underpowered_design",
                            summary="No agent reactions available to score.",
                        )
                    ],
                    refinement_suggestions=[],
                ),
                [],
            )

        groups = await asyncio.gather(
            *(self._analyze_group(hypothesis, r) for r in reactions),
            return_exceptions=False,
        )
        modal_analyses = [g.modal for g in groups]
        if any(len(g.distribution) > 1 for g in groups):
            result = self.aggregate(
                modal_analyses,
                config,
                run_seed=run_seed,
                agent_distributions=[g.distribution for g in groups],
            )
        else:
            result = self.aggregate(modal_analyses, config, run_seed=run_seed)
        return result, modal_analyses

    # — Aggregation (pure function, no LLM) ————————————————————————————

    _SENTIMENT_VALUE: dict[Sentiment, float] = {
        Sentiment.POSITIVE: 1.0,
        Sentiment.NEUTRAL: 0.5,
        Sentiment.NEGATIVE: 0.0,
    }

    @classmethod
    def _compute_score(
        cls,
        analyses: Sequence[AgentAnalysis],
        cfg: ScoringConfig,
    ) -> tuple[float, float, float]:
        """Pure formula: (confidence_0_100, sentiment_score, weakness_signal).

        Extracted from `aggregate()` so that bootstrap resamples can recompute
        the score cheaply without rebuilding the weakness surface or applying
        the underpowered gate. No rounding — callers round at presentation time.

        Behavior matches the pre-extraction inline formula exactly; pinned by
        `test_aggregate_parity_snapshot`.
        """
        n = len(analyses)
        if n == 0:
            # Defensive: aggregate() short-circuits before calling us, but
            # bootstrap resamples never produce empty lists either. If a
            # caller ever sneaks an empty list through, fall back to neutral.
            return 0.0, 0.5, 1.0

        # ── Sentiment: confidence-weighted mean with shrinkage toward 0.5 ──
        if cfg.use_sentiment_confidence:
            num = sum(
                a.sentiment.confidence * cls._SENTIMENT_VALUE[a.sentiment.sentiment]
                for a in analyses
            )
            denom = sum(a.sentiment.confidence for a in analyses)
        else:
            num = sum(cls._SENTIMENT_VALUE[a.sentiment.sentiment] for a in analyses)
            denom = float(n)
        # Bayesian shrinkage: add prior_k pseudo-observations of neutral (0.5).
        num += cfg.sentiment_prior_k * 0.5
        denom += cfg.sentiment_prior_k
        sentiment_score = num / denom if denom > 0 else 0.5

        # ── Weakness: dedupe categories per agent, then any-flag share ──
        agents_with_any_weakness = sum(1 for a in analyses if set(a.weakness.categories))
        any_flag_share = agents_with_any_weakness / n
        weakness_signal = 1.0 - any_flag_share

        confidence = (
            cfg.sentiment_weight * sentiment_score + cfg.weakness_weight * weakness_signal
        ) * 100.0
        return confidence, sentiment_score, weakness_signal

    @classmethod
    def aggregate(
        cls,
        analyses: Iterable[AgentAnalysis],
        config: ScoringConfig | None = None,
        *,
        run_seed: int | None = None,
        agent_distributions: Sequence[Sequence[tuple[AgentAnalysis, float]]] | None = None,
    ) -> SimulationResult:
        """Aggregate per-agent analyses into a SimulationResult.

        Codex-reviewed formula (Wave 4, 2026-05-21):
        - sentiment_score: confidence-weighted mean with Bayesian shrinkage
          toward neutral. Small-N runs don't reach extremes.
        - weakness_signal: 1 − any_flag_share, where any_flag_share is the
          fraction of agents flagging ≥1 weakness (deduped within each agent
          to prevent a malformed LLM response from double-counting).
        - confidence: 100 × (sentiment_weight × sentiment_score +
                             weakness_weight × weakness_signal).

        Underpowered gate: if N < config.min_sample_size, prepend an
        `underpowered_design` weakness so the PM sees the limitation.

        `agent_distributions` (#221 hierarchical scoring, optional): per-agent
        lists of (analysis, probability) aligned 1:1 with `analyses` (each
        agent's modal analysis is the matching `analyses` entry). When provided
        and at least one agent has >1 reaction, the confidence_score CI is
        computed by a two-level bootstrap (resample agents, then draw a
        reaction within each) so it reflects within-agent variance. The point
        estimate, weakness surface, and gates always read the modal `analyses`,
        so passing None (or all single-entry distributions) is byte-identical
        to the historical flat bootstrap.
        """
        cfg = config or ScoringConfig()
        analyses_list = list(analyses)
        n = len(analyses_list)
        if n == 0:
            return SimulationResult(
                confidence_score=0.0,
                weaknesses=[],
                refinement_suggestions=[],
            )

        confidence, _sentiment, _weakness_signal = cls._compute_score(analyses_list, cfg)

        # ── Phase 2.5 #8 degradation guard ──
        # Count weakness + sentiment classification failures independently
        # (total = 2N). If the failure rate exceeds the configured threshold,
        # apply a multiplicative discount to the score (and CI) and prepend an
        # underpowered_design weakness so the PM sees the degraded state.
        # Without this, a totally-failed run silently returns ~70 (neutral
        # sentiment with shrinkage, zero weakness flags) — misleadingly fine.
        # Phase 4.6 #90 (codex R3-P2a): count only ATTEMPTED classifications.
        # Treatment + single-arm agents attempt 2 (weakness + sentiment);
        # control-arm agents skip weakness, so attempting 1. Without this,
        # a fully-failed control-sentiment run reports 50% (N failures /
        # 2N total) and never trips the strict `>` degradation threshold.
        failed_classifications = sum(
            int(a.weakness_failed) + int(a.sentiment_failed) for a in analyses_list
        )
        total_classifications = sum(int(a.weakness_attempted) + 1 for a in analyses_list)
        failure_rate = (
            failed_classifications / total_classifications if total_classifications > 0 else 0.0
        )
        degraded = failure_rate > cfg.degradation_threshold
        if degraded:
            discount_factor = 1.0 - cfg.degradation_discount
            confidence *= discount_factor

        # ── Bootstrap CI on the aggregate score ──
        # bootstrap_resamples=0 is a sentinel that skips the bootstrap entirely
        # (existing tests opt out so they don't pay B × O(n) per assertion).
        confidence_score_ci: tuple[float, float] | None = None
        rounded_score = round(confidence, cfg.confidence_rounding)
        if cfg.bootstrap_resamples > 0:
            effective_seed = (
                run_seed if run_seed is not None else secrets.randbits(53)
            ) ^ _BOOTSTRAP_SEED_MIX
            rng = random.Random(effective_seed)
            # #221 hierarchical scoring: when per-agent reaction distributions
            # are supplied (and at least one agent has >1 reaction), run a
            # two-level bootstrap — resample agents with replacement AND draw
            # one classified reaction within each, weighted by sample
            # probability. This folds WITHIN-agent variance (the
            # verbalized-sampling spread) into the CI on top of the
            # BETWEEN-agent variance the flat bootstrap already captures, so
            # the interval stops being "precisely wrong" around a single
            # collapsed reaction per agent. The point estimate (`confidence`)
            # is untouched: it reads the modal analyses, preserving the
            # frozen-identity headline. Falls back to the historical flat
            # bootstrap when no distributions are present, so the default path
            # is byte-identical.
            use_hierarchical = (
                agent_distributions is not None
                and len(agent_distributions) == n
                and any(len(group) > 1 for group in agent_distributions)
            )
            if use_hierarchical:
                groups = [list(group) for group in agent_distributions]

                def _hierarchical_statistic(
                    resampled_groups: Sequence[Sequence[tuple[AgentAnalysis, float]]],
                ) -> float:
                    drawn = [_draw_within_agent(group, rng) for group in resampled_groups]
                    return cls._compute_score(drawn, cfg)[0]

                ci_low, ci_high = bootstrap_percentile_ci(
                    groups,
                    _hierarchical_statistic,
                    n_resamples=cfg.bootstrap_resamples,
                    rng=rng,
                )
            else:
                ci_low, ci_high = bootstrap_percentile_ci(
                    analyses_list,
                    lambda resample: cls._compute_score(resample, cfg)[0],
                    n_resamples=cfg.bootstrap_resamples,
                    rng=rng,
                )
            # Apply the degradation discount to the CI bounds too so the
            # interval shifts down with the point estimate — otherwise the
            # CI would bracket the raw score, not the displayed one.
            if degraded:
                ci_low *= discount_factor
                ci_high *= discount_factor
            ci_low_r = round(ci_low, cfg.confidence_rounding)
            ci_high_r = round(ci_high, cfg.confidence_rounding)
            # Codex P2 fix: independent rounding (and, more rarely, the
            # discrete percentile result itself) can violate the invariant
            # ci_low <= confidence_score <= ci_high at the edges. Clamp so
            # callers that inspect both fields always see a CI that brackets
            # the reported point estimate. Widening is at most one rounding
            # step when caused by rounding; can be larger if the raw
            # bootstrap interval itself failed to bracket (small B, small N).
            confidence_score_ci = (
                min(ci_low_r, rounded_score),
                max(ci_high_r, rounded_score),
            )

        # Rebuild the category → supporting-agents map for the top-K surface.
        # Kept out of _compute_score() so bootstrap resamples don't pay for it.
        category_agents: dict[str, list[str]] = {}
        for a in analyses_list:
            for cat in set(a.weakness.categories):
                category_agents.setdefault(cat, []).append(a.agent_id)

        # ── Weakness surface: top-K by frequency, each with a Wilson 95% CI ──
        category_counts = Counter({c: len(ids) for c, ids in category_agents.items()})
        top_weaknesses = []
        for cat, count in category_counts.most_common(cfg.top_k_weaknesses):
            ci_low, ci_high = wilson_interval(count, n)
            top_weaknesses.append(
                Weakness(
                    category=cat,
                    summary=_summarize_category(cat, count, n),
                    supporting_agent_ids=category_agents[cat][:5],
                    frequency=count / n,
                    ci_low=ci_low,
                    ci_high=ci_high,
                )
            )

        # ── Structural gates: low N and/or high classification failure rate ──
        # Both gates write to the same `underpowered_design` category. Codex
        # P2 flagged the noise risk for consumers that dedupe by category, so
        # we collapse into a single row when both fire, joined with a clear
        # AND so the user sees both root causes in one place.
        #
        # Counting note (codex P2): the degradation gate counts CLASSIFICATIONS
        # not agents — total=2N. "All sentiment fails / all weakness succeeds"
        # is exactly 50% and therefore doesn't trigger by ticket-strict `>`.
        # If we ever want "agent degradation rate" semantics, count by agent
        # instead.
        weaknesses = list(top_weaknesses)
        low_n = n < cfg.min_sample_size
        if low_n or degraded:
            parts: list[str] = []
            if low_n:
                parts.append(
                    f"Only {n} agent{'s' if n != 1 else ''} reacted "
                    f"(min recommended: {cfg.min_sample_size})"
                )
            if degraded:
                failed_pct = int(round(failure_rate * 100))
                discount_pct = int(round(cfg.degradation_discount * 100))
                parts.append(
                    f"{failed_pct}% of LLM classifications failed "
                    f"({failed_classifications}/{total_classifications}); "
                    f"score discounted by {discount_pct}%"
                )
            summary = " AND ".join(parts) + ". Treat the score as provisional."
            weaknesses.insert(
                0,
                Weakness(category="underpowered_design", summary=summary),
            )

        return SimulationResult(
            confidence_score=rounded_score,
            confidence_score_ci=confidence_score_ci,
            weaknesses=weaknesses,
            refinement_suggestions=[],  # filled in by RefinementService caller
        )


def _summarize_category(category: str, count: int, total: int) -> str:
    return f"{count}/{total} agents flagged this — {category.replace('_', ' ')}."


# ─── A/B paired-lift aggregator (Phase 4.6 #90) ────────────────────────


def _agent_delta(treatment: AgentAnalysis, control: AgentAnalysis) -> float:
    """Confidence-weighted sentiment delta for one matched pair.

    Range [-1.0, +1.0]. Each side's sentiment value is shrunk toward
    the neutral midpoint (0.5) by the inverse of the classifier's
    confidence:

        value_shrunk = confidence × value + (1 − confidence) × 0.5

    The naive `confidence × value` (codex R4-P1 PR #96) silently strips
    confidence for NEGATIVE classifications because `value=0`, so a
    `confidence=0.1, negative` carried the same weight as
    `confidence=1.0, negative`. Shrinking toward neutral applies
    confidence symmetrically across positive (1.0), neutral (0.5),
    and negative (0.0): a low-confidence classification on either end
    collapses toward the neutral midpoint and contributes less to the
    paired delta. Mirrors the shrinkage behavior of the aggregate
    sentiment_score in `_compute_score` (Bayesian prior toward 0.5).
    """
    t_value = ScoringService._SENTIMENT_VALUE[treatment.sentiment.sentiment]
    c_value = ScoringService._SENTIMENT_VALUE[control.sentiment.sentiment]
    t_conf = treatment.sentiment.confidence
    c_conf = control.sentiment.confidence
    t_shrunk = t_conf * t_value + (1.0 - t_conf) * 0.5
    c_shrunk = c_conf * c_value + (1.0 - c_conf) * 0.5
    return t_shrunk - c_shrunk


def _match_paired_analyses(
    treatment_analyses: Sequence[AgentAnalysis],
    control_analyses: Sequence[AgentAnalysis],
) -> tuple[list[tuple[AgentAnalysis, AgentAnalysis]], int, int, int]:
    """Match treatment/control by (persona_id, sample_index).

    Returns:
      paired_pairs: (treatment, control) tuples where BOTH classifications
        succeeded (sentiment_failed=False on both sides).
      unpaired_treatment: count of treatment agents with no matching control.
      unpaired_control: count of control agents with no matching treatment.
      sentiment_failure_drops: matched pairs dropped because one or both
        agents had sentiment_failed=True. Surfacing this counter prevents
        phantom signal from neutral-fallback classifications leaking into
        the paired bootstrap.
    """
    treatment_by_key: dict[tuple[str, int], AgentAnalysis] = {
        (a.persona_id, a.sample_index): a for a in treatment_analyses
    }
    control_by_key: dict[tuple[str, int], AgentAnalysis] = {
        (a.persona_id, a.sample_index): a for a in control_analyses
    }
    treatment_keys = set(treatment_by_key)
    control_keys = set(control_by_key)
    matched_keys = treatment_keys & control_keys

    paired_pairs: list[tuple[AgentAnalysis, AgentAnalysis]] = []
    sentiment_failure_drops = 0
    # Sort matched keys for deterministic iteration (codex P2 PR #96):
    # `set` iteration order depends on Python hash seed, so the same
    # (data, run_seed) tuple could produce different CIs across processes
    # because the RNG resample indices would land on a shuffled `deltas`
    # list. Sorting pins the ordering.
    for key in sorted(matched_keys):
        t = treatment_by_key[key]
        c = control_by_key[key]
        if t.sentiment_failed or c.sentiment_failed:
            sentiment_failure_drops += 1
            continue
        paired_pairs.append((t, c))

    unpaired_treatment = len(treatment_keys - control_keys)
    unpaired_control = len(control_keys - treatment_keys)
    return paired_pairs, unpaired_treatment, unpaired_control, sentiment_failure_drops


def _mean_paired_delta(
    pairs: Sequence[tuple[AgentAnalysis, AgentAnalysis]],
    cfg: ScoringConfig,
) -> float:
    """Mean per-pair sentiment delta scaled into confidence_score units.

    Runs `_agent_delta` over each matched pair, takes the unweighted mean,
    scales by `sentiment_weight × 100` to land in the same [-100, +100]
    range as confidence_score. This is the locked Q2 statistic from
    `docs/4.6-ab-experiment-mode.md`: paired bootstrap on per-agent
    sentiment delta, NOT on per-arm score diff.

    Used for both the lift point estimate (on the full pair list) and
    the bootstrap CI (on each resample). Computing both off the SAME
    statistic guarantees `lift_ci` brackets `lift` by construction
    (codex R1-P1 PR #96). Excluding the weakness signal keeps weakness
    flags in per-arm `confidence_score` only — they describe the
    proposed change, not the paired comparison (codex R2-P2 PR #96).
    """
    if not pairs:
        return 0.0
    deltas = [_agent_delta(t, c) for t, c in pairs]
    mean_delta = sum(deltas) / len(deltas)
    return mean_delta * cfg.sentiment_weight * 100.0


def aggregate_ab(
    treatment_analyses: Sequence[AgentAnalysis],
    control_analyses: Sequence[AgentAnalysis],
    config: ScoringConfig | None = None,
    *,
    run_seed: int | None = None,
) -> tuple[SimulationResult, SimulationResult, ABLiftResult]:
    """Per-arm aggregate + paired bootstrap on lift.

    Reuses the existing single-arm `ScoringService.aggregate()` for each
    arm so the per-arm `confidence_score` / weakness surface stays
    identical to today's behavior. The lift layer matches treatment and
    control by `(persona_id, sample_index)`, then computes the lift
    point estimate AND the bootstrap CI off the SAME statistic — the
    locked Q2 paired sentiment delta from
    `docs/4.6-ab-experiment-mode.md`, scaled by `sentiment_weight × 100`
    into confidence_score units.

    Two codex review rounds shaped this. R1-P1: point and CI must come
    from the same statistic (else the CI can exclude the point at small
    N). R2-P2: that statistic must be paired sentiment delta only —
    pulling the weakness signal into lift contaminates the paired
    comparison since weakness flags describe the proposed change, not
    the user reaction. Both are now satisfied: lift = paired sentiment
    delta scaled to score units, CI = bootstrap of the same. Per-arm
    `treatment_score` / `control_score` continue to expose the full-arm
    confidence_score (sentiment + weakness, both with their gates) for
    the result table.

    Degenerate cases surface honestly via the drop counters and None
    fields — see `docs/4.6-ab-experiment-mode.md` § "Degenerate-case
    behaviour" for the full table.
    """
    cfg = config or ScoringConfig()

    treatment_result = ScoringService.aggregate(treatment_analyses, cfg, run_seed=run_seed)
    control_result = ScoringService.aggregate(control_analyses, cfg, run_seed=run_seed)

    lift_result = _paired_lift(treatment_analyses, control_analyses, cfg, run_seed=run_seed)

    return treatment_result, control_result, lift_result


def _paired_lift(
    treatment_analyses: Sequence[AgentAnalysis],
    control_analyses: Sequence[AgentAnalysis],
    cfg: ScoringConfig,
    *,
    run_seed: int | None = None,
) -> ABLiftResult:
    """Paired-bootstrap lift of `treatment` vs `control` analyses.

    The matched-pair core shared by the A/B aggregator (Phase 4.6 #90) and
    the persona-lift baseline (#221 §4.1). Matches the two analysis sets by
    `(persona_id, sample_index)`, then computes the lift point estimate AND
    the bootstrap CI off the SAME locked Q2 statistic — the per-pair
    confidence-weighted sentiment delta, scaled by `sentiment_weight × 100`
    into confidence_score units — so the CI brackets the point by
    construction. The sign is `treatment − control`: a positive lift means
    the treatment side is more positively received than the control side.

    Degenerate cases (no matched pairs) surface honestly: `lift`/`lift_ci`
    stay None and the drop counters explain what was excluded.
    """
    paired_pairs, unpaired_t, unpaired_c, sentiment_drops = _match_paired_analyses(
        treatment_analyses, control_analyses
    )
    paired_n = len(paired_pairs)

    lift_result = ABLiftResult(
        paired_n=paired_n,
        unpaired_treatment=unpaired_t,
        unpaired_control=unpaired_c,
        sentiment_failure_drops=sentiment_drops,
    )

    if paired_n == 0:
        # No usable pairs — lift is genuinely not computable.
        return lift_result

    # Point estimate + CI both bootstrap the SAME statistic on the
    # matched-pair subset (the locked Q2 paired sentiment delta), so the
    # CI brackets the point by construction.
    lift_point = _mean_paired_delta(paired_pairs, cfg)
    lift_result.lift = round(lift_point, cfg.confidence_rounding)

    if cfg.bootstrap_resamples > 0:
        effective_seed = (
            run_seed if run_seed is not None else secrets.randbits(53)
        ) ^ _BOOTSTRAP_SEED_MIX
        rng = random.Random(effective_seed)
        ci_low, ci_high = bootstrap_percentile_ci(
            paired_pairs,
            lambda resample: _mean_paired_delta(resample, cfg),
            n_resamples=cfg.bootstrap_resamples,
            rng=rng,
        )
        ci_low_r = round(ci_low, cfg.confidence_rounding)
        ci_high_r = round(ci_high, cfg.confidence_rounding)
        # Mirror aggregate()'s edge clamp: independent rounding (and discrete
        # percentile boundaries at small B/N) can violate
        # ci_low <= lift <= ci_high. Widen by at most one rounding step so
        # callers that inspect both fields always see a bracketing CI.
        lift_result.lift_ci = (
            min(ci_low_r, lift_result.lift),
            max(ci_high_r, lift_result.lift),
        )

    return lift_result


def aggregate_persona_lift(
    persona_analyses: Sequence[AgentAnalysis],
    no_persona_analyses: Sequence[AgentAnalysis],
    config: ScoringConfig | None = None,
    *,
    run_seed: int | None = None,
) -> tuple[SimulationResult, ABLiftResult]:
    """Persona-lift baseline (#221 §4.1): persona arm vs no-persona shadow.

    Returns the no-persona arm's standalone `SimulationResult` (so callers
    can surface its score next to the persona score) plus the paired-lift
    result. Lift sign is `persona − no_persona`: a positive lift means the
    persona-conditioned panel is more positively received than the same base
    LLM with no persona — i.e. persona conditioning ADDS optimism. A lift CI
    that straddles zero is the falsification signal: the personas aren't
    moving the needle beyond the base model (the "Funhouse Mirrors" guard).

    The persona arm's own `confidence_score` (the headline number) is
    computed elsewhere on the SAME persona analyses; this function does NOT
    recompute or touch it — it only adds the baseline + lift, keeping the
    headline byte-identical to a run with the flag off.
    """
    cfg = config or ScoringConfig()
    no_persona_result = ScoringService.aggregate(no_persona_analyses, cfg, run_seed=run_seed)
    # persona is the "treatment" side → lift sign is persona − no_persona.
    lift_result = _paired_lift(persona_analyses, no_persona_analyses, cfg, run_seed=run_seed)
    return no_persona_result, lift_result


def aggregate_current_state_delta(
    treatment_analyses: Sequence[AgentAnalysis],
    current_state_analyses: Sequence[AgentAnalysis],
    config: ScoringConfig | None = None,
    *,
    run_seed: int | None = None,
) -> tuple[SimulationResult, ABLiftResult]:
    """Delta-mode baseline (#221 §3.3.1): proposed change vs current-state shadow.

    The single-arm analog of the A/B aggregator: the SAME personas react to
    the proposed change (the headline single-arm panel) AND to the current
    product state (an ephemeral paired shadow, the existing A/B control framing
    applied 1:1). Returns the current-state arm's standalone `SimulationResult`
    (so callers can surface its score next to the headline) plus the paired
    delta. Delta sign is `treatment − current_state`: a positive delta means
    the proposed change is more positively received than leaving the product
    as-is. A delta CI that straddles zero is the falsification signal: the
    change isn't moving sentiment over the status quo.

    Because every persona is its own control (a 100%-paired design), this is
    strictly more powerful than the locked 50/50 A/B split. The headline panel's
    own `confidence_score` is computed elsewhere on the SAME treatment analyses;
    this function does NOT recompute or touch it — it only adds the baseline +
    delta, keeping the headline byte-identical to a run with the flag off.
    """
    cfg = config or ScoringConfig()
    current_state_result = ScoringService.aggregate(current_state_analyses, cfg, run_seed=run_seed)
    # treatment (proposed change) is the "treatment" side → delta is
    # treatment − current_state.
    delta_result = _paired_lift(treatment_analyses, current_state_analyses, cfg, run_seed=run_seed)
    return current_state_result, delta_result


# §5 honesty: conversion is a WEAK behavioral regime (the modality cliff —
# simulated purchase-intent correlates with real behavior at only r≈0.25–0.34,
# vs r≈0.7–0.9 for the copy/CTR regime). This label rides on the result so the
# downstream card never renders conversion lift with the confidence of a
# calibrated A/B test, and so the magnitude is treated as rank/direction signal
# (not a fabricated true effect size) until the #222 shrinkage layer is fit.
CONVERSION_REGIME_WEAK = "weak_behavioral"


def conversion_lift_honesty(lift_result: ConversionLiftResult) -> tuple[str, str | None]:
    """Map a `ConversionLiftResult` to (regime, relative-statement) per §5.

    `regime` is always the weak-behavioral label (conversion never escapes the
    modality cliff pre-#222). `relative` is a direction/rank statement — NOT the
    bare pp value presented as a true effect size — describing which arm
    converts more on the paired identities and whether the paired-bootstrap CI
    excludes zero. Returns `(regime, None)` when no lift is computable so the
    caller can leave the PM-facing line blank rather than assert a direction.
    """
    if lift_result.lift_pp is None:
        return CONVERSION_REGIME_WEAK, None

    if lift_result.lift_pp > 0:
        direction = "Treatment converts directionally higher than control"
    elif lift_result.lift_pp < 0:
        direction = "Treatment converts directionally lower than control"
    else:
        direction = "Treatment and control convert at the same directional rate"

    ci = lift_result.lift_ci_pp
    if ci is not None and (ci[0] > 0 or ci[1] < 0):
        separation = "the paired-bootstrap interval excludes zero"
    elif ci is not None:
        separation = "the paired-bootstrap interval straddles zero (not separable)"
    else:
        separation = "no interval available"

    relative = (
        f"{direction} on {lift_result.paired_n} paired identities; {separation}. "
        "Synthetic conversion is a weak behavioral signal — read as rank/direction, "
        "not as a calibrated effect size."
    )
    return CONVERSION_REGIME_WEAK, relative


def aggregate_conversion_lift(
    treatment_reactions: Sequence[AgentReaction],
    control_reactions: Sequence[AgentReaction],
    config: ScoringConfig | None = None,
    *,
    run_seed: int | None = None,
) -> ConversionLiftResult:
    """Paired conversion-lift (agent-behavior-spec §3a / #221).

    The conversion analog of `_paired_lift`, but the per-agent quantity is the
    elicited `conversion_p` scalar carried on each `AgentReaction` (turn-2
    allocation), not a sentiment classification. Matches treatment/control by
    `(persona_id, sample_index)` (the #90 paired key), then the statistic is the
    mean per-pair delta `p_conv(treatment) − p_conv(control)`, expressed in
    PERCENTAGE POINTS (×100). The sign is `treatment − control`: positive means
    the treatment arm converts more than the control arm on the same identities.

    Why a paired delta and never a level: the absolute `p_conv` is a synthetic,
    uncalibrated number (the §5 modality cliff — conversion is a weak behavioral
    regime), but the per-agent inflation is shared across both arms of a paired
    seed, so it cancels in the delta. The point estimate and the bootstrap CI are
    computed off the SAME statistic (mean paired delta in pp) so the CI brackets
    the point by construction — mirroring `_paired_lift` (codex R1-P1 PR #96).

    A matched pair is usable only when BOTH sides carry a `conversion_p`; a None
    on either side is a per-agent conversion-elicitation failure, counted in
    `elicitation_failure_drops` and never imputed to zero. Degenerate runs (no
    usable pairs) surface honestly: `lift_pp`/`lift_ci_pp` stay None and the drop
    counters explain what was excluded.
    """
    cfg = config or ScoringConfig()

    treatment_by_key: dict[tuple[str, int], AgentReaction] = {
        (r.persona_id, r.sample_index): r for r in treatment_reactions
    }
    control_by_key: dict[tuple[str, int], AgentReaction] = {
        (r.persona_id, r.sample_index): r for r in control_reactions
    }
    treatment_keys = set(treatment_by_key)
    control_keys = set(control_by_key)
    matched_keys = treatment_keys & control_keys

    result = ConversionLiftResult(
        unpaired_treatment=len(treatment_keys - control_keys),
        unpaired_control=len(control_keys - treatment_keys),
    )

    # Sort matched keys for deterministic resample ordering (same rationale as
    # `_match_paired_analyses`: `set` order is hash-seed dependent and would
    # otherwise perturb the bootstrap across processes).
    deltas: list[float] = []
    failure_drops = 0
    for key in sorted(matched_keys):
        t_p = treatment_by_key[key].conversion_p
        c_p = control_by_key[key].conversion_p
        if t_p is None or c_p is None:
            failure_drops += 1
            continue
        deltas.append(t_p - c_p)

    result.elicitation_failure_drops = failure_drops
    result.paired_n = len(deltas)

    if not deltas:
        # No usable pairs — conversion lift is genuinely not computable.
        return result

    def _mean_pp(sample: Sequence[float]) -> float:
        return (sum(sample) / len(sample)) * 100.0

    point = _mean_pp(deltas)
    result.lift_pp = round(point, cfg.confidence_rounding)

    if cfg.bootstrap_resamples > 0:
        effective_seed = (
            run_seed if run_seed is not None else secrets.randbits(53)
        ) ^ _BOOTSTRAP_SEED_MIX
        rng = random.Random(effective_seed)
        ci_low, ci_high = bootstrap_percentile_ci(
            deltas,
            _mean_pp,
            n_resamples=cfg.bootstrap_resamples,
            rng=rng,
        )
        ci_low_r = round(ci_low, cfg.confidence_rounding)
        ci_high_r = round(ci_high, cfg.confidence_rounding)
        # Mirror `_paired_lift`'s edge clamp: independent rounding (and discrete
        # percentile boundaries at small B/N) can violate
        # ci_low <= lift_pp <= ci_high. Widen by at most one rounding step so a
        # caller inspecting both always sees a bracketing CI.
        result.lift_ci_pp = (
            min(ci_low_r, result.lift_pp),
            max(ci_high_r, result.lift_pp),
        )

    return result
