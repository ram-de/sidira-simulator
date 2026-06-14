"""Tests for services.prompt_composer (Phase 2.5, issue #5, T3).

Covers the optional `identity_seed` splice: when present, the
"About you specifically" section appears between `## Who you are`
and `## Behavioral snapshot`; when absent, the prompt is unchanged
(back-compat for pre-#5 agents).
"""

from __future__ import annotations

from sidira_simulator.schemas.feature_pack import (
    Capability,
    Component,
    ReverseFigma,
    Screen,
)
from sidira_simulator.schemas.identity import IdentitySeed
from sidira_simulator.schemas.persona import Persona
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.prompt_composer import compose_identity_prompt


def _persona() -> Persona:
    return Persona(
        id="p_test",
        name="DashPass Power",
        description="Heavy weekly user who orders for the family.",
        jtbd="Get dinner on the table without thinking about it.",
    )


def _capability() -> Capability:
    return Capability(
        name="checkout",
        surfaces=["mobile"],
        roles=["consumer"],
        entry_points=["cart"],
        reverse_prd="The checkout screen lets users confirm and pay.",
        reverse_figma=ReverseFigma(),
    )


def _hypothesis() -> Hypothesis:
    return Hypothesis(
        capability_name="checkout",
        prose="Make the tip selector larger and pre-fill 20%.",
    )


def _seed() -> IdentitySeed:
    return IdentitySeed(
        age_band="25-34",
        locale_band="sf_bay",
        tenure_band="3-5y",
        current_state="commuting home, hungry",
        recent_gripe="late delivery last Tuesday",
    )


def test_compose_identity_prompt_includes_about_you_section_when_seed_present() -> None:
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )

    assert "## About you specifically" in prompt
    assert "- **Age:** 25-34" in prompt
    assert "- **Location:** sf_bay" in prompt
    assert "- **Time on product:** 3-5y" in prompt
    assert "- **Right now:** commuting home, hungry" in prompt
    assert "- **Recent friction:** late delivery last Tuesday" in prompt

    # Section ordering: persona identity -> about you -> behavioral snapshot.
    who_idx = prompt.index("## Who you are")
    about_idx = prompt.index("## About you specifically")
    snapshot_idx = prompt.index("## Behavioral snapshot")
    assert who_idx < about_idx < snapshot_idx


