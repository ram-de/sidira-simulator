"""Tests for the PortfolioCase → BenchmarkCase adapter (directional portfolio).

Mirrors `test_cookiecats_adapter`. Pins:
- the real-winner SIGN encoding on ground_truth (treatment-wins → +, control-wins → −),
- the adapter producing well-formed `BenchmarkCase`s (control narrative → capability
  reverse_figma, treatment narrative → hypothesis proposed_figma, one changed component),
- THE BLINDNESS TEST: the rendered stimulus the engine sees carries neither
  `real_winner`, the `effect` magnitude string, nor the real `metric` name,
- ARM VALENCE SYMMETRY: neither rendered arm carries evaluative/outcome lexicon
  (e.g. "winner", "more appealing", "simplest") — applied symmetrically to both
  arms so a fixture can't leak preference onto one side only,
- the held-out probe adapting to NON-scored cases separately,
- the >= 1 case guard.
"""

from __future__ import annotations

import re

import pytest

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.services.portfolio_adapter import (
    STATE_COMPONENT_ID,
    STATE_SCREEN_ID,
    build_portfolio_case,
    held_out_probe_cases,
    portfolio_cases_to_benchmark_cases,
    scored_portfolio_cases,
)
from sidira_simulator.services.portfolio_archive import (
    HeldOutProbe,
    PortfolioArchive,
    PortfolioCase,
)


def _case(**over) -> PortfolioCase:
    # The control / treatment narratives are deliberately NEUTRAL and PARALLEL:
    # they describe ONLY the structural mechanic (the form's field count), with no
    # evaluative or outcome-hinting adjective on either arm. An earlier fixture
    # ("The existing onboarding flow" vs "A shorter onboarding flow") baked in an
    # arm-asymmetric valence ("shorter" is a comparative that reads as preferred on
    # one arm) and still passed the old blindness test — exactly the leak class
    # `test_rendered_arms_are_valence_symmetric` now guards against. Keep both arms
    # mechanic-only so the suite passes HONESTLY under the valence check.
    base = dict(
        id="case_a",
        domain="saas",
        control="Onboarding flow with 9 form fields.",
        treatment="Onboarding flow with 6 form fields.",
        metric="conversions",
        real_winner="control",
        effect="control won; treatment -14% conversions",
        counter_intuitive="high",
        contamination="med",
        credibility="med",
        source="CXL",
        raw_data=False,
    )
    base.update(over)
    return PortfolioCase(**base)  # type: ignore[arg-type]


# ── REAL-WINNER SIGN ENCODING ───────────────────────────────────────────────────


def test_treatment_wins_encodes_positive_lift() -> None:
    case = build_portfolio_case(_case(real_winner="treatment"))
    assert case.ground_truth.observed_lift == pytest.approx(1.0)
    assert case.ground_truth.winner == "treatment"
    # The sentinel rates are internally consistent (treatment − control == lift)
    # and both non-negative (schema requires >= 0).
    gt = case.ground_truth
    assert gt.treatment_metric - gt.control_metric == pytest.approx(gt.observed_lift)
    assert gt.control_metric >= 0.0 and gt.treatment_metric >= 0.0


def test_control_wins_encodes_negative_lift() -> None:
    case = build_portfolio_case(_case(real_winner="control"))
    assert case.ground_truth.observed_lift == pytest.approx(-1.0)
    assert case.ground_truth.winner == "control"
    gt = case.ground_truth
    assert gt.treatment_metric - gt.control_metric == pytest.approx(gt.observed_lift)
    assert gt.control_metric >= 0.0 and gt.treatment_metric >= 0.0


# ── BENCHMARK CASE SHAPE ────────────────────────────────────────────────────────


def test_build_case_is_well_formed() -> None:
    case = build_portfolio_case(_case())
    assert isinstance(case, BenchmarkCase)
    assert case.source == "portfolio"
    assert case.case_id == "portfolio:case_a"
    assert isinstance(case.ground_truth, GroundTruth)


def test_control_and_treatment_are_a_single_component_diff() -> None:
    """Control = the control narrative as a standalone state; treatment = the SAME
    single screen with the body copy swapped to the treatment narrative."""
    case = build_portfolio_case(_case())
    control_screens = {s.id for s in case.capability.reverse_figma.screens}
    treatment_screens = {s.id for s in case.hypothesis.proposed_figma.screens}
    assert control_screens == treatment_screens == {STATE_SCREEN_ID}
    control_body = next(
        c
        for s in case.capability.reverse_figma.screens
        for c in s.components
        if c.id == STATE_COMPONENT_ID
    )
    treatment_body = next(
        c
        for s in case.hypothesis.proposed_figma.screens
        for c in s.components
        if c.id == STATE_COMPONENT_ID
    )
    assert "9 form fields" in control_body.text
    assert "6 form fields" in treatment_body.text


# ── THE BLINDNESS TEST (the load-bearing invariant) ─────────────────────────────


