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


# ── agent-behavior-spec §2: behavioral-profile block wiring ──────────────────


def _persona_with_centroid() -> Persona:
    return Persona(
        id="p_centroid",
        name="DashPass Power",
        description="Heavy weekly user who orders for the family.",
        jtbd="Get dinner on the table without thinking about it.",
        centroid_features={
            "order_frequency_z": 1.62,
            "browse_dependency_z": -1.33,
        },
    )


def test_behavioral_profile_block_present_when_centroid_salient() -> None:
    """§2 wiring: a persona with salient centroid_features gains the 'How you
    compare' block, rendered from the previously-unused centroid."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_with_centroid(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    assert "## How you compare" in prompt
    assert "**much higher** order frequency" in prompt
    assert "**much lower** browse dependency" in prompt


def test_behavioral_profile_block_positioned_after_snapshot_before_product() -> None:
    """The block is the layer-4 home: between the behavioral snapshot and the
    product-today section (context-assembly.md §1 stack order)."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_with_centroid(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    snapshot_idx = prompt.index("## Behavioral snapshot")
    profile_idx = prompt.index("## How you compare")
    product_idx = prompt.index("## The product today")
    assert snapshot_idx < profile_idx < product_idx


def test_behavioral_profile_block_absent_without_centroid() -> None:
    """Back-compat: a persona with no centroid_features (v1.0 packs, and the
    pre-§2 default) yields a prompt with no profile block — byte-identical to
    before §2 for that input."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),  # no centroid_features
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    assert "## How you compare" not in prompt


def test_behavioral_profile_block_in_both_arms() -> None:
    """The profile is identity, not change framing, so it must appear in BOTH
    arms — otherwise it would break the #90 pairing invariant (arms differ only
    in task framing)."""
    args = dict(
        customer_id="acme",
        persona=_persona_with_centroid(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    treatment = compose_identity_prompt(**args, arm="treatment")
    control = compose_identity_prompt(**args, arm="control")
    assert "## How you compare" in treatment
    assert "## How you compare" in control


# ── agent-behavior-spec §2 step-2: individual-row tier upgrade (layer 4) ──────


def _persona_v11() -> Persona:
    """A v1.1 persona carrying the individual-row inputs (raw adapted units).

    centroid_features (population z-scores) is present so the centroid tier is
    *available* as a fallback; the v1.1 fields let the composer upgrade to the
    per-agent individual row when a sample_index is supplied. Row 0 diverges
    sharply from the cluster mean; row 1 is an average member.
    """
    p = _persona_with_centroid()
    p.centroid_full = {"order_frequency_28d": 10.0, "browse_dependency": 4.0}
    p.feature_scale = {"order_frequency_28d": 2.0, "browse_dependency": 2.0}
    # Both rows are distinctive (integer-divisible → exact z), so any sample_index
    # renders an individual-row block — the tier-upgrade assertions don't depend on
    # which row a given index happens to select.
    p.sample_rows = [
        {"order_frequency_28d": 16.0, "browse_dependency": 8.0},  # +3.0, +2.0
        {"order_frequency_28d": 4.0, "browse_dependency": 0.0},  # -3.0, -2.0
    ]
    return p


def test_individual_row_block_upgrades_when_sample_index_and_v11_present() -> None:
    """With v1.1 fields and a sample_index, the composer renders the per-agent
    individual-row block ('What's distinctive about you') INSTEAD of the
    persona-vs-population centroid block — the most-individual tier wins."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_v11(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        sample_index=0,
    )
    assert "## What's distinctive about you" in prompt
    assert "**dramatically higher** order frequency 28d" in prompt
    # The two tiers are mutually exclusive — no redundant double "compare" block.
    assert "## How you compare" not in prompt


def test_individual_row_block_degrades_to_centroid_on_v10_pack() -> None:
    """A v1.0 persona (no v1.1 fields) WITH a sample_index falls back to the
    centroid tier — render_individual_row returns nothing, so the composer emits
    'How you compare', never a fabricated individual row."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_with_centroid(),  # centroid only, no v1.1 fields
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        sample_index=0,
    )
    assert "## What's distinctive about you" not in prompt
    assert "## How you compare" in prompt


def test_individual_row_block_absent_without_sample_index() -> None:
    """Even on a v1.1 pack, no sample_index means no per-agent row — the composer
    renders the persona-level centroid tier (back-compat for callers that don't
    thread sample_index)."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_v11(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    assert "## What's distinctive about you" not in prompt
    assert "## How you compare" in prompt


