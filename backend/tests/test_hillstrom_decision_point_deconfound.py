"""Regression tests for the Hillstrom decision_point de-confounding fix.

THE CONFOUND (found by a stimulus audit): the Hillstrom A/B is treatment = a
marketing e-mail is received, control = NO e-mail. The blinded elicitation
`decision_point` built in `cli._hillstrom_hypothesis_builder` was hardcoded to
"the customer is reading the promotional e-mail in their inbox" and threaded —
unchanged — into BOTH arms' user turn ("You're at this moment: {decision_point}").
So the No-E-Mail CONTROL agent was told it was reading the very e-mail the
treatment arm ADDS, contaminating control, inflating its propensity, and
mechanically pushing the treatment−control delta toward zero/negative (the
suspected cause of direction_accuracy 0.0 — the sim looked "ad-averse" when
really the control had been told it saw the ad).

THE FIX (single variable): the shared `decision_point` is now e-mail-FREE and
arm-neutral ("the customer is looking at their inbox") — equally true for both
arms. The treatment e-mail is conveyed ONLY where it belongs: the per-arm
STRUCTURAL spec in `compose_metric_prompt` (treatment renders a `promo_email`
screen + body copy; control renders only the `inbox` screen).

These tests render the FULL metric stimulus each arm actually sees — the blinded
system prompt (structural spec) plus the conversion user turn (which carries the
`decision_point`) — and assert the e-mail's presence is ARM-CORRECT:

- the `decision_point` line ("You're at this moment: ...") is e-mail-FREE in BOTH
  arms — this is the surgical surface the fix touches (it used to say "reading the
  promotional e-mail", contaminating control);
- the STRUCTURAL e-mail delta (the `promo_email` screen + its body copy) appears in
  the TREATMENT stimulus ONLY, never in control.

SCOPE NOTE (single-variable discipline): two other surfaces legitimately carry the
word "e-mail" in BOTH arms and are intentionally NOT asserted on here, because the
fix deliberately leaves them alone (clean single-variable de-confounding):
  - the shared capability NAME ("promotional e-mail campaign"), and
  - the shared `conversion_action` ("click through the e-mail and complete a
    purchase").
Both are arm-symmetric framing of the capability/metric under study (they name what
is being measured, not "you are reading the e-mail right now"), so they do not
contaminate the treatment−control delta the way the old decision_point did. The
assertions below target the two surfaces the fix actually governs.
"""

from __future__ import annotations

import re

from sidira_simulator.cli import _hillstrom_hypothesis_builder
from sidira_simulator.schemas.identity import IdentitySeed
from sidira_simulator.schemas.persona import Persona
from sidira_simulator.services.conversion_elicitor import _conversion_user_turn
from sidira_simulator.services.hillstrom_adapter import (
    EMAIL_BODY_COMPONENT_ID,
    EMAIL_SCREEN_ID,
    build_hillstrom_case,
)
from sidira_simulator.services.hillstrom_archive import HillstromRow
from sidira_simulator.services.prompt_composer import compose_metric_prompt

# Words that name the e-mail / promo touchpoint the treatment arm ADDS. The
# decision-moment line must carry NONE of these (it is shared across arms, so any
# e-mail word there contaminates the No-E-Mail control). Word-boundary matched so
# "e-mail"/"email"/"ad" are caught without false positives on substrings.
_EMAIL_MARKER_RE = re.compile(
    r"\b(e-?mails?|promotional|promo|advert(?:isement)?s?|ads?)\b",
    re.IGNORECASE,
)

# The conversion user turn renders the shared decision moment as this exact line
# (`_conversion_user_turn`: "You're at this moment: {decision_point}"). That line
# is the surgical surface this fix governs.
_DECISION_MOMENT_PREFIX = "You're at this moment:"


def _row(segment: str, *, conversion: int, mens: int = 1, womens: int = 0) -> HillstromRow:
    return HillstromRow(
        recency=1,
        history_segment="1) $0 - $100",
        history=100.0,
        mens=mens,
        womens=womens,
        zip_code="Urban",
        newbie=0,
        channel="Web",
        segment=segment,
        visit=0,
        conversion=conversion,
        spend=0.0,
    )


def _frame() -> list[HillstromRow]:
    rows: list[HillstromRow] = []
    rows += [_row("No E-Mail", conversion=c) for c in (1, 0, 0, 0)]
    rows += [_row("Mens E-Mail", conversion=c) for c in (1, 1, 1, 0)]
    return rows


def _persona() -> Persona:
    return Persona(
        id="p_hillstrom",
        name="Returning Shopper",
        description="A past customer who browses from their inbox.",
        jtbd="Find something worth buying without much effort.",
    )


def _seed() -> IdentitySeed:
    return IdentitySeed(
        age_band="35-44",
        locale_band="urban",
        tenure_band="1-3y",
        current_state="checking messages on the couch",
        recent_gripe="too many notifications lately",
    )


