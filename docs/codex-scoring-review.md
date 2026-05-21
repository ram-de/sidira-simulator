# Codex Review — Scoring Formula (Wave 4)

**Date:** 2026-05-21
**Branch:** `wave-4-scoring`
**Reviewer:** OpenAI Codex CLI 0.133.0 (model: codex default, reasoning=high)
**Prompt scope:** `backend/pythia_simulator/services/scoring.py` `ScoringService.aggregate()` and the schemas it consumes from `backend/pythia_simulator/schemas/scoring.py`.

This is the cross-model second opinion planned in `/plan-eng-review` (Wave 0). It was preceded by a self-review; the two reviews converged on 4 of 5 findings independently, with Codex catching one additional bug.

## Findings (Codex output verbatim)

- **[P2]** `services/scoring.py:240` — `max_category_share` is the wrong primary penalty because diffuse failure across categories scores as low-risk; use fraction-of-agents-flagging-any-weakness as the main weakness penalty and keep entropy/Gini only as diagnostic concentration metadata.
- **[P2]** `services/scoring.py:231` — `sentiment.confidence` is ignored; use confidence-weighted sentiment with shrinkage toward neutral, e.g. `(sum(conf * value) + prior_k * 0.5) / (sum(conf) + prior_k)`, so low-confidence and tiny-N runs do not swing the score.
- **[P2]** `services/scoring.py:223` — `N=1` and `N=2` produce precise-looking scores from noise; below a configurable `min_sample_size`, return/surface `underpowered_design` and mark the score as provisional or withheld.
- **[P2]** `services/scoring.py:236` — duplicate categories in one agent's `weakness.categories` are counted multiple times, so one malformed classification can inflate concentration above the true agent share.
- **[P3]** `services/scoring.py:244` — `0.6/0.4` is defensible as a starting prior, but `sentiment_weight`, weakness weight, prevalence/concentration choice, `min_sample_size`, shrinkage prior, top-K weaknesses, and rounding should be `ScoringConfig` parameters before Layer-3 calibration.

Tokens used: 21,122.

## Disposition

All 5 findings applied in the same wave-4-scoring branch.

| # | Finding | Action |
|---|---|---|
| 1 | max_category_share wrong primary penalty | Switched to `1 − any_flag_share` (deduped per agent). Concentration removed from the score formula entirely. |
| 2 | Sentiment confidence ignored | Confidence-weighted mean with Bayesian shrinkage toward neutral (prior_k=1.0 pseudo-observations). |
| 3 | N=1/N=2 noise | `min_sample_size=3` default. Below threshold, `underpowered_design` is prepended to the weakness list with "provisional" copy. |
| 4 | Duplicate categories double-count | `set(a.weakness.categories)` dedupe inside the per-agent loop. |
| 5 | Tunable parameters | `ScoringConfig` Pydantic model — exposes sentiment_weight, weakness_weight, prior_k, use_sentiment_confidence, min_sample_size, top_k_weaknesses, confidence_rounding. |

## Convergence with self-review

| Finding | Codex | Claude self-review | Net |
|---|---|---|---|
| max_category_share alternative | ✅ flagged | ✅ flagged | Independent agreement |
| Sentiment confidence ignored | ✅ flagged (with shrinkage formula) | ✅ flagged (simple weighted avg) | Codex's formula adopted (technically stronger) |
| min_sample_size gate | ✅ flagged | ✅ flagged | Independent agreement |
| Duplicate categories | ✅ flagged | ❌ missed | **Codex caught a bug** the self-review missed |
| ScoringConfig | ✅ flagged | ✅ flagged | Independent agreement |

**Net value of cross-model review:** 1 P2 bug that would have shipped without it (`duplicate categories double-count`). Worth the ~5 minutes.

## Implementation summary

- `schemas/scoring.py`: new `ScoringConfig` Pydantic model.
- `services/scoring.py`: `aggregate()` is now a `@classmethod` taking an optional `config: ScoringConfig | None = None`. Defaults preserve the locked priors from Wave 0; the formula is rewritten per findings 1–4.
- `tests/test_scoring.py`: tests updated to assert the new formula. New tests for diffuse-weaknesses, duplicate-category dedupe, confidence dampening, and the min_sample_size gate.
- `tests/test_simulations_api.py`: e2e expectation updated from 60.0 → ~51.2 with documented math.

## Future calibration hooks

`ScoringConfig` is what Phase 9 (Layer-3 calibration) will tune from real outcome data. The starting priors live in the code, but they're now parameters — not magic numbers.
