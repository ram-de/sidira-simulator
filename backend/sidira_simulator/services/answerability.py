"""Pre-flight answerability gate (epic #309, ticket #310 / T1).

A deterministic, **zero-LLM** check run pre-persist in `create_simulation`
(`api/simulations.py`), *before any LLM token is spent*, that ROUTES on a
categorical verdict — it never produces a number and never touches
`confidence_score`. See `sessions/hypothesis-input-quality/analysis.md` for the
full design rationale (the panel's hard constraints are non-negotiable).

T1 implements exactly two checks, both of which catch a one-field-fixable
structural defect that no existing component catches pre-run:

1. **Structurally-invisible change.** A UI-structure / visual change submitted
   as prose only (`proposed_figma is None`) means the agents compare a wireframe
   against a paragraph. → `needs_input`, fix = attach the structured change.

2. **OEC undeclared.** `metric_name is None` → `needs_input` for the
   OEC-declaration prompt, *with an explicit override* ("run as
   generic-reception, not OEC-aligned") so a paying user is never dead-ended.

T1 emits only `answerable` / `needs_input`. `out_of_scope` / abstention is T2
(#311); the ordinal LLM lint is T3 (#312). Neither is built here.

## Classifier choice: cheap pre-flight prose proxy (NOT `render_state_diff`)

The ticket asks to prefer reusing `treatment_renderer`'s deterministic
`prose_only` / reliability-regime classifier. We deliberately use a cheap
pre-flight proxy instead, for two reasons:

- `render_state_diff(capability, hypothesis)` requires a `Capability` — the
  *current* product state from the customer's active Feature Pack. That artifact
  is only loaded inside `orchestrator.prepare`, which is exactly the
  (potentially LLM-spending, R2-reading) work this gate runs *before*. Loading
  the pack here would defeat the "spend nothing on the common cases" goal and
  duplicate the orchestrator's pack-resolution path.

- The one piece of the renderer that *is* available pre-flight — `prose_only` —
  is by construction just `proposed_figma is None` (see
  `render_state_diff`'s early return at treatment_renderer.py:333). The
  reliability *regime* (copy / ui_structure / mechanics / visual) is derived
  from the structural *diff*, which only exists once a figma is present — i.e.
  exactly the case we are NOT blocking. So the renderer cannot tell us, from
  prose alone, whether a *prose-only* change is structural.

The proxy therefore detects UI-structure intent in the prose lexically: if the
prose reads like a layout/structure/visual change AND no `proposed_figma` was
supplied, the agents would be handed a paragraph where a wireframe belongs. This
is a presence check, not a quality score — it is Goodhart-safe (the fix is to
attach the structured change, which is the desired behavior) and it never fires
once a figma is attached, regardless of the prose.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from sidira_simulator.schemas.simulation import Hypothesis

AnswerabilityState = Literal["answerable", "needs_input"]

# Reason codes are stable, machine-readable identifiers the frontend can branch
# on (e.g. to render the "attach a Figma" affordance vs the OEC picker). The
# human-readable text lives in `reasons` / `fixes`.
REASON_STRUCTURALLY_INVISIBLE = "structurally_invisible_change"
REASON_OEC_UNDECLARED = "oec_undeclared"

# Unconditional UI-structure / layout terms. These describe *repositioning the
# layout itself* — they are structural no matter what noun follows, so a wireframe
# is genuinely needed for the agents to read the change. Deliberately does NOT
# include bare UI *nouns* (button, banner, tab…): mentioning a "button" is not by
# itself a structural change ("reword the checkout button label" is copy, not
# layout). Bare nouns only trip the check when paired with an add/remove/move
# action verb (see `_UI_NOUN_TERMS` + `_UI_ACTION_TERMS`). This keeps the block
# set tiny and avoids hard-blocking copy-only changes that merely name an element
# (codex P2 on #310). Word-boundary matched. The list is append-only-with-
# evidence (the panel's "tiny block set" rule).
_UI_STRUCTURE_TERMS: tuple[str, ...] = (
    "move",
    "moves",
    "moved",
    "moving",
    "reorder",
    "reorders",
    "reordered",
    "reordering",
    "rearrange",
    "rearranges",
    "rearranged",
    "rearranging",
    "relocate",
    "relocates",
    "relocated",
    "relocating",
    "resize",
    "resizes",
    "resized",
    "resizing",
    "layout",
    "wireframe",
    "navbar",
    "sidebar",
    "carousel",
)

# Verbs that, combined with a UI noun, signal an add/remove/reposition of an
# on-screen element. "add a button", "remove the tab", "reposition the CTA".
# These add/remove/move actions on a structural element change the layout and so
# need a wireframe; a copy edit that only *names* a button does not.
_UI_ACTION_TERMS: tuple[str, ...] = (
    "add",
    "adds",
    "added",
    "adding",
    "remove",
    "removes",
    "removed",
    "removing",
    "reposition",
    "repositions",
    "repositioned",
    "repositioning",
    "place",
    "places",
    "placed",
    "placing",
)

# UI nouns that, when paired with an action verb, indicate a structural change.
_UI_NOUN_TERMS: tuple[str, ...] = (
    "button",
    "buttons",
    "tab",
    "tabs",
    "menu",
    "menus",
    "modal",
    "banner",
    "screen",
    "screens",
    "field",
    "fields",
    "section",
    "sections",
    "card",
    "cards",
    "cta",
    "icon",
    "icons",
    "toggle",
    "toggles",
    "row",
    "column",
    "panel",
    "widget",
)


def _tokens(prose: str) -> set[str]:
    """Lowercased word tokens of the prose, for word-boundary term matching."""
    return set(re.findall(r"[a-z]+", prose.lower()))


def _reads_as_ui_structure_change(prose: str) -> bool:
    """Cheap lexical proxy: does the prose describe a UI-structure change?

    Fires when the prose contains an unambiguous structure/layout term, OR an
    action verb paired with a UI noun (e.g. "add a reorder button"). Pure and
    deterministic — no LLM, no I/O. Returns False for empty prose.
    """
    toks = _tokens(prose)
    if not toks:
        return False
    if toks & set(_UI_STRUCTURE_TERMS):
        return True
    has_action = bool(toks & set(_UI_ACTION_TERMS))
    has_noun = bool(toks & set(_UI_NOUN_TERMS))
    return has_action and has_noun


@dataclass(frozen=True)
class AnswerabilityVerdict:
    """The categorical pre-flight verdict.

    Carries no number and no persisted scalar — it ROUTES, it does not score
    (panel hard constraint). `reasons` and `fixes` are positionally aligned
    human-readable lists shaped to drop into the refinement-style payload the
    frontend already renders. `reason_codes` are stable machine identifiers so
    the UI can attach the right affordance (Figma upload vs OEC picker).
    `allow_override` is True when the user can proceed anyway (the OEC case):
    structural-invisibility is NOT overridable because there is no faithful way
    to simulate a wireframe described as a paragraph.
    """

    state: AnswerabilityState
    reasons: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
    reason_codes: list[str] = field(default_factory=list)
    allow_override: bool = False


def assess_answerability(
    hypothesis: Hypothesis,
    *,
    allow_generic_reception: bool = False,
) -> AnswerabilityVerdict:
    """Deterministic pre-flight answerability gate (T1).

    Args:
        hypothesis: the PM-supplied change to validate.
        allow_generic_reception: the OEC-undeclared override. When True, an
            undeclared OEC no longer blocks — the run proceeds, labeled
            (by the caller) as generic-reception rather than OEC-aligned. The
            structural-invisibility block has NO override (see
            `AnswerabilityVerdict.allow_override`).

    Returns:
        An `AnswerabilityVerdict`. `needs_input` aggregates every failing check
        so the user fixes them all in one round-trip; `answerable` otherwise.
    """
    reasons: list[str] = []
    fixes: list[str] = []
    reason_codes: list[str] = []
    allow_override = False

    # Check 1 — structurally-invisible change (no override path).
    if hypothesis.proposed_figma is None and _reads_as_ui_structure_change(hypothesis.prose):
        reason_codes.append(REASON_STRUCTURALLY_INVISIBLE)
        reasons.append(
            "This reads as a UI-structure or visual change, but no structured "
            "change (proposed_figma) was attached. Without it the agents compare "
            "a wireframe against a paragraph."
        )
        fixes.append(
            "Attach the structured change (proposed_figma) describing the new "
            "layout, or the agents compare a wireframe to a paragraph."
        )

    # Check 2 — OEC undeclared (overridable: run as generic-reception).
    if hypothesis.metric_name is None and not allow_generic_reception:
        reason_codes.append(REASON_OEC_UNDECLARED)
        reasons.append("No decision metric (OEC) was declared for this hypothesis.")
        fixes.append(
            "Declare the OEC (decision metric) so the run is OEC-aligned, or "
            "resubmit with the override to run as generic-reception (sentiment "
            "only, not OEC-aligned)."
        )
        # Only the OEC defect is overridable. If structural-invisibility is also
        # present the user must still fix that first, so we only advertise the
        # override when OEC is the *sole* blocker.
        allow_override = REASON_STRUCTURALLY_INVISIBLE not in reason_codes

    if reasons:
        return AnswerabilityVerdict(
            state="needs_input",
            reasons=reasons,
            fixes=fixes,
            reason_codes=reason_codes,
            allow_override=allow_override,
        )
    return AnswerabilityVerdict(state="answerable")
