"""Scoring service — turns N agent reactions into a SimulationResult.

Per-agent: weakness classification + sentiment classification (two `chat_json`
calls in parallel). Aggregation: `0.6 × sentiment_score + 0.4 × (1 − weakness_concentration)`
on a 0–100 scale. This is the locked formula from /plan-eng-review.

The scorer is independent of SimulationRunner so its formula is unit-testable
without driving an end-to-end simulation.
"""

from __future__ import annotations

import asyncio
import logging
import random
import secrets
from collections import Counter
from typing import Iterable, Sequence

from pythia_simulator.adapters.llm import ChatClient, JSONRepairError, get_chat_client
from pythia_simulator.schemas.scoring import (
    AgentAnalysis,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from pythia_simulator.schemas.simulation import Hypothesis, SimulationResult, Weakness
from pythia_simulator.services.statistics import bootstrap_percentile_ci, wilson_interval

# Arbitrary integer XOR mask used to derive a bootstrap-specific RNG seed
# from the runner's run_seed, so the bootstrap resample stream cannot
# collide with the identity-seed stream (which uses sha256 over a different
# namespace tuple — distinct domain anyway, so this is defense in depth).
_BOOTSTRAP_SEED_MIX = 0xB007_5747_5474

log = logging.getLogger(__name__)


# ─── Per-agent reaction record passed to the scorer ─────────────────────


class AgentReaction:
    """Lightweight DTO so scoring doesn't import SimulationRunner internals."""

    __slots__ = ("agent_id", "persona_id", "persona_name", "reaction_text")

    def __init__(
        self,
        *,
        agent_id: str,
        persona_id: str,
        persona_name: str,
        reaction_text: str,
    ) -> None:
        self.agent_id = agent_id
        self.persona_id = persona_id
        self.persona_name = persona_name
        self.reaction_text = reaction_text


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

    async def analyze(
        self, hypothesis: Hypothesis, reaction: AgentReaction
    ) -> AgentAnalysis:
        """Run weakness + sentiment classification in parallel for one agent."""
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
        sentiment_task = asyncio.to_thread(
            self._chat.chat_json,
            [
                {"role": "system", "content": _SENTIMENT_SYSTEM},
                {
                    "role": "user",
                    "content": _build_sentiment_user_prompt(hypothesis, reaction.reaction_text),
                },
            ],
            SentimentClassification,
        )
        weakness, sentiment = await asyncio.gather(
            weakness_task, sentiment_task, return_exceptions=True
        )

        weakness_failed = isinstance(weakness, BaseException)
        sentiment_failed = isinstance(sentiment, BaseException)
        if weakness_failed:
            log.warning("weakness classification failed: %s", weakness)
            weakness = WeaknessClassification(categories=[], primary_reason="(classification failed)")
        if sentiment_failed:
            log.warning("sentiment classification failed: %s", sentiment)
            sentiment = SentimentClassification(
                sentiment=Sentiment.NEUTRAL, confidence=0.0, one_line_summary="(classification failed)"
            )

        # Drop any categories the LLM hallucinated outside the closed set.
        weakness.categories = [c for c in weakness.categories if c in _VALID_CATEGORIES]

        return AgentAnalysis(
            agent_id=reaction.agent_id,
            persona_id=reaction.persona_id,
            persona_name=reaction.persona_name,
            weakness=weakness,
            sentiment=sentiment,
            weakness_failed=weakness_failed,
            sentiment_failed=sentiment_failed,
        )

    # — Pack-level scoring ——————————————————————————————————————————

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

        analyses = await asyncio.gather(
            *(self.analyze(hypothesis, r) for r in reactions),
            return_exceptions=False,
        )
        result = self.aggregate(analyses, config, run_seed=run_seed)
        return result, analyses

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
        agents_with_any_weakness = sum(
            1 for a in analyses if set(a.weakness.categories)
        )
        any_flag_share = agents_with_any_weakness / n
        weakness_signal = 1.0 - any_flag_share

        confidence = (
            cfg.sentiment_weight * sentiment_score
            + cfg.weakness_weight * weakness_signal
        ) * 100.0
        return confidence, sentiment_score, weakness_signal

    @classmethod
    def aggregate(
        cls,
        analyses: Iterable[AgentAnalysis],
        config: ScoringConfig | None = None,
        *,
        run_seed: int | None = None,
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

        confidence, _sentiment, _weakness_signal = cls._compute_score(
            analyses_list, cfg
        )

        # ── Phase 2.5 #8 degradation guard ──
        # Count weakness + sentiment classification failures independently
        # (total = 2N). If the failure rate exceeds the configured threshold,
        # apply a multiplicative discount to the score (and CI) and prepend an
        # underpowered_design weakness so the PM sees the degraded state.
        # Without this, a totally-failed run silently returns ~70 (neutral
        # sentiment with shrinkage, zero weakness flags) — misleadingly fine.
        failed_classifications = sum(
            int(a.weakness_failed) + int(a.sentiment_failed) for a in analyses_list
        )
        total_classifications = 2 * n
        failure_rate = (
            failed_classifications / total_classifications
            if total_classifications > 0
            else 0.0
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
