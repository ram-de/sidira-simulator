"""Treatment-rendering layer — turns (existing state, proposed change) into the
exact structured context an agent reads.

This is the shared-infra piece from the agent-behavior-spec session (spec §1,
`sessions/agent-behavior-spec/treatment-rendering-layer.md`). It is built ONCE
here and consumed identically by:

- production (`prompt_composer.compose_identity_prompt`, the treatment arm), and
- the Tier-0 benchmark harness (#222), via an archive→`Hypothesis` adapter that
  feeds the *same* `render_state_diff` so benchmark inputs and customer PRDs are
  format-identical.

The gap this closes (audited in `prompt_composer.py`): today the treatment arm
injects only `hypothesis.prose` + `proposed_prd` as prose, while the current
state is rendered richly via `_summarize_figma`. `Hypothesis.proposed_figma`
(the *same* `ReverseFigma` type as `capability.reverse_figma`) is dropped on the
floor, so the agent compares a wireframe against a paragraph and must *infer*
the delta — exactly where confabulation enters. This module computes the delta
deterministically (no LLM) and renders it explicitly, including a mandatory
"NOT changing" guard.

It is deliberately pure and side-effect-free so it is trivially unit-testable
and identical across the two call sites. Wiring it into `prompt_composer` is a
separate, higher-blast-radius step (it edits the frozen-identity entry point).

v1 scope (see treatment-rendering-layer.md §7 open questions):
- Emits ADDED / REMOVED / CHANGED reliably. MOVED is best-effort and NOT emitted
  in v1 (positional moves need layout coordinates `ReverseFigma` does not carry);
  a re-routed transition surfaces as REMOVED + ADDED.
- Visual restyle (color / spacing / imagery) is out of `ReverseFigma`'s reach;
  it is declared unsupported, never faked.
- `Component.states` are not diffed in v1 (only top-level `text`); documented.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
    Transition,
)
from sidira_simulator.schemas.simulation import Hypothesis

ChangeKind = Literal["ADDED", "REMOVED", "CHANGED", "MOVED"]
TargetType = Literal["screen", "component", "transition"]
# Reliability modality, ordered weakest→strongest reading regime for agents
# (treatment-rendering-layer.md §3). The *weakest* touched modality sets the
# confidence ceiling on the result card.
Modality = Literal["copy", "ui_structure", "mechanics", "visual"]
Regime = Literal["strong", "mixed", "weak", "unsupported", "unknown"]

# Cap the structural changelog so a PRD touching dozens of components doesn't
# blow up the prompt. Overflow is counted (never silently dropped) and surfaced
# as "+K more minor changes" (open Q2).
_MAX_CHANGES = 40


class StateChange(BaseModel):
    """One typed entry in the structural changelog."""

    model_config = ConfigDict(extra="forbid")

    kind: ChangeKind
    target_type: TargetType
    target_id: str = Field(description="Component/screen id, or transition signature.")
    screen_id: str | None = Field(
        default=None,
        description="Owning screen for component changes; None for screen/transition.",
    )
    modality: Modality
    detail: str = Field(description="Human-readable changelog body (sans KIND prefix).")

    def line(self) -> str:
        """Render as one changelog line: `KIND detail`."""
        return f"{self.kind} {self.detail}"


class RenderedChange(BaseModel):
    """The deterministic output of the treatment renderer.

    Carries two serializations (treatment-rendering-layer.md §5b): a blinded
    `standalone_state_view` (the proposed product as just-the-product, no "what
    changed" framing — fed to blinded behavioral agents for metric elicitation)
    and an unblinded `state_plus_diff_view` (the explicit changelog + NOT-changing
    block — fed to the chat/"why" pass and the scorer, never to a blinded agent).
    """

    model_config = ConfigDict(extra="forbid")

    capability_name: str
    prose: str
    prose_only: bool = Field(
        description="True when no proposed_figma was supplied (no structural diff).",
    )
    changes: list[StateChange] = Field(default_factory=list)
    not_changing: list[str] = Field(default_factory=list)
    touched_modalities: list[Modality] = Field(default_factory=list)
    reliability_regime: Regime
    truncated_count: int = Field(
        default=0,
        description="Structural changes beyond _MAX_CHANGES, counted not dropped.",
    )
    proposed_prd: str | None = None
    # Kept so the standalone view and the §3a choice-set extractor can render the
    # proposed product / its reachable transitions without re-diffing.
    proposed_figma: ReverseFigma | None = None

    @property
    def has_standalone_view(self) -> bool:
        """Whether a blinded standalone-state view can be produced.

        A pure-prose or pure-removal change ("we removed the confirmation step")
        cannot always be rendered as a coherent standalone product state — those
        fall back to the unblinded view + a flag (treatment-rendering-layer.md
        §5b caveat / §3b open Q2).
        """
        return self.proposed_figma is not None

    def standalone_state_view(self) -> str | None:
        """The proposed state rendered as *just the product* — no change framing.

        Returns None when no structural proposed state exists (caller must fall
        back to the unblinded view and flag it).
        """
        if self.proposed_figma is None:
            return None
        body = summarize_reverse_figma(self.proposed_figma)
        prd = f"\n\n### PRD\n\n{self.proposed_prd}" if self.proposed_prd else ""
        return (
            f"### Structural spec\n\n{body}{prd}"
            if body
            else f"_(no structural detail available)_{prd}"
        )

    def state_plus_diff_view(self) -> str:
        """The explicit, unblinded changelog + mandatory NOT-changing guard."""
        lines = [
            "## What's changing",
            "",
            f"The product team is considering: {self.prose}",
            "",
        ]
        if self.proposed_prd:
            lines += ["### Proposed PRD", "", self.proposed_prd, ""]

        if self.changes:
            lines.append("### Concretely")
            lines += [f"  {c.line()}" for c in self.changes]
            if self.truncated_count:
                lines.append(f"  …and {self.truncated_count} more minor changes")
        elif self.prose_only:
            lines.append(
                "_The change is described in prose only; assume everything else " "is unchanged._"
            )
        else:
            # proposed_figma was present but identical to the current state.
            lines.append(
                "_No structural delta detected between the current and proposed "
                "states; the change is described in prose/PRD only._"
            )
        lines.append("")

        # The NOT-changing block is mandatory in every mode — the cheapest single
        # defense against the inference-confabulation gap (§2).
        lines.append("### Explicitly NOT changing")
        if self.not_changing:
            lines += [f"  - {item}" for item in self.not_changing]
        else:
            lines.append("  - everything not listed above is unchanged")
        return "\n".join(lines)

    def choice_set(self, decision_point: str, fallback: list[str] | None = None) -> ChoiceSet:
        """The realistic action set at `decision_point` for the §3a conversion
        question (delegates to :func:`extract_choice_set`)."""
        return extract_choice_set(self, decision_point, fallback)


# ──────────────────────────────────────────────────────────────────────────
# Choice-set extraction (treatment-rendering-layer.md §1.6 step 4 / resolves
# §3a Q3): the conversion question's realistic-alternatives set is the
# transitions reachable from the agent's decision-point screen in the *proposed*
# state. Grounding it in the actual crawled flow (rather than a hand-written
# list) is what keeps the benchmark and production choice sets format-identical.
# ──────────────────────────────────────────────────────────────────────────

# Curated fallback when the crawl yields no transitions out of the decision
# point (thin/partial crawl, prose-only change, or an unknown screen id). The
# `grounded`/`fallback_used` flags let the caller log it so a sparse crawl never
# masquerades as a grounded choice set (elicitation-conversion.md §6 / the
# no-silent-degradation rule shared with §1/§2/§4).
_DEFAULT_FALLBACK_CHOICES = ("convert", "keep_browsing", "comparison_shop", "leave")

# Trigger fragments that already represent abandoning the flow — used so the
# synthetic always-available "leave" sink is not appended twice. Kept narrow on
# purpose: broad fragments like "back" or "close" match ordinary in-flow
# navigation ("back_to_cart", "close_modal"), which would suppress the leave
# sink and understate non-conversion alternatives. When in doubt, append leave —
# a duplicate-ish option is cheaper than omitting the abandon choice entirely.
_LEAVE_MARKERS = ("leave", "exit", "abandon", "quit")


class Choice(BaseModel):
    """One realistic alternative the agent can allocate trials to."""

    model_config = ConfigDict(extra="forbid")

    action: str = Field(description="The trigger / action label the user would take.")
    leads_to: str | None = Field(
        default=None,
        description="Destination screen id; None for the synthetic leave sink "
        "and curated fallback choices.",
    )
    role_gated: list[str] | None = Field(
        default=None,
        description="Roles the underlying transition is gated to (carried so a "
        "downstream filter can drop actions the agent's role can't take); None = open.",
    )
    synthetic: bool = Field(
        default=False,
        description="True for the always-available leave sink and curated fallback "
        "choices (not a crawled transition).",
    )


class ChoiceSet(BaseModel):
    """The realistic-alternatives set fed to the §3a forced-allocation question."""

    model_config = ConfigDict(extra="forbid")

    decision_point: str
    choices: list[Choice] = Field(default_factory=list)
    grounded: bool = Field(
        description="True when choices derive from real crawled transitions; "
        "False when the curated fallback was used.",
    )
    fallback_used: bool = Field(
        description="True when no transition left the decision point and the "
        "curated default set was substituted — caller should log this.",
    )


def _is_leave(action: str) -> bool:
    """Whether an action label already represents abandoning the flow."""
    low = action.lower()
    return any(marker in low for marker in _LEAVE_MARKERS)


def extract_choice_set(
    rendered: RenderedChange,
    decision_point: str,
    fallback: list[str] | None = None,
) -> ChoiceSet:
    """Realistic alternatives at `decision_point` in the *proposed* state.

    Pure and deterministic. The grounded set is every transition leaving
    `decision_point` in `rendered.proposed_figma`, plus a synthetic always-
    available "leave" sink (a real user can abandon at any step — §3a needs a
    non-conversion option). When no transition leaves the decision point (thin
    crawl, prose-only change, or an unknown screen id) the curated `fallback`
    set is substituted and `grounded=False` / `fallback_used=True` are set so the
    caller can log the degradation rather than letting it pass silently.
    """
    fallback_labels = tuple(fallback) if fallback is not None else _DEFAULT_FALLBACK_CHOICES

    figma = rendered.proposed_figma
    reachable: list[Transition] = (
        [t for t in figma.transitions if t.from_screen == decision_point]
        if figma is not None
        else []
    )

    if not reachable:
        return ChoiceSet(
            decision_point=decision_point,
            choices=[Choice(action=a, synthetic=True) for a in fallback_labels],
            grounded=False,
            fallback_used=True,
        )

    choices = [
        Choice(
            action=t.trigger,
            leads_to=t.to_screen,
            role_gated=t.role_gated,
            synthetic=False,
        )
        for t in reachable
    ]
    if not any(_is_leave(c.action) for c in choices):
        choices.append(Choice(action="leave", synthetic=True))

    return ChoiceSet(
        decision_point=decision_point,
        choices=choices,
        grounded=True,
        fallback_used=False,
    )


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────


def render_state_diff(capability: Capability, hypothesis: Hypothesis) -> RenderedChange:
    """Compute the structural diff between the current and proposed states.

    Pure and deterministic — no LLM, no I/O. When `hypothesis.proposed_figma` is
    present it id-matches screens→components and signature-matches transitions to
    emit a typed changelog; when absent it falls back to a prose-only diff that is
    *still labelled as a diff* and still carries the NOT-changing guard.
    """
    current = capability.reverse_figma
    proposed = hypothesis.proposed_figma

    if proposed is None:
        modalities: list[Modality] = ["mechanics"] if hypothesis.proposed_prd else []
        return RenderedChange(
            capability_name=capability.name,
            prose=hypothesis.prose,
            prose_only=True,
            changes=[],
            not_changing=["everything not described in the change above"],
            touched_modalities=modalities,
            reliability_regime=_regime(modalities),
            proposed_prd=hypothesis.proposed_prd,
            proposed_figma=None,
        )

    all_changes: list[StateChange] = []
    all_changes += _diff_screens(current, proposed)
    all_changes += _diff_transitions(current, proposed)

    # Derive the NOT-changing guard and the reliability metadata from the FULL
    # diff, BEFORE truncating the rendered changelog. Truncating first would let
    # a screen whose only change fell past the cap be wrongly listed as "NOT
    # changing", and would overstate the regime if the weakest modality only
    # appears after the cutoff — defeating the safety purpose of this layer.
    modalities = _collect_modalities(all_changes, hypothesis.proposed_prd)
    not_changing = _not_changing(current, proposed, all_changes)

    truncated_count = max(0, len(all_changes) - _MAX_CHANGES)
    changes = all_changes[:_MAX_CHANGES]

    return RenderedChange(
        capability_name=capability.name,
        prose=hypothesis.prose,
        prose_only=False,
        changes=changes,
        not_changing=not_changing,
        touched_modalities=modalities,
        reliability_regime=_regime(modalities),
        truncated_count=truncated_count,
        proposed_prd=hypothesis.proposed_prd,
        proposed_figma=proposed,
    )


# ──────────────────────────────────────────────────────────────────────────
# Diff internals (deterministic; ordered for stable output)
# ──────────────────────────────────────────────────────────────────────────


def _diff_screens(current: ReverseFigma, proposed: ReverseFigma) -> list[StateChange]:
    cur_by_id = {s.id: s for s in current.screens}
    prop_by_id = {s.id: s for s in proposed.screens}
    out: list[StateChange] = []

    # ADDED / REMOVED screens, in proposed order then current order for stability.
    for sid, screen in prop_by_id.items():
        if sid not in cur_by_id:
            out.append(
                StateChange(
                    kind="ADDED",
                    target_type="screen",
                    target_id=sid,
                    modality="ui_structure",
                    detail=f"screen `{sid}` — {screen.name}",
                )
            )
    for sid, screen in cur_by_id.items():
        if sid not in prop_by_id:
            out.append(
                StateChange(
                    kind="REMOVED",
                    target_type="screen",
                    target_id=sid,
                    modality="ui_structure",
                    detail=f"screen `{sid}` — {screen.name}",
                )
            )

    # CHANGED screens: the screen's own prompt-visible fields (name/role), then
    # its components, for screens present in both.
    for sid, prop_screen in prop_by_id.items():
        cur_screen = cur_by_id.get(sid)
        if cur_screen is not None:
            out += _diff_one_screen(cur_screen, prop_screen)
            out += _diff_components(sid, cur_screen, prop_screen)
    return out


def _diff_one_screen(current: Screen, proposed: Screen) -> list[StateChange]:
    """Diff a screen's own fields (name/role) — both are rendered by
    `summarize_reverse_figma`, so a change is prompt-visible and must surface as
    CHANGED rather than letting the screen read as "NOT changing"."""
    out: list[StateChange] = []
    sid = proposed.id

    if current.name != proposed.name:
        out.append(
            StateChange(
                kind="CHANGED",
                target_type="screen",
                target_id=sid,
                modality="copy",
                detail=f"screen `{sid}` — name {_q(current.name)} → {_q(proposed.name)}",
            )
        )

    if (current.role or None) != (proposed.role or None):
        out.append(
            StateChange(
                kind="CHANGED",
                target_type="screen",
                target_id=sid,
                # Screen `role` is an access role (who the screen is for), so it
                # is a mechanics change, like a component's visible_to_roles.
                modality="mechanics",
                detail=f"screen `{sid}` — role {_q(current.role)} → {_q(proposed.role)}",
            )
        )
    return out


def _diff_components(screen_id: str, current: Screen, proposed: Screen) -> list[StateChange]:
    cur_by_id = {c.id: c for c in current.components}
    prop_by_id = {c.id: c for c in proposed.components}
    out: list[StateChange] = []

    for cid, comp in prop_by_id.items():
        if cid not in cur_by_id:
            out.append(
                StateChange(
                    kind="ADDED",
                    target_type="component",
                    target_id=cid,
                    screen_id=screen_id,
                    modality="ui_structure",
                    detail=_component_added_detail(screen_id, comp),
                )
            )
    for cid, comp in cur_by_id.items():
        if cid not in prop_by_id:
            out.append(
                StateChange(
                    kind="REMOVED",
                    target_type="component",
                    target_id=cid,
                    screen_id=screen_id,
                    modality="ui_structure",
                    detail=f"{comp.role} `{cid}` on screen `{screen_id}`",
                )
            )

    for cid, prop_comp in prop_by_id.items():
        cur_comp = cur_by_id.get(cid)
        if cur_comp is not None:
            out += _diff_one_component(screen_id, cur_comp, prop_comp)
    return out


def _diff_one_component(
    screen_id: str, current: Component, proposed: Component
) -> list[StateChange]:
    out: list[StateChange] = []
    cid = proposed.id

    if (current.text or None) != (proposed.text or None):
        out.append(
            StateChange(
                kind="CHANGED",
                target_type="component",
                target_id=cid,
                screen_id=screen_id,
                modality="copy",
                detail=(
                    f"{proposed.role} `{cid}` on screen `{screen_id}` — "
                    f"text {_q(current.text)} → {_q(proposed.text)}"
                ),
            )
        )

    if _norm_roles(current.visible_to_roles) != _norm_roles(proposed.visible_to_roles):
        out.append(
            StateChange(
                kind="CHANGED",
                target_type="component",
                target_id=cid,
                screen_id=screen_id,
                modality="mechanics",
                detail=(
                    f"{proposed.role} `{cid}` on screen `{screen_id}` — visible to "
                    f"{_roles_str(current.visible_to_roles)} → "
                    f"{_roles_str(proposed.visible_to_roles)}"
                ),
            )
        )

    if current.role != proposed.role:
        out.append(
            StateChange(
                kind="CHANGED",
                target_type="component",
                target_id=cid,
                screen_id=screen_id,
                modality="ui_structure",
                detail=(
                    f"`{cid}` on screen `{screen_id}` — role " f"{current.role} → {proposed.role}"
                ),
            )
        )
    return out


def _diff_transitions(current: ReverseFigma, proposed: ReverseFigma) -> list[StateChange]:
    # Transitions carry no id; identity is the (trigger, from, to) signature.
    # A re-routed transition (same trigger+from, different to) surfaces as
    # REMOVED + ADDED in v1 — MOVED detection is deferred (§7 Q1).
    cur_by_sig = {_transition_sig(t): t for t in current.transitions}
    prop_by_sig = {_transition_sig(t): t for t in proposed.transitions}
    out: list[StateChange] = []

    for sig, t in prop_by_sig.items():
        if sig not in cur_by_sig:
            out.append(
                StateChange(
                    kind="ADDED",
                    target_type="transition",
                    target_id=sig,
                    modality="ui_structure",
                    detail=_transition_detail(t),
                )
            )
    for sig, t in cur_by_sig.items():
        if sig not in prop_by_sig:
            out.append(
                StateChange(
                    kind="REMOVED",
                    target_type="transition",
                    target_id=sig,
                    modality="ui_structure",
                    detail=_transition_detail(t),
                )
            )

    # Role-gating change on a transition kept across both states (mechanics).
    for sig, prop_t in prop_by_sig.items():
        cur_t = cur_by_sig.get(sig)
        if cur_t is not None and _norm_roles(cur_t.role_gated) != _norm_roles(prop_t.role_gated):
            out.append(
                StateChange(
                    kind="CHANGED",
                    target_type="transition",
                    target_id=sig,
                    modality="mechanics",
                    detail=(
                        f"transition {prop_t.trigger}: `{prop_t.from_screen}` → "
                        f"`{prop_t.to_screen}` — role-gating "
                        f"{_roles_str(cur_t.role_gated)} → "
                        f"{_roles_str(prop_t.role_gated)}"
                    ),
                )
            )
    return out


def _not_changing(
    current: ReverseFigma, proposed: ReverseFigma, changes: list[StateChange]
) -> list[str]:
    """Screens present in both states with no recorded change, explicitly listed."""
    touched_screens = {c.screen_id for c in changes if c.screen_id is not None}
    touched_screens |= {c.target_id for c in changes if c.target_type == "screen"}
    cur_ids = {s.id for s in current.screens}
    prop_ids = {s.id for s in proposed.screens}
    unchanged = sorted(sid for sid in (cur_ids & prop_ids) if sid not in touched_screens)
    out = [f"screen `{sid}`" for sid in unchanged]
    out.append("everything else not listed above")
    return out


# ──────────────────────────────────────────────────────────────────────────
# Rendering helper (shared with the standalone-state view; mirrors the
# prompt_composer `_summarize_figma` vocabulary so the two are format-identical)
# ──────────────────────────────────────────────────────────────────────────


def summarize_reverse_figma(rf: ReverseFigma) -> str:
    """Compact structural rendering of a ReverseFigma for prompt embedding.

    Byte-compatible with `prompt_composer._summarize_figma`'s output shape so the
    "product today" and the standalone proposed state read identically — the
    symmetry that makes the #90 paired comparison attributable to the change.
    """
    lines: list[str] = []
    for screen in rf.screens:
        role_tag = f" (role: {screen.role})" if screen.role else ""
        lines.append(f"- **Screen `{screen.id}`** — {screen.name}{role_tag}")
        for comp in screen.components:
            visible = (
                f" [visible to: {', '.join(comp.visible_to_roles)}]"
                if comp.visible_to_roles
                else ""
            )
            text = f" — `{comp.text}`" if comp.text else ""
            lines.append(f"    - {comp.role} `{comp.id}`{text}{visible}")
    if rf.transitions:
        lines.append("\nTransitions:")
        for t in rf.transitions:
            gate = f" [role-gated: {', '.join(t.role_gated)}]" if t.role_gated else ""
            lines.append(f"- {t.trigger}: `{t.from_screen}` → `{t.to_screen}`{gate}")
    return "\n".join(lines)


# ──────────────────────────────────────────────────────────────────────────
# Small pure helpers
# ──────────────────────────────────────────────────────────────────────────


def _component_added_detail(screen_id: str, comp: Component) -> str:
    text = f" {_q(comp.text)}" if comp.text else ""
    visible = f" [visible to: {', '.join(comp.visible_to_roles)}]" if comp.visible_to_roles else ""
    return f"{comp.role} `{comp.id}` on screen `{screen_id}`{text}{visible}"


def _transition_sig(t: Transition) -> str:
    return f"{t.trigger}:{t.from_screen}->{t.to_screen}"


def _transition_detail(t: Transition) -> str:
    gate = f" [role-gated: {', '.join(t.role_gated)}]" if t.role_gated else ""
    return f"transition {t.trigger}: `{t.from_screen}` → `{t.to_screen}`{gate}"


def _q(text: str | None) -> str:
    return f'"{text}"' if text else "(none)"


def _norm_roles(roles: list[str] | None) -> tuple[str, ...]:
    return tuple(sorted(roles)) if roles else ()


def _roles_str(roles: list[str] | None) -> str:
    return f"[{', '.join(sorted(roles))}]" if roles else "[all]"


def _collect_modalities(changes: list[StateChange], proposed_prd: str | None) -> list[Modality]:
    order: list[Modality] = ["copy", "ui_structure", "mechanics", "visual"]
    present = {c.modality for c in changes}
    if proposed_prd:
        present.add("mechanics")
    return [m for m in order if m in present]


def _regime(modalities: list[Modality]) -> Regime:
    """Weakest touched modality sets the confidence ceiling (§3 reliability)."""
    if not modalities:
        return "unknown"
    if "visual" in modalities:
        return "unsupported"
    if "ui_structure" in modalities:
        return "weak"
    if "mechanics" in modalities:
        return "mixed"
    if "copy" in modalities:
        return "strong"
    return "unknown"
