"""PortfolioCase → BenchmarkCase adapter (product-change directional portfolio).

The portfolio mirror of `services.cookiecats_adapter` / `services.hillstrom_adapter`.
It turns each curated published-narrative product-change case
(`services.portfolio_archive.PortfolioCase`) into the SAME `(Capability,
Hypothesis)` shape production builds, each carrying a `GroundTruth` that encodes
the REAL winner's SIGN — so the whole experiment is ONE directional bit scored
through the shared blinded engine.

WHAT IS DIFFERENT FROM THE SIBLING ADAPTERS (and why). Cookie Cats / Hillstrom
have RAW per-user rows, so their `GroundTruth.observed_lift` is a measured
difference-in-means (a real magnitude). The portfolio cases are PUBLISHED
NARRATIVES with no per-user data — only a REPORTED winner (and a publication-
biased point estimate that is OUT OF SCOPE, see PORTFOLIO_CASES.json
`methodology.scoring`). So this adapter encodes ONLY the SIGN of the real winner
as a unit-magnitude `observed_lift`:

    real_winner == "treatment"  →  observed_lift = +1.0   (winner "treatment")
    real_winner == "control"    →  observed_lift = -1.0   (winner "control")

This matches the sign convention every sibling adapter uses (`_winner`:
positive lift → treatment wins, negative → control wins). The MAGNITUDE 1.0 is a
deliberate sentinel — it is never interpreted as a real effect size. Only the
SIGN is scored (direction_accuracy is the headline); rank-ρ across these cases is
NOT a credible magnitude claim (the narratives' effect sizes are inflated by
publication bias) and the run reports it directionally / for cross-case ordering
only. This is recorded in the module + the pre-registration.

HOW A DESCRIBED CHANGE IS RENDERED AS A BLINDED ENGINE STIMULUS (the crux). The
engine path renders a state-DIFF: `Capability.reverse_figma` is the CONTROL
(current) state and `Hypothesis.proposed_figma` is the TREATMENT (proposed) state
(`services.treatment_renderer.render_state_diff`). A portfolio case has only TEXT,
so we build a MINIMAL standalone state for each arm: a single `Screen` carrying
one `Component` whose `text` is the case's `control` (resp. `treatment`)
narrative, plus a one-line generic framing in the `reverse_prd` / hypothesis
`prose`. The change presented to the engine is therefore "the screen's body copy
switches from the control description to the treatment description" — exactly the
production copy/value state-diff path, built from the case's own words.

STRUCTURAL BLINDNESS (the load-bearing invariant, proven by a test). The rendered
stimulus the engine sees — `capability` + `hypothesis` — carries ONLY the
control/treatment narratives and a GENERIC metric framing. It NEVER carries
`real_winner`, the `effect` magnitude string, the `counter_intuitive` /
`credibility` / `contamination` metadata, or the `metric` name (which can hint
the direction, e.g. "control won; treatment -64% buy-button clickers"). Those
ride ONLY on `GroundTruth` (the held-out answer key) and the case_id, never in the
stimulus. So the engine is label-invariant by construction and the null-integrity
certificate's scrambled-label re-run leaves its predictions unchanged → PASS.

METRIC MAPPING (heterogeneous metrics → one generic engine elicitation). The
cases span retention, conversion, clicks, referral revenue, signups. Rather than
fragment them across the engine's four registered metrics (conversion / retention
/ ctr / visit) — which would split one directional bit per case into mismatched
elicitations and complicate the single-bit-per-experiment design — every case is
scored through the engine's single generic `conversion` metric: "faced with this
variant, would you take its primary action?" Direction (which variant wins on the
generic act) is all that is scored, so a generic engagement/conversion elicitation
is the clean choice. The per-case real metric is preserved on the PortfolioCase
(for the report) but is NOT shown to the engine (it can leak direction). This is a
documented limitation: the generic elicitation may under-fit a case whose real
mechanism is retention-shaped rather than immediate-conversion-shaped.
"""

from __future__ import annotations

from collections.abc import Sequence

from sidira_simulator.schemas.benchmark import BenchmarkCase, GroundTruth
from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
)
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.portfolio_archive import (
    WINNER_TREATMENT,
    PortfolioArchive,
    PortfolioCase,
)

_SOURCE = "portfolio"

# Screen / component ids for the standalone product-state stimulus. Both arms show
# the SAME single screen; the CHANGED delta is the body copy (control narrative →
# treatment narrative). Stable ids so the rendered diff is one component swap.
STATE_SCREEN_ID = "product_state"
STATE_COMPONENT_ID = "product_state_body"

