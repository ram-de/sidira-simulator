"""Pre-flight ordinal input lint (epic #309, ticket #312 / T3).

A pre-flight quality lint over the hypothesis prose that ROUTES — it never
produces a number and never touches `confidence_score` (panel hard constraint,
`sessions/hypothesis-input-quality/analysis.md`). It composes with the T1/T2
deterministic gate (`services/answerability.py`): T1's two STRUCTURAL defects
hard-block (422); this lint is the **disclose** (amber) path — it NEVER 422s.
A paying user always gets a run plus a refinement offer.

The lint emits an ORDINAL state — `green | amber | red | abstain` — plus
`reasons[]` drawn ONLY from the existing weakness vocabulary
(`scoring._VALID_CATEGORIES`: `untestable_hypothesis`, `wrong_metric`,
`wrong_cohort`, `broken_mechanism`, `hidden_guardrail_risk`,
`underpowered_design`). One taxonomy, two timepoints — the same vocabulary the
post-hoc scorer uses, lifted forward to pre-flight. We do NOT invent a parallel
vocabulary and we do NOT emit a score.

Three signals compose into the verdict:

1. **LLM-judge (falsifiability / specificity).** One cheap judge call classifies
   the prose as green/amber/red with reasons from `_VALID_CATEGORIES`. Ordinal +
   named reasons — never a number. Stubbed in tests (no live LLM in the suite).

2. **Deterministic leading-framing lint.** Cheap lexical detection of
   demand-characteristic / leading prose ("we're excited to…", "new and
   improved", "would you like…", "we think you'll love") → amber + an
   auto-neutralize hint. Blinding already owns most of this (the blinded
   elicitor strips framing at elicitation time); this adds ONLY the overt-prose
   lint so the PM sees the leading framing pre-flight. Maps to
   `untestable_hypothesis` (demand-characteristic framing is the falsifiability
   axis — a leading question pre-answers itself).

3. **Paraphrase-abstain (reliability).** Reusing the K-paraphrase-instability
   pattern from `conversion_elicitor.py` (`elicit_ensemble`'s "reword the
   question only, flag if the answer flips" mechanic): the SAME prose is judged
   under K hand-authored paraphrases of the *judge question wording* (the
   system prompt and the prose are byte-identical across the K calls — only the
   instruction wording varies). If the verdict FLIPS across paraphrases the lint
   returns **ABSTAIN** ("indeterminate — please clarify") instead of a confident
   wrong label. A label that wobbles on reword must never ship (the product's
   own paraphrase-instability bar, analysis.md TL;DR §1).

   COST CONTROL: the K-paraphrase stability pass runs ONLY when the single-shot
   judge is non-green. Green is the overwhelmingly common case; spending K judge
   calls to confirm a clean hypothesis is clean would burn tokens on every run.
   A green single-shot is accepted as-is; only a flag (amber/red) earns the
   reliability re-check, and only a flag can be abstained.

## Routing (the caller's job; this service only classifies)

- `green`  → run silently (no `input_flags`, no refinement).
- `amber`  → run + stamp `input_flags` on the result card (degrade-and-disclose)
             + offer refinement. Never blocks.
- `red`    → run + stamp + refinement. Never 422 (semantic judgments are
             disclose-and-run; only T1's structural defects hard-block).
- `abstain`→ run + stamp "indeterminate — please clarify" + refinement.

The caller (`api/simulations.py`) runs this AFTER the T1/T2 gate (so a
needs_input 422 short-circuits before any token is spent) and threads the
verdict through the orchestrator into the runner, which stamps `input_flags`
onto `SimulationResult` and moves the refinement trigger earlier.
"""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Literal

import structlog
from pydantic import BaseModel, Field, field_validator

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.scoring import _VALID_CATEGORIES

log = structlog.get_logger()

# The ordinal lint state. `abstain` is the paraphrase-instability outcome — a
# label that flips on reword is withheld rather than shipped confidently.
InputLintState = Literal["green", "amber", "red", "abstain"]

