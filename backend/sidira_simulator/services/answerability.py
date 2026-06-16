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

The gate emits `answerable` / `needs_input` / `out_of_scope`. The ordinal LLM
lint is T3 (#312) and is NOT built here.

## T2 (#311) — `out_of_scope` instrument-fit detector (deterministic, zero-LLM)

A third, categorical state for OECs that are *fundamentally unresolvable by this
instrument* — a first-exposure, single-session persona panel. Unlike
`needs_input`, `out_of_scope` does **NOT** block the run and does **NOT** 422:
the run proceeds and the score is still computed, but the ship/no-ship verdict is
**categorically WITHHELD** ("NOT ANSWERABLE BY THIS INSTRUMENT") with the named
reasons. This strictly dominates a confidence discount in expected-cost terms for
a Kohavi-class buyer: a tool that says *"I can't resolve this, here's why"* is
more credible than one that always returns a (quietly wrong) number. There is NO
arithmetic discount and NO new persisted scalar — the abstention is categorical
(state + reasons) only, and `confidence_score` is untouched.

Three taxonomy classes are detected lexically over `prose` + `capability_name` +
the metric bundle (taxonomy classes (g) long-horizon and (h) emergent effects):

- **Long-horizon / lifetime outcomes** — revenue, LTV, lifetime value, churn,
  multi-week/month retention, annual/quarterly outcomes. A single-session panel
  observes a first reaction; it cannot observe a 90-day revenue curve.
- **Network / virality / equilibrium effects** — virality, network effects,
  referral loops, market equilibrium, marketplace cannibalization. These are
  population-interaction phenomena; isolated single-agent reactions cannot
  surface them.
- **Novelty-decay / habituation over time** — "novelty wears off", long-term
  habituation. A first-exposure reaction is, by construction, the novelty peak;
  the instrument cannot watch the decay.

The lexicon is deliberately TIGHT and documented (see `_OUT_OF_SCOPE_TERMS` /
`_OUT_OF_SCOPE_PHRASES` below). Over-triggering is worse than a miss here: a
false abstention erodes trust ("the tool refused a question it could have
answered"), so each token must name an outcome the instrument provably cannot
resolve, never a topic that merely *mentions* time or growth.

NOTE — `retention` as a declared `metric_name` is NOT auto-out-of-scope. The
single-session retention elicitor (#275) measures a *return-intent* proxy at the
session's end, which the instrument can resolve; only retention framed over a
*multi-week / lifetime horizon in the prose* is out of scope.

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

AnswerabilityState = Literal["answerable", "needs_input", "out_of_scope"]

# Reason codes are stable, machine-readable identifiers the frontend can branch
# on (e.g. to render the "attach a Figma" affordance vs the OEC picker). The
# human-readable text lives in `reasons` / `fixes`.
REASON_STRUCTURALLY_INVISIBLE = "structurally_invisible_change"
REASON_OEC_UNDECLARED = "oec_undeclared"

# T2 (#311) out-of-scope reason codes — one per detected instrument-fit class.
REASON_OUT_OF_SCOPE_LONG_HORIZON = "out_of_scope_long_horizon"
REASON_OUT_OF_SCOPE_NETWORK_EFFECT = "out_of_scope_network_effect"
REASON_OUT_OF_SCOPE_NOVELTY_DECAY = "out_of_scope_novelty_decay"

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


# ── T2 (#311) instrument-fit lexicon ────────────────────────────────────────
# Each entry names an OUTCOME a first-exposure, single-session panel provably
# cannot resolve. Word-boundary matched against the token set; deliberately
# tight (see module docstring — false abstention is the costlier error).
#
# Class (g) — long-horizon / lifetime outcomes. Single tokens that, on their own,
# denote an outcome measured over time/money the instrument never observes.
_LONG_HORIZON_TERMS: tuple[str, ...] = (
    "revenue",
    "ltv",
    "arpu",
    "arr",
    "mrr",
    "churn",
    # NB: bare "lifetime" is deliberately NOT a token (codex P2 #311) — it
    # false-abstains on in-scope copy like "lifetime warranty" / "lifetime
    # access". The genuine long-horizon outcome is caught by the phrases
    # "lifetime value" / "customer lifetime" below.
)
# Multi-word long-horizon phrases (substring matched on normalized prose) — these
# need the adjacency to be unambiguous (e.g. "lifetime value", "90-day revenue").
_LONG_HORIZON_PHRASES: tuple[str, ...] = (
    "lifetime value",
    "customer lifetime",
    "long-term retention",
    "long term retention",
    "annual retention",
    "annual revenue",
    "quarterly revenue",
    "multi-week retention",
    "multi week retention",
    "multi-month retention",
    "multi month retention",
)
# Numeric multi-period horizons paired with retention/revenue — matched by regex
# so spacing/hyphenation variants ("90-day retention", "90 day retention",
# "30day revenue") all trip the same trigger instead of enumerating each form
# (codex P2 #311). Requires an explicit count + period unit + retention/revenue
# so a bare "retention" (a single-session return-intent proxy) is NOT caught.
_LONG_HORIZON_NUMERIC = re.compile(
    r"\b\d+\s*-?\s*(?:day|days|week|weeks|month|months|year|years)\s+"
    r"(?:retention|revenue)\b"
)

# Class (h) — network / virality / equilibrium effects. Population-interaction
# phenomena that isolated single-agent reactions cannot surface.
_NETWORK_EFFECT_TERMS: tuple[str, ...] = (
    "virality",
    "viral",
    "virally",
)
_NETWORK_EFFECT_PHRASES: tuple[str, ...] = (
    "network effect",
    "network effects",
    "referral loop",
    "referral loops",
    "viral loop",
    "viral coefficient",
    "market equilibrium",
    "marketplace equilibrium",
    "cannibalization across the marketplace",
    "marketplace cannibalization",
    "cross-side network",
    "two-sided market",
    "two sided market",
)

# Class (h) — novelty-decay / habituation over time. A first-exposure reaction is
# the novelty peak by construction; the instrument cannot watch the decay.
_NOVELTY_DECAY_PHRASES: tuple[str, ...] = (
    "novelty wears off",
    "novelty wear off",
    "novelty effect",
    "novelty decay",
    "long-term habituation",
    "long term habituation",
    "wears off over time",
    "wear off over time",
)


def _normalized(text: str) -> str:
    """Lowercased, single-spaced prose for substring phrase matching."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _detect_out_of_scope(hypothesis: Hypothesis) -> tuple[list[str], list[str]]:
    """Deterministic instrument-fit detector (T2 / #311).

    Pure and zero-LLM. Scans the OEC surface for outcomes a first-exposure
    single-session panel cannot resolve, at two sensitivities: bare single-token
    signals (revenue, churn, viral) only against the outcome-describing fields
    (`prose` + `decision_point`), and the unambiguous multi-word phrases +
    numeric-horizon regex against all fields including the product-area labels
    (`capability_name` / `conversion_action` / `conversion_action_label`). This
    avoids false-abstaining on an in-scope run whose product area merely happens
    to be named e.g. "Revenue dashboard". Returns `(reason_codes, reasons)`
    positionally aligned; both empty when the OEC is within resolving power.

    Each class fires at most once (de-duplicated) so a prose that says
    "revenue" twice doesn't double-report. The detector NEVER inspects
    `confidence_score` and produces no number — it is a categorical signal only.
    """
    # Two surfaces, scanned at different sensitivities (codex P2 #311):
    #   • OUTCOME text — `prose` + `decision_point` — genuinely describes the OEC
    #     and the moment it's measured, so bare single-token signals (revenue,
    #     churn, viral) are meaningful here.
    #   • LABEL text — `capability_name` + the conversion action labels — names a
    #     product area / action, NOT the outcome horizon. A "Revenue dashboard"
    #     capability measured by CTR is in-scope; matching the bare token there
    #     would false-abstain (the costlier error). So labels only contribute the
    #     unambiguous MULTI-WORD phrases + the numeric-horizon regex, which carry
    #     their own horizon context.
    outcome_blob = _normalized(
        " ".join(f for f in (hypothesis.prose, hypothesis.decision_point) if f)
    )
    full_blob = _normalized(
        " ".join(
            f
            for f in (
                hypothesis.prose,
                hypothesis.capability_name,
                hypothesis.conversion_action,
                hypothesis.conversion_action_label,
                hypothesis.decision_point,
            )
            if f
        )
    )
    outcome_toks = set(re.findall(r"[a-z]+", outcome_blob))

    # When the PM has DECLARED an explicitly-immediate first-session OEC
    # (metric_name conversion / ctr), defer to it for the BARE single-token
    # signals (codex P2 #311): prose often repeats a product-area name ("the
    # Revenue dashboard") that is the surface, not the outcome. The unambiguous
    # multi-word phrases + numeric-horizon regex still fire — "lift 90-day
    # revenue" / "lifetime value" state a horizon outright and override even a
    # declared immediate metric. (retention is NOT immediate-declared here: it's
    # the session-end return-intent proxy, already handled by horizon phrases.)
    declared_immediate = hypothesis.metric_name in ("conversion", "ctr")

    reason_codes: list[str] = []
    reasons: list[str] = []

    long_horizon_phrase = any(p in full_blob for p in _LONG_HORIZON_PHRASES) or bool(
        _LONG_HORIZON_NUMERIC.search(full_blob)
    )
    long_horizon_token = bool(outcome_toks & set(_LONG_HORIZON_TERMS))
    long_horizon = long_horizon_phrase or (
        long_horizon_token and not declared_immediate
    )
    if long_horizon:
        reason_codes.append(REASON_OUT_OF_SCOPE_LONG_HORIZON)
        reasons.append(
            "The OEC is a long-horizon / lifetime outcome (e.g. revenue, LTV, "
            "or multi-week retention). A first-exposure, single-session panel "
            "observes an initial reaction — it cannot observe an outcome that "
            "accrues over days, weeks, or the customer lifetime."
        )

    network_phrase = any(p in full_blob for p in _NETWORK_EFFECT_PHRASES)
    network_token = bool(outcome_toks & set(_NETWORK_EFFECT_TERMS))
    network = network_phrase or (network_token and not declared_immediate)
    if network:
        reason_codes.append(REASON_OUT_OF_SCOPE_NETWORK_EFFECT)
        reasons.append(
            "The OEC depends on network / virality / equilibrium effects. These "
            "are population-interaction phenomena; isolated single-agent "
            "reactions cannot surface how the change propagates across users or "
            "shifts a market equilibrium."
        )

    novelty = any(p in full_blob for p in _NOVELTY_DECAY_PHRASES)
    if novelty:
        reason_codes.append(REASON_OUT_OF_SCOPE_NOVELTY_DECAY)
        reasons.append(
            "The OEC is about novelty decay / habituation over time. A "
            "first-exposure reaction is the novelty peak by construction; the "
            "instrument cannot watch the effect wear off across repeat sessions."
        )

    return reason_codes, reasons


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

    For `out_of_scope` (T2 / #311) the run proceeds with NO override needed and
    NO fixes (the OEC is structurally beyond a single-session panel); `reasons`
    + `reason_codes` carry the named instrument-fit failures and the verdict is
    withheld at result time ("NOT ANSWERABLE BY THIS INSTRUMENT").
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
        An `AnswerabilityVerdict`. `needs_input` aggregates every failing
        structural check so the user fixes them all in one round-trip;
        `out_of_scope` (T2 / #311) when the OEC is unresolvable by this
        instrument; `answerable` otherwise.

    State precedence: `needs_input` > `out_of_scope` > `answerable`. A blocking
    structural defect (`needs_input`) must be fixed before the run can proceed at
    all, so it is reported first — there is no point abstaining on a run that
    won't start. Once the structural checks pass, an out-of-scope OEC routes to
    ABSTAIN (the run proceeds; the verdict is withheld at result time).
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

    # T2 (#311) — instrument-fit. Only reached once the structural checks pass.
    # ABSTAIN does not block: the run proceeds and the verdict is withheld at
    # result time. No fixes (there is no one-field fix — the OEC is structurally
    # beyond a single-session panel), no override (the run already proceeds).
    oos_codes, oos_reasons = _detect_out_of_scope(hypothesis)
    if oos_codes:
        return AnswerabilityVerdict(
            state="out_of_scope",
            reasons=oos_reasons,
            reason_codes=oos_codes,
        )

    return AnswerabilityVerdict(state="answerable")
