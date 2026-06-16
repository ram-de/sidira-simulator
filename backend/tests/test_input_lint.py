"""Unit tests for the T3 (#312) pre-flight ordinal input lint.

The judge is ALWAYS stubbed here — no path in this module may reach a live
ChatClient (panel/ticket hard constraint). The stub is a synchronous chat-client
shim that returns a canned `_JudgeOutput` per judge call; some stubs vary their
verdict by paraphrase index to exercise the abstain-on-flip reliability pass.

Covers:
- green prose -> green verdict, NO flags, and the K-paraphrase pass does NOT run
  (cost control: a confirmed-clean hypothesis must not burn K extra calls).
- judge amber / red -> that state with reasons drawn from `_VALID_CATEGORIES`.
- leading-framing prose -> at least amber + `leading_framing` reason_code + a fix,
  even when the judge says green.
- paraphrase FLIP across the K judge prompts -> `abstain` + paraphrase_unstable.
- judge raises -> degrades to deterministic framing-only (amber if framing, else
  green) — a semantic judgment never hard-fails.
- every judge-emitted reason_code is a member of `_VALID_CATEGORIES`.
"""

from __future__ import annotations

import asyncio

import pytest

from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.input_lint import (
    JUDGE_PARAPHRASE_COUNT,
    REASON_LEADING_FRAMING,
    InputLintVerdict,
    _detect_leading_framing,
    assess_input_lint,
)
from sidira_simulator.services.scoring import _VALID_CATEGORIES


def _hyp(prose: str) -> Hypothesis:
    return Hypothesis(capability_name="reorder", prose=prose)


class _StubJudgeChat:
    """A stubbed ChatClient for the input-lint judge.

    Returns one canned verdict per `chat_json` call. `verdict_by_call` is an
    ordered list consumed call-by-call (so a flip across paraphrases can be
    simulated); if it is exhausted, the last entry repeats. `reasons` is the
    fixed reason list for every call. Records `call_count` so cost-control
    assertions can verify the K-paraphrase pass did/did not fire.
    """

    def __init__(
        self,
        *,
        verdict: str = "green",
        verdict_by_call: list[str] | None = None,
        reasons: list[str] | None = None,
        raise_exc: Exception | None = None,
    ) -> None:
        self._verdict_by_call = verdict_by_call or [verdict]
        self._reasons = reasons or []
        self._raise = raise_exc
        self.call_count = 0

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):  # pragma: no cover
        raise NotImplementedError("input-lint judge uses chat_json only")

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        if self._raise is not None:
            raise self._raise
        idx = min(self.call_count, len(self._verdict_by_call) - 1)
        verdict = self._verdict_by_call[idx]
        self.call_count += 1
        # `schema` is _JudgeOutput; build it so the field_validator runs (it
        # filters reasons to _VALID_CATEGORIES exactly as in prod).
        return schema(verdict=verdict, reasons=list(self._reasons))


class _RecordingChat(_StubJudgeChat):
    """A stub that records the user-turn content of every judge call, so a test
    can assert the coherence pass actually showed the declared metric to the
    judge (the T7 #338 metric/change-mismatch input)."""

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.user_turns: list[str] = []

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.user_turns.append(messages[-1]["content"])
        return super().chat_json(messages, schema, max_tokens, temperature, seed)


def _run(coro):
    return asyncio.run(coro)


# ── green path + cost control ────────────────────────────────────────────────


def test_green_prose_returns_green_with_no_flags() -> None:
    chat = _StubJudgeChat(verdict="green")
    v = _run(assess_input_lint(_hyp("Add a one-tap reorder button to the home tab."), chat_client=chat))
    assert v.state == "green"
    assert v.reasons == []
    assert v.reason_codes == []
    assert v.fixes == []
    assert v.paraphrase_unstable is False
    assert v.is_flagged is False


def test_green_single_shot_does_not_trigger_paraphrase_pass() -> None:
    """Cost control: a green single-shot is accepted as-is — the K-paraphrase
    stability pass must NOT run (it would burn K-1 extra judge calls on every
    clean hypothesis, the common case)."""
    chat = _StubJudgeChat(verdict="green")
    _run(assess_input_lint(_hyp("Add a one-tap reorder button to the home tab."), chat_client=chat))
    assert chat.call_count == 1, "green should run exactly one judge call"


# ── judge amber / red ────────────────────────────────────────────────────────


def test_judge_amber_yields_amber_with_taxonomy_reasons() -> None:
    chat = _StubJudgeChat(verdict="amber", reasons=["wrong_cohort"])
    v = _run(assess_input_lint(_hyp("Make the thing better for some users."), chat_client=chat))
    assert v.state == "amber"
    assert "wrong_cohort" in v.reason_codes
    assert v.reasons  # human-readable line(s)
    assert v.is_flagged is True