def test_compose_identity_prompt_omits_section_when_seed_absent() -> None:
    """Back-compat: pre-#5 callers (and chat replay of old sims) pass no seed."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
    )

    assert "## About you specifically" not in prompt
    # Persona description still present, untouched.
    assert "Heavy weekly user who orders for the family." in prompt
    assert "## Behavioral snapshot" in prompt


def test_compose_identity_prompt_renders_unknown_for_empty_seed_field() -> None:
    """FM-3 mitigation: never emit a half-formed section if a pool was empty."""
    seed = IdentitySeed(
        age_band="25-34",
        locale_band="",
        tenure_band="3-5y",
        current_state="commuting home",
        recent_gripe="late delivery",
    )
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=seed,
    )
    assert "- **Location:** _(unknown)_" in prompt


def test_compose_identity_prompt_includes_opener_guidance() -> None:
    """#77: composed prompt must carry the anti-template opener instructions
    so the LLM stops opening every reaction with "Honestly, I'm not thrilled..."

    Pinned at the prompt-content level; opener-quality behavior in production
    is observed via PM-side calibration thumbs (#56) and Phase 9."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    # Positive instructions present
    assert "How to open" in prompt
    assert "first sentence MUST start from a concrete, in-the-moment detail" in prompt
    # Each of the 4 grounding anchors mentioned by name
    assert "current_state" in prompt
    assert "recent_gripe" in prompt
    # Negative templates explicitly listed so an LLM steering away from one
    # doesn't just pick the next nearest hedge
    assert "Honestly, I'm not" in prompt
    assert "As someone who" in prompt
    assert "mixed feelings" in prompt
    assert "interesting proposed change" in prompt


# ─────────────────────────────────────────────────────────────────────
# Phase 4.6 #89 — control-arm prompt variant
# ─────────────────────────────────────────────────────────────────────


def test_treatment_arm_is_the_default() -> None:
    """Backwards compatibility: pre-#89 callers don't know about `arm` and
    must keep getting the treatment-arm prompt. Pin via byte-equivalence
    against the explicit-treatment call."""
    args = dict(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    default_prompt = compose_identity_prompt(**args)
    explicit_treatment = compose_identity_prompt(**args, arm="treatment")
    assert default_prompt == explicit_treatment


def test_control_arm_omits_proposed_change_section() -> None:
    """#89 Q1 (locked in docs/4.6): control-arm prompt drops the
    `## The proposed change` section entirely. The agent reacts to the
    current product, NOT to a hypothetical change."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        arm="control",
    )
    assert "## The proposed change" not in prompt
    # The hypothesis prose specifically must not appear in the control arm
    # (carrying it through would re-introduce the proposed-change reality
    # the control arm is supposed to be blind to).
    assert _hypothesis().prose not in prompt


def test_control_arm_includes_status_quo_task_framing() -> None:
    """The control arm replaces the treatment task with a status-quo
    framing that prompts the agent to react to TODAY's experience."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        arm="control",
    )
    assert "as it works for you TODAY" in prompt
    # Explicit anti-speculation guard so the LLM doesn't drift into
    # "well if you imagined a change..." in the control arm. Normalize
    # whitespace because the prompt wraps lines.
    normalized = " ".join(prompt.split())
    assert "Do not speculate about hypothetical changes" in normalized


def test_control_arm_preserves_77_anti_template_guards() -> None:
    """Codex regression risk: any change to `prompt_composer.py` can drop
    the #77 anti-templated-opener guards. Both arms MUST keep the same
    "Do NOT open" template list — otherwise the control arm starts
    emitting "Honestly, I'm not too thrilled" again and the lift becomes
    a comparison of templated drift, not real persona reaction."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        arm="control",
    )
    for hedge in (
        "Honestly, I'm not",
        "As someone who",
        "mixed feelings",
        "interesting proposed change",
    ):
        assert hedge in prompt, f"control arm dropped #77 guard for {hedge!r}"


def test_control_arm_drops_proposed_change_opener_anchor() -> None:
    """The treatment arm's 4th opener anchor is 'a specific number, item, or
    flow step from the proposed change.' That doesn't apply to the control
    arm since there IS no proposed change — drop it. The other three anchors
    (current_state / recent_gripe / role-gated experience) stay."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        arm="control",
    )
    # Three anchors that survive
    assert "current_state" in prompt
    assert "recent_gripe" in prompt
    assert "role-gated experience" in prompt
    # The proposed-change anchor is removed
    assert "specific number, item, or flow step from the proposed change" not in prompt