def test_rendered_stimulus_is_structurally_blind() -> None:
    """The rendered stimulus the engine sees (capability + hypothesis) must carry
    NEITHER the real_winner, NOR the effect magnitude string, NOR the real metric
    name — those leak the answer and ride ONLY on ground_truth + case_id."""
    src = _case(
        real_winner="control",
        effect="control won; treatment -64% buy-button clickers",
        metric="Buy-button clickers",
    )
    case = build_portfolio_case(src)
    stimulus = (case.capability.model_dump_json() + case.hypothesis.model_dump_json()).lower()
    assert src.real_winner not in stimulus
    assert "64" not in stimulus  # effect magnitude must not leak
    assert "buy-button" not in stimulus  # the real metric name can hint direction
    assert "won" not in stimulus  # no winner verb in the stimulus
    # The answer key DOES live on ground_truth (it is the held-out label).
    assert case.ground_truth.winner == "control"


def test_blindness_holds_across_the_committed_set() -> None:
    """Every committed scored case is structurally blind: no real_winner / effect
    digits in its rendered stimulus."""
    from sidira_simulator.services.portfolio_archive import load_portfolio_cases

    arc, _ = load_portfolio_cases()
    for src in arc.scored_cases:
        case = build_portfolio_case(src)
        stim = (case.capability.model_dump_json() + case.hypothesis.model_dump_json()).lower()
        assert src.real_winner not in stim, src.id


# ── ARM VALENCE SYMMETRY / NO OUTCOME LEAK ──────────────────────────────────────
#
# The old blindness test only checked that the stimulus omits the real_winner, the
# effect MAGNITUDE digits, the real metric NAME, and the literal verb "won". It did
# NOT catch two real leak classes an audit found in authored narratives:
#
#   1. OUTCOME LEAKS that aren't the word "won" — e.g. "winner of 6 variants"
#      ("winner" passes a "won"-only check but still names the result).
#   2. ARM-ASYMMETRIC VALENCE — evaluative adjectives that tell the reader which
#      arm is better ("MORE appealing", "Simplest", "preferred"), which biases the
#      blinded engine toward the leaked answer even with no explicit winner string.
#
# A blinded stimulus must describe each arm's MECHANIC only; whether an arm is
# good/bad/preferred is the held-out answer and belongs on ground_truth. The ban
# list below is curated (not a blanket "more") and each entry is tagged with WHY:
#   [O] = outcome/result leak   [V] = evaluative valence
#
# Curated, word-boundary, case-insensitive. We avoid a blanket "more" (false
# positives like "more offers" / "more free play" are legitimate mechanic copy)
# and instead ban specific evaluative comparatives.
_BANNED_LEXICON: dict[str, str] = {
    # ── Outcome / result leaks ────────────────────────────────────────────────
    "winner": "[O] names the result of the experiment",
    "won": "[O] names the result of the experiment",
    "win": "[O] names the result of the experiment",
    "wins": "[O] names the result of the experiment",
    "best": "[O] superlative result claim",
    "optimal": "[O] superlative result claim",
    "superior": "[O]/[V] declares one arm the better outcome",
    # ── Evaluative valence (asymmetric preference signals) ─────────────────────
    "better": "[V] comparative preference",
    "worse": "[V] comparative preference",
    "appealing": "[V] judges desirability",
    "preferred": "[V] declares an arm preferred",
    "popular": "[V] implies the chosen/liked arm",
    "improved": "[V] frames a change as an improvement",
    "improvement": "[V] frames a change as an improvement",
    "simplest": "[V] superlative quality claim",
    "simpler": "[V] comparative quality claim",
    "prettier": "[V] comparative aesthetic claim",
    "nicer": "[V] comparative quality claim",
    "cleaner": "[V] comparative quality claim",
    # "shorter"/"simplified" are borderline mechanic vs. valence; banned because in
    # practice they appear ONLY on the treatment arm and read as the preferred arm.
    "shorter": "[V] comparative that in practice marks the favored arm",
    "simplified": "[V] frames a change as an improvement",
    # ── Behavior-history / preference signals (codex P2) ───────────────────────
    # "(cut the 3 MOST-engaged-with fields)" tells the engine WHICH elements users
    # valued — an asymmetric direction cue (removing high-engagement fields hints
    # the change is worse). The stimulus should state the mechanic (fields removed),
    # not the held-out behavioral judgement, so ban engagement-history wording.
    "engaged": "[V] user-behavior/preference-history signal (which arm users liked)",
    "engagement": "[V] user-behavior/preference-history signal (which arm users liked)",
}

_BANNED_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(rf"\b{re.escape(tok)}\b", re.IGNORECASE), why)
    for tok, why in _BANNED_LEXICON.items()
]


def _banned_hits(text: str) -> list[str]:
    """Banned-lexicon tokens present in `text` (word-boundary, case-insensitive)."""
    return [f"{pat.pattern!r} ({why})" for pat, why in _BANNED_PATTERNS if pat.search(text)]


