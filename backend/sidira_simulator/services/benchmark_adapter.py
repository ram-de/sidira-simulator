"""Upworthy archive → Hypothesis adapter (agent-behavior-spec §1 / ticket #222).

Turns an archived Upworthy clickability test into `BenchmarkCase`s whose
`(capability, hypothesis)` pair is the EXACT shape production builds, so the
benchmark feeds the shared renderer (`treatment_renderer.render_state_diff`)
with no benchmark-only path. That structural identity — not a string-match
assertion — is what makes the Tier-0 benchmark a real test of the production
treatment-rendering layer (treatment-rendering-layer.md §4).

Modelling choice. An Upworthy unit is "a promoted story card in the feed that,
when clicked, opens the article." We model two screens:

  - `story_card` — carries the `headline` (and a fixed `eyecatcher` image), the
    surface the experiment actually varies;
  - `article`   — the unchanged destination, linked by a `click` transition.

A headline A/B swap is then exactly ONE `CHANGED`/copy delta on the `headline`
component; the `article` screen is unchanged, so the renderer's "Explicitly NOT
changing" guard names it concretely. CTR (= clicks / impressions) is the click
on that transition — the measured outcome.

Scope (v1, the forcing function). A pair that also swaps the image cannot be
expressed as a copy state-diff — `ReverseFigma` carries no image *content* — so
`build_upworthy_case` raises and the enumerator records a `SkippedPair` rather
than silently faking an image change as copy. Per §4 that unrepresentability is
a signal the *production* path can't model that change class either, not a row
to drop from the benchmark's denominator.
"""

from __future__ import annotations

from sidira_simulator.schemas.benchmark import (
    BenchmarkCase,
    GroundTruth,
    SkippedPair,
    UpworthyAdaptationResult,
    UpworthyTest,
    UpworthyVariant,
)
from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
    Transition,
)
from sidira_simulator.schemas.simulation import Hypothesis

CARD_SCREEN_ID = "story_card"
ARTICLE_SCREEN_ID = "article"
HEADLINE_COMPONENT_ID = "headline"
EYECATCHER_COMPONENT_ID = "eyecatcher"
CLICK_TRIGGER = "click_headline"

_SOURCE = "upworthy"


def _card_figma(headline: str, eyecatcher_id: str | None) -> ReverseFigma:
    """The two-screen state for one headline package.

    The `eyecatcher` image component is included identically across arms when
    present so it reads as held-fixed context in the agent's view; its *content*
    (which image) is never encoded — see the module docstring on scope.
    """
    card_components = [
        Component(id=HEADLINE_COMPONENT_ID, role="headline", text=headline),
    ]
    if eyecatcher_id is not None:
        card_components.append(Component(id=EYECATCHER_COMPONENT_ID, role="image", text=None))
    return ReverseFigma(
        screens=[
            Screen(
                id=CARD_SCREEN_ID,
                name="Promoted story card",
                components=card_components,
            ),
            Screen(id=ARTICLE_SCREEN_ID, name="Story article", components=[]),
        ],
        transitions=[
            Transition(
                trigger=CLICK_TRIGGER,
                from_screen=CARD_SCREEN_ID,
                to_screen=ARTICLE_SCREEN_ID,
            )
        ],
    )


def _ground_truth(control: UpworthyVariant, treatment: UpworthyVariant) -> GroundTruth:
    lift = treatment.ctr - control.ctr
    if lift > 0:
        winner = "treatment"
    elif lift < 0:
        winner = "control"
    else:
        winner = "tie"
    return GroundTruth(
        metric_name="ctr",
        control_metric=control.ctr,
        treatment_metric=treatment.ctr,
        observed_lift=lift,
        winner=winner,
    )