# Reason code for the deterministic leading-framing lint. The human-readable text
# lives in `reasons`; this stable code lets the caller / UI branch (and lets the
# auto-neutralize hint be attached). It is NOT a new weakness *category* — the
# category it maps to is `untestable_hypothesis` (a leading question pre-answers
# itself, which is the falsifiability failure axis). Reusing the taxonomy, not
# forking it (panel hard constraint).
REASON_LEADING_FRAMING = "leading_framing"

# How many judge paraphrases the reliability pass runs. Index 0 is the canonical
# wording (so K=1 is byte-identical to the single-shot judge); the K-paraphrase
# stability pass only runs when the single-shot is non-green (see module
# docstring on cost control). Mirrors conversion_elicitor's
# CONVERSION_PARAPHRASE_COUNT = len(_QUESTION_PARAPHRASES).
JUDGE_PARAPHRASE_COUNT = 3


# ── Deterministic leading-framing lexicon ───────────────────────────────────
# Demand-characteristic / leading prose: phrasing that pre-answers the question
# or primes the agent toward a positive reaction. Each entry pairs a matched
# phrase with a concrete neutralize hint. Substring-matched on normalized
# (lowercased, single-spaced) prose so spacing variants collapse. Deliberately
# TIGHT — blinding already strips framing at elicitation time, so this only
# surfaces the OVERT prose-level cases the PM should see pre-flight; over-
# triggering here is friction on legitimate copy. Append-only-with-evidence.
_LEADING_FRAMING_PHRASES: tuple[tuple[str, str], ...] = (
    ("we're excited to", "State the change neutrally — drop the enthusiasm framing."),
    ("we are excited to", "State the change neutrally — drop the enthusiasm framing."),
    ("we think you'll love", "Remove the predicted reaction; let the agents react."),
    ("we think you will love", "Remove the predicted reaction; let the agents react."),
    ("you'll love", "Remove the predicted reaction; let the agents react."),
    ("you will love", "Remove the predicted reaction; let the agents react."),
    ("new and improved", "Describe what changed, not that it is 'improved'."),
    ("would you like", "Describe the change, not a yes/no prompt that primes assent."),
    ("don't you think", "Drop the rhetorical prompt that primes agreement."),
    ("dont you think", "Drop the rhetorical prompt that primes agreement."),
    ("wouldn't it be great", "Describe the change neutrally, not as a leading question."),
    ("wouldnt it be great", "Describe the change neutrally, not as a leading question."),
    ("everyone loves", "Drop the universal-appeal claim; let reception be measured."),
    ("game-changing", "Describe the mechanism, not a superlative."),
    ("game changing", "Describe the mechanism, not a superlative."),
    ("revolutionary new", "Describe what changed, not a marketing superlative."),
    ("best-in-class", "Describe the change, not a superlative."),
    ("best in class", "Describe the change, not a superlative."),
)


def _normalized(text: str) -> str:
    """Lowercased, single-spaced prose for substring phrase matching."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _detect_leading_framing(prose: str) -> tuple[list[str], list[str]]:
    """Deterministic, zero-LLM leading-framing lint.

    Returns `(reasons, fixes)` positionally aligned; both empty when the prose
    carries no overt demand-characteristic framing. De-duplicated on the fix
    text so two phrases that share a neutralize hint don't double-report. Pure —
    no LLM, no I/O.
    """
    blob = _normalized(prose)
    matched: list[str] = []
    fixes: list[str] = []
    seen_fixes: set[str] = set()
    for phrase, hint in _LEADING_FRAMING_PHRASES:
        if phrase in blob and hint not in seen_fixes:
            matched.append(phrase)
            fixes.append(hint)
            seen_fixes.add(hint)
    if not matched:
        return [], []
    reasons = [
        "The prose uses leading / demand-characteristic framing "
        f"({', '.join(repr(m) for m in matched)}). A leading question "
        "pre-answers itself, so the reaction measures the framing, not the "
        "change (untestable_hypothesis)."
    ]
    return reasons, fixes


# ── LLM judge ────────────────────────────────────────────────────────────────

_JUDGE_VALID_REASONS = sorted(_VALID_CATEGORIES)

_JUDGE_SYSTEM = """You are an experimentation expert running a PRE-FLIGHT check on a product
hypothesis BEFORE it is simulated. You judge ONLY whether the prose is well-posed
enough to yield a falsifiable, specific prediction — you do NOT predict whether
the change will succeed.