def _arm_bodies(case: BenchmarkCase) -> tuple[str, str]:
    """The rendered (control_body, treatment_body) copy the engine actually sees."""
    control_body = next(
        c.text
        for s in case.capability.reverse_figma.screens
        for c in s.components
        if c.id == STATE_COMPONENT_ID
    )
    treatment_body = next(
        c.text
        for s in case.hypothesis.proposed_figma.screens
        for c in s.components
        if c.id == STATE_COMPONENT_ID
    )
    return control_body, treatment_body


def test_banned_lexicon_helper_flags_known_leaks() -> None:
    """Self-check the detector on the exact real-world defects the audit found, so a
    future weakening of the ban list fails here rather than silently disarming the
    valence guard."""
    assert _banned_hits("Simplest, search-like redesigned layout (winner of 6 variants)")
    assert _banned_hits("Redesign most users found MORE appealing")
    assert _banned_hits("Simplified to 3 steps")
    assert _banned_hits("6-field form (cut the 3 MOST-engaged-with fields)")
    # Pure mechanic copy is clean (and "more" alone is NOT banned).
    assert _banned_hits("Add 3 paid offers below the shopping module") == []
    assert _banned_hits("Onboarding flow with 6 form fields.") == []
    assert _banned_hits("6-field form (3 fields removed)") == []


def test_rendered_arms_are_valence_symmetric() -> None:
    """BOTH rendered arms must be free of evaluative/outcome lexicon — symmetrically.

    A blinded stimulus describes each arm's MECHANIC only; an evaluative adjective
    ("more appealing") or an outcome word ("winner") on EITHER arm leaks the answer
    the engine is supposed to predict. We assert the SAME ban on control_body and
    treatment_body so a fixture can't sneak valence onto one arm only."""
    case = build_portfolio_case(_case())
    control_body, treatment_body = _arm_bodies(case)
    assert _banned_hits(control_body) == [], f"control arm leaks: {control_body!r}"
    assert _banned_hits(treatment_body) == [], f"treatment arm leaks: {treatment_body!r}"


def test_committed_scored_cases_are_valence_symmetric() -> None:
    """The guard runs against the REAL committed cases the adapter loads, not only
    the synthetic fixture (codex P2). Each committed scored case's rendered arms
    must be free of evaluative/outcome lexicon on BOTH sides — this is what
    actually protects the benchmark data from silently reintroducing a leak (the
    audit found "winner of 6 variants" / "MORE appealing" / "Simplified" living in
    the committed set; neutralized in the same change)."""
    from sidira_simulator.services.portfolio_archive import load_portfolio_cases

    arc, _ = load_portfolio_cases()
    leaks: dict[str, list[str]] = {}
    for src in arc.scored_cases:
        case = build_portfolio_case(src)
        control_body, treatment_body = _arm_bodies(case)
        hits = _banned_hits(control_body) + _banned_hits(treatment_body)
        if hits:
            leaks[src.id] = hits
    assert not leaks, f"committed scored cases leak banned lexicon: {leaks}"


# ── ENUMERATION + GUARDS ────────────────────────────────────────────────────────


def test_scored_cases_excludes_probe() -> None:
    arc = PortfolioArchive(
        portfolio_id="p",
        scored_cases=[_case(id="s1"), _case(id="s2")],
        held_out_probe=[
            HeldOutProbe(id="p1", change="x", real_winner="control", why_held_out="famous")
        ],
        human_baseline_anchors={},
        balance_check={},
        methodology={},
    )
    cases = scored_portfolio_cases(arc)
    assert {c.case_id for c in cases} == {"portfolio:s1", "portfolio:s2"}


def test_held_out_probe_cases_are_separate_non_scored() -> None:
    arc = PortfolioArchive(
        portfolio_id="p",
        scored_cases=[_case(id="s1")],
        held_out_probe=[
            HeldOutProbe(
                id="netflix",
                change="wall -> browse first",
                real_winner="control (won all 5)",
                why_held_out="famous",
            ),
            HeldOutProbe(
                id="highrise",
                change="long -> short page",
                real_winner="treatment (+47%)",
                why_held_out="famous",
            ),
        ],
        human_baseline_anchors={},
        balance_check={},
        methodology={},
    )
    probes = held_out_probe_cases(arc)
    assert {c.case_id for c in probes} == {"portfolio:netflix", "portfolio:highrise"}
    # The "control (won all 5)" probe parses to a control-wins (negative) sign.
    netflix = next(c for c in probes if c.case_id == "portfolio:netflix")
    assert netflix.ground_truth.winner == "control"
    highrise = next(c for c in probes if c.case_id == "portfolio:highrise")
    assert highrise.ground_truth.winner == "treatment"


def test_empty_cases_raises() -> None:
    with pytest.raises(ValueError, match="at least one case"):
        portfolio_cases_to_benchmark_cases([])


def test_duplicate_case_ids_raise() -> None:
    """Two cases with the same id would collapse to one case_id and silently reuse a
    prediction (the cache is keyed by case_id) — must FAIL LOUD (codex)."""
    with pytest.raises(ValueError, match="duplicate portfolio case id"):
        portfolio_cases_to_benchmark_cases([_case(id="dup"), _case(id="dup")])