def test_judge_red_yields_red() -> None:
    # All K paraphrases agree on red -> stable red, no abstain.
    chat = _StubJudgeChat(verdict="red", reasons=["untestable_hypothesis"])
    v = _run(assess_input_lint(_hyp("Improve engagement somehow."), chat_client=chat))
    assert v.state == "red"
    assert "untestable_hypothesis" in v.reason_codes


# ── deterministic leading-framing lint ───────────────────────────────────────


def test_leading_framing_forces_amber_even_on_green_judge() -> None:
    chat = _StubJudgeChat(verdict="green")
    v = _run(
        assess_input_lint(
            _hyp("We're excited to add a one-tap reorder button users will love."),
            chat_client=chat,
        )
    )
    assert v.state == "amber"
    assert REASON_LEADING_FRAMING in v.reason_codes
    assert v.fixes, "leading framing must carry an auto-neutralize hint"
    assert any("leading" in r.lower() for r in v.reasons)


def test_detect_leading_framing_is_pure_and_aligned() -> None:
    reasons, fixes = _detect_leading_framing("This is a new and improved checkout flow.")
    assert reasons and fixes
    # No framing -> both empty.
    assert _detect_leading_framing("Add a reorder button to the home tab.") == ([], [])


# ── paraphrase-abstain reliability pass ──────────────────────────────────────


def test_paraphrase_flip_abstains() -> None:
    """When the judge verdict FLIPS across the K paraphrases (single-shot is
    non-green so the stability pass runs), the lint ABSTAINS rather than ship a
    wobbly label."""
    # Call 0 = amber (single-shot, non-green -> triggers the pass), call 1 = red,
    # call 2 = amber. Distinct verdicts across survivors -> flip -> abstain.
    chat = _StubJudgeChat(
        verdict_by_call=["amber", "red", "amber"],
        reasons=["wrong_metric"],
    )
    v = _run(assess_input_lint(_hyp("Maybe tweak the funnel a bit."), chat_client=chat))
    assert v.state == "abstain"
    assert v.paraphrase_unstable is True
    assert any("indeterminate" in r.lower() for r in v.reasons)
    # The pass ran all K paraphrases.
    assert chat.call_count == JUDGE_PARAPHRASE_COUNT


def test_stable_non_green_does_not_abstain() -> None:
    """A non-green verdict that is STABLE across all K paraphrases keeps its
    state (no abstain) — abstain is reserved for genuine instability."""
    chat = _StubJudgeChat(verdict="amber", reasons=["wrong_cohort"])
    v = _run(assess_input_lint(_hyp("Make the thing better for some users."), chat_client=chat))
    assert v.state == "amber"
    assert v.paraphrase_unstable is False
    assert chat.call_count == JUDGE_PARAPHRASE_COUNT  # the stability pass ran


# ── judge failure degrades, never hard-fails ─────────────────────────────────


def test_judge_failure_degrades_to_framing_only_amber() -> None:
    chat = _StubJudgeChat(raise_exc=RuntimeError("transport down"))
    v = _run(
        assess_input_lint(
            _hyp("We're excited to launch this new and improved reorder flow!"),
            chat_client=chat,
        )
    )
    # Deterministic framing lint still fires -> amber.
    assert v.state == "amber"
    assert REASON_LEADING_FRAMING in v.reason_codes
    assert v.fixes


def test_judge_failure_with_clean_prose_degrades_to_green() -> None:
    chat = _StubJudgeChat(raise_exc=RuntimeError("transport down"))
    v = _run(assess_input_lint(_hyp("Add a reorder button to the home tab."), chat_client=chat))
    assert v.state == "green"
    assert v.is_flagged is False


# ── taxonomy compliance (no parallel vocabulary) ─────────────────────────────


@pytest.mark.parametrize("verdict", ["amber", "red"])
def test_judge_reason_codes_are_all_valid_categories(verdict: str) -> None:
    """Every taxonomy reason the judge emits must be a member of
    `_VALID_CATEGORIES` — the lint reuses the weakness taxonomy, never a parallel
    vocabulary. A stray label is silently dropped by the field validator."""
    # Stub emits a mix of valid + invalid labels; only the valid ones survive.
    chat = _StubJudgeChat(
        verdict=verdict,
        reasons=["wrong_metric", "totally_made_up_label", "broken_mechanism"],
    )
    v = _run(assess_input_lint(_hyp("Tweak the metric somehow."), chat_client=chat))
    judge_codes = [c for c in v.reason_codes if c != REASON_LEADING_FRAMING]
    assert judge_codes, "expected at least one surviving taxonomy code"
    for code in judge_codes:
        assert code in _VALID_CATEGORIES, f"{code!r} leaked outside the taxonomy"
    assert "totally_made_up_label" not in v.reason_codes