# The sentinel directional magnitudes. The portfolio cases carry NO per-user data,
# so observed_lift encodes ONLY the real winner's SIGN at unit magnitude — it is
# never a real effect size (publication-bias-inflated point estimates are out of
# scope). +1 = treatment wins, -1 = control wins, matching the sibling adapters'
# _winner sign convention.
_TREATMENT_WINS_LIFT = 1.0
_CONTROL_WINS_LIFT = -1.0

# The sentinel control / treatment "rates" carried on GroundTruth. The schema
# requires both >= 0 and treatment - control == observed_lift; we anchor control
# at 1.0 so a -1.0 (control-wins) lift keeps treatment at 0.0 (both non-negative),
# and use 0.0 control for a +1.0 (treatment-wins) lift. These are NOT measured
# rates — they exist only so the GroundTruth's fields stay internally consistent
# with the directional sentinel (the runner re-derives the same shape for the null
# scramble). Never reported as a metric value.
_CONTROL_WINS_CONTROL_RATE = 1.0
_TREATMENT_WINS_CONTROL_RATE = 0.0


def _winner_lift(real_winner: str) -> float:
    """The signed directional sentinel for a real winner.

    treatment-wins → +1.0; control-wins → -1.0. The PortfolioCase loader already
    validated `real_winner` ∈ {control, treatment}, so this is a total mapping
    over valid input; an unexpected value raises (defense-in-depth) rather than
    silently encoding a zero/tie sentinel that would mis-score the bit.
    """
    if real_winner == WINNER_TREATMENT:
        return _TREATMENT_WINS_LIFT
    if real_winner == "control":
        return _CONTROL_WINS_LIFT
    raise ValueError(
        f"PortfolioCase.real_winner must be 'control' or 'treatment', got {real_winner!r}"
    )


def _winner_label(lift: float) -> str:
    """Winner label from a signed lift (matches the sibling adapters' _winner)."""
    if lift > 0.0:
        return "treatment"
    if lift < 0.0:
        return "control"
    return "tie"


def _state_figma(body: str) -> ReverseFigma:
    """A minimal standalone state for one arm: one screen, one body component.

    The arm's narrative (the case's `control` or `treatment` text) is the screen's
    body copy. Both arms share the SAME screen id, so the rendered control→treatment
    diff is exactly ONE changed component — the production copy/value state-diff
    path, built from the case's own words. Carries NOTHING but the narrative copy
    (no winner / effect / metric leak).
    """
    return ReverseFigma(
        screens=[
            Screen(
                id=STATE_SCREEN_ID,
                name="Product state",
                components=[
                    Component(id=STATE_COMPONENT_ID, role="body", text=body),
                ],
            )
        ],
        transitions=[],
    )


def _case_capability_hypothesis(case: PortfolioCase) -> tuple[Capability, Hypothesis]:
    """The `(Capability, Hypothesis)` control→treatment copy-delta pair for a case.

    The structural-blindness boundary: this carries ONLY the control / treatment
    narratives plus a GENERIC framing — never `real_winner`, the `effect`
    magnitude string, the `metric` name, or any other answer-hinting metadata. The
    capability is the CONTROL (current) state; the hypothesis's proposed_figma is
    the TREATMENT (proposed) state. The single CHANGED delta is the body copy.

    The framing is deliberately metric-NEUTRAL and direction-NEUTRAL: it describes
    a user encountering the product and frames the implicit metric as the generic
    "primary action" so neither arm is told which is preferred (a metric like
    "buy-button clickers" can itself hint the direction — kept off the stimulus).
    """
    reverse_prd = (
        "A user encounters this product experience. The description below is the "
        "CURRENT version of the experience."
    )
    capability = Capability(
        name="product change under test",
        surfaces=["product"],
        roles=["user"],
        entry_points=[STATE_SCREEN_ID],
        reverse_prd=reverse_prd,
        reverse_figma=_state_figma(case.control),
        implicit_metric="whether the user takes the experience's primary action",
    )
    hypothesis = Hypothesis(
        capability_name=capability.name,
        prose=(
            "Change the experience to the proposed version described below. Nothing "
            "else about the user's situation changes — only this experience differs."
        ),
        proposed_prd=None,
        proposed_figma=_state_figma(case.treatment),
    )
    return capability, hypothesis