def build_upworthy_case(
    test: UpworthyTest,
    control_index: int,
    treatment_index: int,
) -> BenchmarkCase:
    """Build ONE benchmark case from a (control, treatment) headline pair.

    Raises `ValueError` if the pair is not a pure headline swap — i.e. the two
    packages differ in their eyecatcher image, which is an image / multi-factor
    change `ReverseFigma` cannot represent as a copy state-diff. The enumerator
    catches this and records a `SkippedPair`.

    Also raises `ValueError` on an out-of-range index: this is a public builder,
    so it validates its own arguments rather than letting a negative index
    silently wrap (yielding a bogus `case_id` like `-1v0`) or an over-range one
    raise an uncaught `IndexError`.
    """
    n = len(test.variants)
    for label, idx in (("control_index", control_index), ("treatment_index", treatment_index)):
        if not 0 <= idx < n:
            raise ValueError(f"{label} {idx} out of range for {n} variants")

    control = test.variants[control_index]
    treatment = test.variants[treatment_index]

    if control.eyecatcher_id != treatment.eyecatcher_id:
        # Differing image identity is a multi-factor change ReverseFigma can't
        # encode. Equality here certifies held-fixed — including the None==None
        # case, where None is the explicit "no image on the card" sentinel (see
        # UpworthyVariant.eyecatcher_id): both cards have no image, so there is
        # nothing to hold fixed. Importers MUST set a real id when an image
        # exists; defaulting to None to mean "unknown" would violate that
        # contract and is the importer's bug, not something to re-litigate here.
        raise ValueError(
            "image / multi-factor change: variants differ in eyecatcher "
            f"({control.eyecatcher_id!r} → {treatment.eyecatcher_id!r}); not "
            "representable as a copy state-diff in v1"
        )

    if control.headline == treatment.headline:
        # Same index, or a duplicate package in the archive. With the eyecatcher
        # already equal, the two states are identical: render_state_diff yields no
        # delta and no standalone view, yet the pair could still carry a non-zero
        # ground-truth lift from traffic noise — a label for an intervention the
        # agents never see. Reject so it is recorded as skipped, not scored.
        raise ValueError(
            f"no-op pair: control and treatment share headline {control.headline!r}; "
            "no structural delta to render"
        )

    context_line = f" Story: {test.article_context}" if test.article_context else ""
    # Keep the PRD consistent with the structural state: only mention the image
    # when the card actually has one (eyecatcher present). A no-image card (None
    # sentinel) emits no eyecatcher component, so claiming "above the story image"
    # would give the agent context the rendered state does not contain.
    image_clause = " above the story image" if control.eyecatcher_id is not None else ""
    reverse_prd = (
        f"A promoted story card in the feed shows the headline "
        f"{control.headline!r}{image_clause}. Readers click the "
        f"headline to open the article.{context_line}"
    )

    capability = Capability(
        name="promoted story headline",
        surfaces=["feed"],
        roles=["reader"],
        entry_points=["feed"],
        reverse_prd=reverse_prd,
        reverse_figma=_card_figma(control.headline, control.eyecatcher_id),
        implicit_metric="click-through rate (reader clicks the story card)",
    )

    hypothesis = Hypothesis(
        capability_name=capability.name,
        prose=(
            f"Change the promoted headline from {control.headline!r} to "
            f"{treatment.headline!r}. Everything else about the card and the "
            "article it links to stays the same."
        ),
        proposed_prd=None,
        proposed_figma=_card_figma(treatment.headline, treatment.eyecatcher_id),
    )

    return BenchmarkCase(
        case_id=f"{test.test_id}:{control_index}v{treatment_index}",
        source=_SOURCE,
        capability=capability,
        hypothesis=hypothesis,
        ground_truth=_ground_truth(control, treatment),
    )


def upworthy_test_to_cases(
    test: UpworthyTest,
    baseline_index: int = 0,
) -> UpworthyAdaptationResult:
    """Enumerate a test as baseline-vs-each-other-variant benchmark cases.

    Mirrors the archive's "control headline vs each challenger" framing: the
    package at `baseline_index` is the control, every other package a treatment.
    Pairs that are not representable as a headline swap are recorded in
    `result.skipped` rather than dropped — so the benchmark's denominator stays
    honest about what it could and couldn't model.
    """
    if not 0 <= baseline_index < len(test.variants):
        # A negative index would silently emit a self-comparison (the loop skips
        # by ==, not by identity); an over-range one would raise an uncaught
        # IndexError mid-build. Reject explicitly so a bad baseline fails loudly.
        raise ValueError(
            f"baseline_index {baseline_index} out of range for " f"{len(test.variants)} variants"
        )

    cases: list[BenchmarkCase] = []
    skipped: list[SkippedPair] = []
    for i in range(len(test.variants)):
        if i == baseline_index:
            continue
        try:
            cases.append(build_upworthy_case(test, baseline_index, i))
        except ValueError as exc:
            skipped.append(
                SkippedPair(
                    control_index=baseline_index,
                    treatment_index=i,
                    reason=str(exc),
                )
            )
    return UpworthyAdaptationResult(cases=cases, skipped=skipped)