def test_individual_row_block_positioned_after_snapshot_before_product() -> None:
    """The individual-row block occupies the same layer-4 slot as the centroid
    block: between the behavioral snapshot and the product-today section."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_v11(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        sample_index=0,
    )
    snapshot_idx = prompt.index("## Behavioral snapshot")
    row_idx = prompt.index("## What's distinctive about you")
    product_idx = prompt.index("## The product today")
    assert snapshot_idx < row_idx < product_idx


def test_individual_row_block_identical_across_arms_for_same_sample_index() -> None:
    """The #90 paired invariant at the composer level: a treatment agent and its
    control twin share sample_index, so the individual-row block they render is
    byte-identical (the arms differ only in the trailing task framing)."""
    args = dict(
        customer_id="acme",
        persona=_persona_v11(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        sample_index=3,
    )
    treatment = compose_identity_prompt(**args, arm="treatment")
    control = compose_identity_prompt(**args, arm="control")
    marker = "## What's distinctive about you"
    assert marker in treatment and marker in control
    # The identity preamble (through the product-today section) is shared; isolate
    # and compare the individual-row block verbatim across the two arms.
    block_t = treatment.split(marker, 1)[1].split("## The product today", 1)[0]
    block_c = control.split(marker, 1)[1].split("## The product today", 1)[0]
    assert block_t == block_c


def test_individual_row_block_stripped_when_use_persona_false() -> None:
    """The no-persona baseline (#221) strips ALL persona conditioning, including
    the v1.1 individual-row block — a sample_index must not leak persona texture
    into the shadow prompt."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona_v11(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        sample_index=0,
        use_persona=False,
    )
    assert "## What's distinctive about you" not in prompt
    assert "## How you compare" not in prompt


# ── #221 §4.1 persona-lift: use_persona flag ──────────────────────────────


def test_use_persona_true_is_the_default() -> None:
    """Back-compat: pre-#221 callers don't pass `use_persona`. The default must
    be byte-identical to an explicit use_persona=True so existing agents keep
    their persona-conditioned prompt."""
    args = dict(
        customer_id="acme",
        persona=_persona_with_centroid(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    default_prompt = compose_identity_prompt(**args)
    explicit = compose_identity_prompt(**args, use_persona=True)
    assert default_prompt == explicit


def test_no_persona_prompt_drops_all_persona_conditioning() -> None:
    """The no-persona baseline (#221) strips EVERY persona-specific element:
    the name, description, jtbd, the identity-seed 'About you' block, the
    behavioral snapshot, and the §2 behavioral-profile section. Only the
    generic framing + product-today section survive."""
    persona = _persona_with_centroid()
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=persona,
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
        use_persona=False,
    )
    assert persona.name not in prompt
    assert persona.description not in prompt
    assert persona.jtbd not in prompt
    assert "## Who you are" not in prompt
    assert "## About you specifically" not in prompt
    assert "## Behavioral snapshot" not in prompt
    assert "## How you compare" not in prompt
    # The identity-seed details must not leak either.
    assert "commuting home, hungry" not in prompt
    # But it IS still a user of the product, grounded in the current product.
    assert "real user of acme's product" in prompt
    assert "## The product today" in prompt
    assert _capability().reverse_prd in prompt


def test_no_persona_keeps_treatment_task_block_byte_equivalent() -> None:
    """The ONLY difference between a persona agent and its no-persona shadow is
    the presence/absence of persona identity in the preamble — the trailing
    treatment task block (change view + #77 openers) must be byte-identical, so
    the persona-lift comparison isolates persona conditioning alone."""
    args = dict(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        identity_seed=_seed(),
    )
    persona_prompt = compose_identity_prompt(**args, arm="treatment", use_persona=True)
    shadow_prompt = compose_identity_prompt(**args, arm="treatment", use_persona=False)
    # Both end with the same task block; split on the task header and compare
    # the tail verbatim.
    marker = "## Your task"
    assert marker in persona_prompt
    assert marker in shadow_prompt
    assert persona_prompt.split(marker, 1)[1] == shadow_prompt.split(marker, 1)[1]


def test_no_persona_still_sees_the_proposed_change() -> None:
    """The shadow reacts to the SAME proposed change as the persona arm — the
    treatment renderer's change view (and its NOT-changing guard) must be
    present, so any sentiment delta is about persona conditioning, not about a
    different change being shown."""
    prompt = compose_identity_prompt(
        customer_id="acme",
        persona=_persona(),
        capability=_capability(),
        hypothesis=_hypothesis(),
        use_persona=False,
    )
    assert "What's changing" in prompt or "NOT changing" in prompt