def test_k1_paraphrases_disables_stability_pass() -> None:
    """With paraphrases=1 the stability pass is a no-op (one paraphrase cannot
    flip): a non-green single-shot keeps its state with exactly one judge call."""
    chat = _StubJudgeChat(verdict="amber", reasons=["wrong_cohort"])
    v = _run(
        assess_input_lint(
            _hyp("Make the thing better for some users."),
            chat_client=chat,
            paraphrases=1,
        )
    )
    assert v.state == "amber"
    assert v.paraphrase_unstable is False
    assert chat.call_count == 1


def test_verdict_dataclass_is_flagged_property() -> None:
    assert InputLintVerdict(state="green").is_flagged is False
    assert InputLintVerdict(state="amber").is_flagged is True
    assert InputLintVerdict(state="red").is_flagged is True
    assert InputLintVerdict(state="abstain").is_flagged is True


# ── T7 (#338) coherence pass: weak-but-present fields ─────────────────────────
#
# The judge stub is what classifies in the suite (no live LLM), so these tests
# pin the CONTRACT the coherence rubric routes through: a weak-but-present field
# maps onto an EXISTING taxonomy category and surfaces via the SAME amber
# `input_flags` path — green/amber/red stay categorical, no new vocabulary, no
# second LLM call. The rubric wording itself (what makes the LLM emit the code)
# is exercised against the live judge, not unit-tested here.


def test_coherence_all_users_cohort_maps_to_wrong_cohort_amber() -> None:
    """cohort = "all users" is everyone, not a cohort -> wrong_cohort, amber,
    surfaced through the existing categorical input_flags path."""
    chat = _StubJudgeChat(verdict="amber", reasons=["wrong_cohort"])
    v = _run(
        assess_input_lint(
            _hyp("Add a one-tap reorder button for all users."),
            chat_client=chat,
        )
    )
    assert v.state == "amber"
    assert "wrong_cohort" in v.reason_codes
    assert v.is_flagged is True
    # No parallel vocabulary: every judge code is an existing taxonomy member.
    for code in (c for c in v.reason_codes if c != REASON_LEADING_FRAMING):
        assert code in _VALID_CATEGORIES


def test_coherence_metric_mismatch_maps_to_wrong_metric_amber() -> None:
    """A CTR metric declared for a retention-shaped change -> wrong_metric,
    amber. The declared metric must be visible to the judge for it to catch the
    mismatch (T7 folds the structured metric into the judge input)."""
    chat = _RecordingChat(verdict="amber", reasons=["wrong_metric"])
    hyp = Hypothesis(
        capability_name="reorder",
        prose="Nudge users to come back next week with a weekly summary.",
        metric_name="ctr",
        decision_point="you've just finished tonight's session",
        conversion_action="tap the summary",
        conversion_action_label="see your week",
    )
    v = _run(assess_input_lint(hyp, chat_client=chat))
    assert v.state == "amber"
    assert "wrong_metric" in v.reason_codes
    # The judge actually SAW the declared metric (so it could detect the
    # mismatch) — the coherence pass shapes the judge input, not a new call.
    assert any("Declared metric: ctr" in turn for turn in chat.user_turns)


def test_coherence_metric_free_hypothesis_is_byte_identical_judge_input() -> None:
    """No declared metric -> the judge sees the bare prose (historical input),
    so a metric-free hypothesis is unchanged by the coherence pass."""
    chat = _RecordingChat(verdict="green")
    _run(assess_input_lint(_hyp("Add a reorder button to the home tab."), chat_client=chat))
    assert chat.user_turns
    for turn in chat.user_turns:
        assert "Declared metric" not in turn


def test_coherence_circular_mechanism_maps_to_broken_mechanism_amber() -> None:
    """A circular / non-mechanistic mechanism ("it'll work because it's better")
    -> broken_mechanism, amber."""
    chat = _StubJudgeChat(verdict="amber", reasons=["broken_mechanism"])
    v = _run(
        assess_input_lint(
            _hyp("Redesign the home tab; it'll work because it's just better."),
            chat_client=chat,
        )
    )
    assert v.state == "amber"
    assert "broken_mechanism" in v.reason_codes
    assert v.is_flagged is True


def test_coherence_findings_keep_confidence_path_untouched() -> None:
    """A coherence finding is still just a categorical verdict carrying taxonomy
    reason_codes — no scalar, no confidence field. The dataclass exposes only the
    existing categorical surface (regression guard for the no-scalar constraint)."""
    chat = _StubJudgeChat(verdict="amber", reasons=["wrong_metric"])
    v = _run(assess_input_lint(_hyp("Tweak the funnel for all users."), chat_client=chat))
    # No scalar/score attribute leaked onto the verdict.
    assert not hasattr(v, "score")
    assert not hasattr(v, "confidence_score")
    assert v.state in ("green", "amber", "red", "abstain")
