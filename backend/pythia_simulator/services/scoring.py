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
from collections import Counter
from typing import Iterable

from pythia_simulator.adapters.llm import ChatClient, JSONRepairError, get_chat_client
from pythia_simulator.schemas.scoring import (
    AgentAnalysis,
    ScoringConfig,
    Sentiment,
    SentimentClassification,
    WeaknessClassification,
)
from pythia_simulator.schemas.simulation import Hypothesis, SimulationResult, Weakness

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

        if isinstance(weakness, BaseException):
            log.warning("weakness classification failed: %s", weakness)
            weakness = WeaknessClassification(categories=[], primary_reason="(classification failed)")
        if isinstance(sentiment, BaseException):
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
        )

    # — Pack-level scoring ——————————————————————————————————————————

    async def score(
        self,
        hypothesis: Hypothesis,
        reactions: list[AgentReaction],
    ) -> tuple[SimulationResult, list[AgentAnalysis]]:
        """Fan out per-agent analysis, then aggregate."""
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
        result = self.aggregate(analyses)
        return result, analyses

    # — Aggregation (pure function, no LLM) ————————————————————————————

    _SENTIMENT_VALUE: dict[Sentiment, float] = {
        Sentiment.POSITIVE: 1.0,
        Sentiment.NEUTRAL: 0.5,
        Sentiment.NEGATIVE: 0.0,
    }

    @classmethod
    def aggregate(
        cls,
        analyses: Iterable[AgentAnalysis],
        config: ScoringConfig | None = None,
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

        # ── Sentiment: confidence-weighted mean with shrinkage toward 0.5 ──
        if cfg.use_sentiment_confidence:
            num = sum(
                a.sentiment.confidence * cls._SENTIMENT_VALUE[a.sentiment.sentiment]
                for a in analyses_list
            )
            denom = sum(a.sentiment.confidence for a in analyses_list)
        else:
            num = sum(cls._SENTIMENT_VALUE[a.sentiment.sentiment] for a in analyses_list)
            denom = float(n)
        # Bayesian shrinkage: add prior_k pseudo-observations of neutral (0.5).
        num += cfg.sentiment_prior_k * 0.5
        denom += cfg.sentiment_prior_k
        sentiment_score = num / denom if denom > 0 else 0.5

        # ── Weakness: dedupe categories per agent, then count any-flag share ──
        category_agents: dict[str, list[str]] = {}
        agents_with_any_weakness = 0
        for a in analyses_list:
            unique_cats = set(a.weakness.categories)  # dedupe within agent
            if unique_cats:
                agents_with_any_weakness += 1
            for cat in unique_cats:
                category_agents.setdefault(cat, []).append(a.agent_id)

        any_flag_share = agents_with_any_weakness / n
        weakness_signal = 1.0 - any_flag_share

        confidence = (
            cfg.sentiment_weight * sentiment_score
            + cfg.weakness_weight * weakness_signal
        ) * 100.0

        # ── Weakness surface: top-K by frequency ──
        category_counts = Counter({c: len(ids) for c, ids in category_agents.items()})
        top_weaknesses = [
            Weakness(
                category=cat,
                summary=_summarize_category(cat, len(category_agents[cat]), n),
                supporting_agent_ids=category_agents[cat][:5],
            )
            for cat, _ in category_counts.most_common(cfg.top_k_weaknesses)
        ]

        # ── Underpowered gate ──
        weaknesses = list(top_weaknesses)
        if n < cfg.min_sample_size:
            weaknesses.insert(
                0,
                Weakness(
                    category="underpowered_design",
                    summary=(
                        f"Only {n} agent{'s' if n != 1 else ''} reacted "
                        f"(min recommended: {cfg.min_sample_size}). Treat the score as provisional."
                    ),
                ),
            )

        return SimulationResult(
            confidence_score=round(confidence, cfg.confidence_rounding),
            weaknesses=weaknesses,
            refinement_suggestions=[],  # filled in by RefinementService caller
        )


def _summarize_category(category: str, count: int, total: int) -> str:
    return f"{count}/{total} agents flagged this — {category.replace('_', ' ')}."