def test_control_arm_keeps_identity_preamble_byte_equivalent() -> None:
    """The persona / about-you / behavioral-snapshot / product-today preamble
    MUST be byte-identical between arms. This is the pairing invariant: the
    only diff between a treatment and control agent's prompt is the task
    framing — everything that defines who the agent IS stays the same.
    Drift here breaks the paired comparison in #90."""
    args = dict(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    treatment = compose_identity_prompt(**args, arm="treatment")
    control = compose_identity_prompt(**args, arm="control")
    # The shared preamble runs from "You are roleplaying" through the
    # "### Structural spec" section. Both prompts must contain this region
    # verbatim.
    shared_start = "You are roleplaying"
    shared_end_marker = "### Structural spec"
    t_start = treatment.find(shared_start)
    t_end = treatment.find(shared_end_marker)
    c_start = control.find(shared_start)
    c_end = control.find(shared_end_marker)
    assert t_start >= 0 and t_end > t_start
    assert c_start >= 0 and c_end > c_start
    # Compare the shared region (preamble through end of "Structural spec"
    # header). The trailing figma summary is included downstream, but the
    # header position alignment is enough to pin "same preamble shape".
    assert treatment[t_start:t_end] == control[c_start:c_end]


def test_control_arm_works_without_identity_seed() -> None:
    """Back-compat: control arm must accept identity_seed=None (single-arm
    sims pre-#5 had no seed; an A/B run against a v1.0 persona pack with
    no behavioral_seeds also produces None)."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=None,
        arm="control",
    )
    # No about-you section, but the control task framing still landed.
    assert "## About you specifically" not in prompt
    assert "as it works for you TODAY" in prompt


# ─────────────────────────────────────────────────────────────────────
# agent-behavior-spec §1 — treatment arm renders via the treatment renderer
# (typed changelog + mandatory NOT-changing guard), not hand-built prose.
# ─────────────────────────────────────────────────────────────────────


def _capability_with_figma() -> Capability:
    """Current state: a cart screen whose CTA reads one way."""
    return Capability(
        name="checkout",
        surfaces=["mobile"],
        roles=["consumer"],
        entry_points=["cart"],
        reverse_prd="The checkout screen lets users confirm and pay.",
        reverse_figma=ReverseFigma(
            screens=[
                Screen(
                    id="cart",
                    name="Cart",
                    components=[Component(id="cta", role="button", text="Tip: choose amount")],
                ),
            ],
        ),
    )


def _hypothesis_with_proposed_figma() -> Hypothesis:
    """Proposed state: same screen, CTA copy changed → one CHANGED copy delta."""
    return Hypothesis(
        capability_name="checkout",
        prose="Pre-fill a 20% tip on the cart CTA.",
        proposed_figma=ReverseFigma(
            screens=[
                Screen(
                    id="cart",
                    name="Cart",
                    components=[Component(id="cta", role="button", text="Tip: 20% pre-filled")],
                ),
            ],
        ),
    )


def test_treatment_arm_renders_typed_changelog_when_proposed_figma_present() -> None:
    """§1 wiring: with a structural delta the treatment arm carries the
    renderer's changelog headers, not the old hand-built `## The proposed
    change` block."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability_with_figma(),
        hypothesis=_hypothesis_with_proposed_figma(),
        identity_seed=_seed(),
    )
    assert "## What's changing" in prompt
    assert "### Concretely" in prompt
    # The CTA copy delta surfaces concretely (old → new copy both named).
    assert "Tip: choose amount" in prompt
    assert "Tip: 20% pre-filled" in prompt
    # The old hand-built header is gone.
    assert "## The proposed change" not in prompt


def test_treatment_arm_always_carries_not_changing_guard() -> None:
    """The mandatory NOT-changing guard (spec §2 defense) is present even for
    a prose-only change with no proposed_figma — exactly the case that most
    needs an explicit boundary against confabulated inference."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),  # prose only, no proposed_figma
        identity_seed=_seed(),
    )
    assert "### Explicitly NOT changing" in prompt
    # Prose-only changes are still labelled as a diff, not silently dropped.
    assert "## What's changing" in prompt
    # The prose itself is carried through the renderer.
    assert _hypothesis().prose in prompt


def test_control_arm_never_sees_renderer_change_framing() -> None:
    """The renderer output is treatment-only: a control agent must not see the
    changelog or the NOT-changing block, even when the hypothesis carries a
    full proposed_figma. Drift here would leak the intervention into the
    control arm and break the #90 paired comparison."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability_with_figma(),
        hypothesis=_hypothesis_with_proposed_figma(),
        identity_seed=_seed(),
        arm="control",
    )
    assert "## What's changing" not in prompt
    assert "### Explicitly NOT changing" not in prompt
    assert "Tip: 20% pre-filled" not in prompt
    assert _hypothesis_with_proposed_figma().prose not in prompt