Return an ORDINAL verdict, never a number:
- "green": the prose names a specific change and yields a falsifiable prediction.
- "amber": the prose is workable but vague on one axis (metric, cohort, or
  mechanism under-specified).
- "red": the prose is too vague to produce a falsifiable prediction at all.

If the verdict is amber or red, list the weaknesses using ONLY these exact
category strings (any other string is invalid):

1. wrong_metric — the prose implies a metric that won't capture the behavioral change
2. wrong_cohort — the change targets users unlikely to respond meaningfully
3. broken_mechanism — the change doesn't address the actual behavioral driver
4. untestable_hypothesis — too vague to produce a falsifiable prediction
5. hidden_guardrail_risk — might lift the primary metric while damaging a downstream one
6. underpowered_design — segment too narrow, MDE too optimistic, duration too short

For a green verdict, return an empty `reasons` list.

Return STRICT JSON: {"verdict": "green|amber|red", "reasons": ["<cat1>", ...]}.
Use the exact category strings above; any other reason string is invalid."""


def _judge_user_turn_v1(prose: str) -> str:
    return (
        "Judge this pre-flight hypothesis prose for falsifiability and "
        "specificity. Prose:\n\n"
        f"{prose}"
    )


def _judge_user_turn_v2(prose: str) -> str:
    return (
        "Before this hypothesis is simulated, classify whether its prose is "
        "well-posed enough to yield a falsifiable, specific prediction. "
        "Hypothesis prose:\n\n"
        f"{prose}"
    )


def _judge_user_turn_v3(prose: str) -> str:
    return (
        "Read the following proposed product change and decide whether it is "
        "specific and falsifiable enough to test. The change:\n\n"
        f"{prose}"
    )


# Hand-authored judge paraphrases. Index 0 is the canonical wording (K=1 is
# byte-identical to the single-shot judge), mirroring conversion_elicitor's
# `_QUESTION_PARAPHRASES`: every entry keeps the SAME system prompt, the SAME
# prose, and the SAME JSON contract — only the instruction wording varies, so
# the ensemble isolates prompt-surface sensitivity, not content.
_JUDGE_PARAPHRASES = (
    _judge_user_turn_v1,
    _judge_user_turn_v2,
    _judge_user_turn_v3,
)
assert len(_JUDGE_PARAPHRASES) == JUDGE_PARAPHRASE_COUNT


class _JudgeOutput(BaseModel):
    """Strict JSON contract for one judge call. Ordinal + taxonomy reasons.

    `reasons` is filtered to `_VALID_CATEGORIES` (an LLM that emits a string
    outside the taxonomy is silently dropped, mirroring scoring.py's category
    filter) so a stray label can never leak a parallel vocabulary.
    """

    verdict: Literal["green", "amber", "red"]
    reasons: list[str] = Field(default_factory=list)

    @field_validator("reasons")
    @classmethod
    def _only_valid_categories(cls, v: list[str]) -> list[str]:
        # De-dupe while preserving order; drop anything outside the taxonomy.
        seen: set[str] = set()
        out: list[str] = []
        for r in v:
            if r in _VALID_CATEGORIES and r not in seen:
                out.append(r)
                seen.add(r)
        return out


@dataclass(frozen=True)
class InputLintVerdict:
    """The categorical pre-flight lint verdict.

    Carries no number and no persisted scalar — it ROUTES, it does not score
    (panel hard constraint). `state` is the ordinal verdict (or `abstain` on
    paraphrase instability). `reasons` are human-readable lines; `reason_codes`
    are the stable taxonomy category strings (from `_VALID_CATEGORIES`) plus the
    deterministic `leading_framing` code, so the caller / UI can branch and the
    refinement service can be fed the right weakness categories. `fixes` carries
    the auto-neutralize hints for leading framing (empty for the judge axes —
    refinement owns those rewrites). `paraphrase_unstable` records whether the
    abstain was triggered by a judge flip across paraphrases.
    """

    state: InputLintState
    reasons: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    paraphrase_unstable: bool = False

    @property
    def is_flagged(self) -> bool:
        """True when the lint is non-green (amber / red / abstain) — i.e. the
        caller should stamp `input_flags` and offer refinement."""
        return self.state != "green"


class InputLintJudge:
    """One cheap LLM-judge call classifying hypothesis prose as green/amber/red.

    Mirrors RefinementService's lazy-chat construction so it's unit-testable with
    a stubbed `chat_client` (no live LLM in the suite). `judge_once` is the
    single-shot path (canonical paraphrase, index 0); `judge_paraphrase` runs an
    arbitrary paraphrase index for the K-stability pass.
    """

    def __init__(self, chat_client: ChatClient | None = None) -> None:
        self._chat_explicit = chat_client

    @property
    def _chat(self) -> ChatClient:
        if self._chat_explicit is None:
            self._chat_explicit = get_chat_client()
        return self._chat_explicit

    def judge_paraphrase(self, prose: str, paraphrase_index: int) -> _JudgeOutput:
        """Run one judge call under the given paraphrase index (sync — the
        ChatClient is sync; the async wrapper is in `assess_input_lint`)."""
        build = _JUDGE_PARAPHRASES[paraphrase_index]
        return self._chat.chat_json(
            [
                {"role": "system", "content": _JUDGE_SYSTEM},
                {"role": "user", "content": build(prose)},
            ],
            _JudgeOutput,
        )

    def judge_once(self, prose: str) -> _JudgeOutput:
        """Single-shot judge on the canonical wording (paraphrase index 0)."""
        return self.judge_paraphrase(prose, 0)


async def _to_thread(func, *args, **kwargs):
    """Async wrapper since chat_json is sync (mirrors refinement._to_thread)."""
    return await asyncio.to_thread(func, *args, **kwargs)


def _judge_reasons_to_text(categories: list[str]) -> list[str]:
    """Render the taxonomy category codes the judge returned into the
    human-readable note lines the UI / refinement payload carry."""
    blurbs = {
        "wrong_metric": "The implied metric may not capture the behavioral change the change would cause.",
        "wrong_cohort": "The change targets users unlikely to respond meaningfully.",
        "broken_mechanism": "The change may not address the actual behavioral driver.",
        "untestable_hypothesis": "The prose is too vague to produce a falsifiable prediction.",
        "hidden_guardrail_risk": "The change may lift the primary metric while damaging a downstream one.",
        "underpowered_design": "The design looks underpowered (segment too narrow / MDE too optimistic / duration too short).",
    }
    return [blurbs[c] for c in categories if c in blurbs]


_ABSTAIN_REASON = (
    "Indeterminate — please clarify. The pre-flight verdict was not stable "
    "across reworded judge prompts, so a confident label is withheld. Sharpen "
    "the prose (name the metric, cohort, and mechanism) and re-run."
)


async def assess_input_lint(
    hypothesis: Hypothesis,
    *,
    chat_client: ChatClient | None = None,
    paraphrases: int = JUDGE_PARAPHRASE_COUNT,
) -> InputLintVerdict:
    """Pre-flight ordinal lint over the hypothesis prose (T3 / #312).

    Composes the deterministic leading-framing lint with the LLM judge and the
    paraphrase-abstain reliability pass. Routes, never scores. Returns
    `green` (run silently) / `amber` / `red` / `abstain`.

    Cost control: the single-shot judge always runs (one cheap call); the
    K-paraphrase stability pass runs ONLY when the single-shot is non-green
    (green is the common case and a confirmed-clean hypothesis does not earn K
    extra calls). `paraphrases` is clamped to [1, JUDGE_PARAPHRASE_COUNT]; at
    K=1 the stability pass is a no-op (one paraphrase cannot flip).

    Failure posture mirrors refinement.suggest: a judge transport/JSON failure
    degrades to the deterministic-only verdict (the leading-framing lint still
    fires) rather than blocking the run — a semantic judgment never hard-fails a
    paying user.
    """
    # 1) Deterministic leading-framing lint (always runs, zero-LLM). Maps to
    #    untestable_hypothesis.
    framing_reasons, framing_fixes = _detect_leading_framing(hypothesis.prose)
    framing_codes = [REASON_LEADING_FRAMING] if framing_reasons else []

    judge = InputLintJudge(chat_client=chat_client)

    # 2) Single-shot judge (one cheap call). Degrade to deterministic-only on
    #    LLM failure — never block the run.
    try:
        single = await _to_thread(judge.judge_once, hypothesis.prose)
    except Exception as exc:  # noqa: BLE001 — degrade gracefully; never hard-block
        log.warning(
            "input_lint.judge_failed",
            error=str(exc),
            exc_type=type(exc).__name__,
        )
        # Judge unavailable: fall back to the deterministic framing lint alone.
        if framing_reasons:
            return InputLintVerdict(
                state="amber",
                reasons=framing_reasons,
                reason_codes=framing_codes,
                fixes=framing_fixes,
            )
        return InputLintVerdict(state="green")

    judge_state: InputLintState = single.verdict
    judge_codes = list(single.reasons)

    # 3) Paraphrase-abstain reliability pass — ONLY when the single-shot is
    #    non-green (cost control). If the verdict flips across the K paraphrases,
    #    ABSTAIN: a label that wobbles on reword must not ship.
    k = max(1, min(paraphrases, JUDGE_PARAPHRASE_COUNT))
    paraphrase_unstable = False
    if judge_state != "green" and k >= 2:
        verdicts = [single.verdict]
        for i in range(1, k):
            try:
                verdicts.append((await _to_thread(judge.judge_paraphrase, hypothesis.prose, i)).verdict)
            except Exception as exc:  # noqa: BLE001 — drop a degenerate paraphrase, keep the rest
                log.warning(
                    "input_lint.paraphrase_failed",
                    paraphrase_index=i,
                    error=str(exc),
                    exc_type=type(exc).__name__,
                )
                continue
        # A flip = the set of distinct verdicts across the survivors is >1. Needs
        # at least two survivors to be meaningful (mirrors elicit_ensemble's
        # `len(...) >= 2` instability guard).
        if len(verdicts) >= 2 and len(set(verdicts)) > 1:
            paraphrase_unstable = True

    if paraphrase_unstable:
        # Abstain dominates a confident wrong label. Carry the framing reasons
        # too (deterministic, reliable) so the PM still sees the concrete lint,
        # plus the indeterminate note.
        return InputLintVerdict(
            state="abstain",
            reasons=[_ABSTAIN_REASON, *framing_reasons],
            reason_codes=[*judge_codes, *framing_codes],
            fixes=framing_fixes,
            paraphrase_unstable=True,
        )

    # 4) Combine the stable judge verdict with the deterministic framing lint.
    #    Leading framing forces at least amber even on a green judge (the prose
    #    is leading regardless of the judge's specificity read).
    state = judge_state
    if framing_reasons and state == "green":
        state = "amber"

    if state == "green":
        return InputLintVerdict(state="green")

    reasons = [*_judge_reasons_to_text(judge_codes), *framing_reasons]
    reason_codes = [*judge_codes, *framing_codes]
    return InputLintVerdict(
        state=state,
        reasons=reasons,
        reason_codes=reason_codes,
        fixes=framing_fixes,
    )


__all__ = [
    "InputLintState",
    "InputLintVerdict",
    "InputLintJudge",
    "REASON_LEADING_FRAMING",
    "JUDGE_PARAPHRASE_COUNT",
    "assess_input_lint",
    "_detect_leading_framing",
]