def build_portfolio_case(case: PortfolioCase) -> BenchmarkCase:
    """Build ONE benchmark case from a `PortfolioCase` (a whole-experiment bit).

    The case is the SAME `(Capability, Hypothesis)` shape production builds:
    control = the case's control narrative; treatment = its treatment narrative as
    a copy delta. `GroundTruth` encodes ONLY the real winner's SIGN at unit
    magnitude (see the module docstring) — direction is what's scored. The case_id
    is `portfolio:<case id>` so the per-case honesty stratifier can report each
    experiment as its own bit.

    STRUCTURAL BLINDNESS: the rendered capability + hypothesis carry only the
    narratives + a generic framing; `real_winner` / `effect` / `metric` ride only
    on `GroundTruth` + the case_id, never in the stimulus.
    """
    lift = _winner_lift(case.real_winner)
    capability, hypothesis = _case_capability_hypothesis(case)
    if lift > 0.0:
        control_metric = _TREATMENT_WINS_CONTROL_RATE
        treatment_metric = control_metric + lift  # 0.0 + 1.0
    else:
        control_metric = _CONTROL_WINS_CONTROL_RATE
        treatment_metric = control_metric + lift  # 1.0 + (-1.0) = 0.0
    ground_truth = GroundTruth(
        metric_name=case.metric or "directional",
        control_metric=control_metric,
        treatment_metric=treatment_metric,
        observed_lift=lift,
        winner=_winner_label(lift),
    )
    return BenchmarkCase(
        case_id=f"{_SOURCE}:{case.id}",
        source=_SOURCE,
        capability=capability,
        hypothesis=hypothesis,
        ground_truth=ground_truth,
    )


def portfolio_cases_to_benchmark_cases(cases: Sequence[PortfolioCase]) -> list[BenchmarkCase]:
    """Adapt a sequence of `PortfolioCase`s into `BenchmarkCase`s (one bit each).

    Each whole experiment becomes one directional benchmark case. Raises
    ValueError on an empty sequence (nothing to score is a caller bug) — the
    null-integrity certificate needs >= 8 cases, so an empty/too-small set must
    fail loud rather than silently produce an uncertifiable run.
    """
    if not cases:
        raise ValueError("portfolio_cases_to_benchmark_cases requires at least one case")
    return [build_portfolio_case(c) for c in cases]


def scored_portfolio_cases(archive: PortfolioArchive) -> list[BenchmarkCase]:
    """The SCORED set as benchmark cases (the certifiable portfolio).

    Reads `archive.scored_cases` only — the held-out memorization probe is NEVER
    folded into the scored set (it is a contamination control, scored separately
    and non-scored by default). Raises ValueError if the archive carries no scored
    cases.
    """
    return portfolio_cases_to_benchmark_cases(archive.scored_cases)


def held_out_probe_cases(archive: PortfolioArchive) -> list[BenchmarkCase]:
    """The held-out memorization-probe set as benchmark cases (NON-scored).

    The probe carries a compact `change` description (not a control/treatment
    split), so each probe is rendered as a single CHANGE narrative: the control
    state is a neutral "the current experience" placeholder and the treatment
    state is the probe's `change` text. This is a CONTAMINATION CONTROL — a run
    must label it clearly as NON-scored and never average it into the certified
    portfolio score (a sim that aces the famous probes but flunks the obscure
    scored cases is reciting, not reasoning). Raises ValueError if the archive
    carries no probe cases.
    """
    probes = archive.held_out_probe
    if not probes:
        raise ValueError("held_out_probe_cases requires at least one held-out probe")
    out: list[BenchmarkCase] = []
    for probe in probes:
        winner = probe.real_winner.strip().lower()
        # The probe's real_winner is free text (e.g. "control (won all 5)"); read
        # the leading arm word, defaulting to treatment if neither is named (the
        # probe is non-scored, so a soft default here cannot corrupt a certified
        # score — but we still record the parsed sign honestly).
        real = "control" if winner.startswith("control") else WINNER_TREATMENT
        synthetic = PortfolioCase(
            id=probe.id,
            domain="held_out_probe",
            control="The current version of the experience (the incumbent).",
            treatment=probe.change,
            metric="directional",
            real_winner=real,
            effect="",
            counter_intuitive="n/a",
            contamination="high (held-out memorization probe)",
            credibility="n/a",
            source="held_out_memorization_probe",
            raw_data=False,
        )
        out.append(build_portfolio_case(synthetic))
    return out