def _full_stimulus(arm: str) -> str:
    """The complete metric stimulus one arm sees: the blinded system prompt
    (structural spec) plus the conversion user turn (which carries the shared
    `decision_point`). This is the exact text the agent is conditioned on."""
    case = build_hillstrom_case(_frame(), "Mens E-Mail", metric_name="conversion", n_resamples=10)
    # The real builder forces the metric + the shared decision_point onto the case.
    hypothesis = _hillstrom_hypothesis_builder("conversion")(case)
    assert hypothesis.decision_point, "the builder must set a decision_point"

    system_prompt, _blinded = compose_metric_prompt(
        customer_id="cust",
        persona=_persona(),
        capability=case.capability,
        hypothesis=hypothesis,
        identity_seed=_seed(),
        arm=arm,  # type: ignore[arg-type]
    )
    user_turn = _conversion_user_turn(
        capability_name=hypothesis.capability_name,
        conversion_action=hypothesis.conversion_action or "buy",
        conversion_action_label=hypothesis.conversion_action_label or "buy now",
        decision_point=hypothesis.decision_point or "",
        options=["buy now", "keep browsing"],
    )
    return system_prompt + "\n" + user_turn


def _decision_moment_line(stimulus: str) -> str:
    """The rendered shared decision moment ("You're at this moment: ...") — the one
    line this fix governs. Fails loud if it is missing so the test can't silently
    pass on a renaming of the prefix."""
    for line in stimulus.splitlines():
        if line.startswith(_DECISION_MOMENT_PREFIX):
            return line
    raise AssertionError(
        f"decision-moment line ({_DECISION_MOMENT_PREFIX!r}) not found in stimulus"
    )


def _treatment_email_body() -> str:
    """The structural e-mail body copy the treatment arm renders (and control must
    not) — read straight off the built case's proposed figma."""
    case = build_hillstrom_case(_frame(), "Mens E-Mail", metric_name="conversion", n_resamples=10)
    email_screen = next(
        s for s in case.hypothesis.proposed_figma.screens if s.id == EMAIL_SCREEN_ID
    )
    body = next(c for c in email_screen.components if c.id == EMAIL_BODY_COMPONENT_ID)
    assert body.text, "the treatment proposed figma must carry e-mail body copy"
    return body.text


# ── the decision_point itself is e-mail-free and arm-neutral ───────────────────


def test_decision_point_is_email_free_and_arm_neutral() -> None:
    """The shared decision_point must NOT name an e-mail/promo/ad — otherwise the
    No-E-Mail control arm is told it is reading the treatment's e-mail."""
    hypothesis = _hillstrom_hypothesis_builder("conversion")(
        build_hillstrom_case(_frame(), "Mens E-Mail", n_resamples=10)
    )
    dp = hypothesis.decision_point or ""
    assert dp, "the conversion builder must set a decision_point"
    assert not _EMAIL_MARKER_RE.search(dp), (
        f"decision_point leaks the treatment e-mail into the shared (both-arm) "
        f"elicitation: {dp!r}"
    )
    # The visit builder shares the same decision_point and must be just as clean.
    visit_dp = _hillstrom_hypothesis_builder("visit")(
        build_hillstrom_case(_frame(), "Mens E-Mail", metric_name="visit", n_resamples=10)
    ).decision_point
    assert visit_dp and not _EMAIL_MARKER_RE.search(visit_dp)


# ── the shared decision moment is e-mail-free in BOTH arms ─────────────────────


def test_decision_moment_line_is_email_free_in_both_arms() -> None:
    """The shared decision-moment line ("You're at this moment: ...") — the surface
    this fix governs — must be e-mail-free in BOTH arms. The old wording put
    "reading the promotional e-mail" here, telling the No-E-Mail control it was
    reading the treatment's e-mail."""
    for arm in ("control", "treatment"):
        line = _decision_moment_line(_full_stimulus(arm))
        leak = _EMAIL_MARKER_RE.search(line)
        assert leak is None, (
            f"the {arm} decision-moment line names {leak.group(0)!r} — the shared "
            f"decision_point is contaminating the arms: {line!r}"
        )


# ── the STRUCTURAL e-mail delta is present in TREATMENT only ───────────────────


def test_email_body_copy_is_in_treatment_stimulus_only() -> None:
    """The treatment e-mail must be conveyed by the STRUCTURAL spec (the `promo_email`
    screen + body copy), present in the treatment stimulus and ABSENT from control —
    proving the e-mail's presence is arm-correct, carried structurally rather than
    leaked into the shared decision moment."""
    body = _treatment_email_body()
    treatment = _full_stimulus("treatment")
    control = _full_stimulus("control")
    assert body in treatment, (
        "the treatment stimulus must render the e-mail body copy (the only thing the "
        "treatment arm adds), but it was not found"
    )
    assert body not in control, (
        "the e-mail body copy leaked into the No-E-Mail control stimulus — control "
        "must render only the inbox screen"
    )
