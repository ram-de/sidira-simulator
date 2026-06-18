"""Prompt composition — builds the FROZEN identity_prompt for an AgentInstance.

This is called ONCE per agent, at simulation time. The output is persisted to
R2 as `identity.md` and is never recomputed. See the identity-continuity
guarantee in sidira_simulator/memory/agent_memory.py.

Phase 4.6 #89 adds the `arm` parameter to support A/B mode. The control-arm
prompt drops the proposed-change section and replaces the task framing with a
status-quo reaction prompt. Both arms share the persona/identity_seed/
behavioral_snapshot/product-today preamble AND the #77 opener guidance
(identity-grounded openers + the anti-polite-hedge template list).

agent-behavior-spec §1 wiring (#221/#222): the treatment arm no longer hand-
formats the proposed change as prose. It runs the deterministic treatment
renderer (`render_state_diff`) and embeds its unblinded `state_plus_diff_view`
— a typed changelog plus the mandatory "Explicitly NOT changing" guard, the
cheapest single defense against the inference-confabulation gap (spec §2). This
is the SAME renderer the Tier-0 benchmark (#222) consumes, so the production
agent and the benchmark see byte-identical change framing. Prose-only changes
(no `proposed_figma`) route through the renderer too, so they still get the
NOT-changing guard. The preamble and the #77 opener guidance are unchanged, so
the #90 pairing invariant (treatment and control differ only in task framing)
holds.

agent-behavior-spec §2 wiring (context-assembly.md): the preamble gains a
"How you compare" block between the behavioral snapshot and the product-today
section — the persona's population-relative behavioral profile, rendered from
the previously-unused `Persona.centroid_features` by
`behavioral_profile.render_behavioral_profile`. It is additive (empty string
when the persona has no centroid or nothing salient, so old prompts are
byte-identical) and shared by both arms (it is identity, not change framing), so
the #90 invariant still holds. This is the *segment* reference frame; the
per-agent individual row (layer 4, within-persona variety) is the #7-gated next
touch that plugs into the same renderer.
"""

from __future__ import annotations

from typing import Literal

from sidira_simulator.schemas.feature_pack import Capability
from sidira_simulator.schemas.identity import IdentitySeed
from sidira_simulator.schemas.persona import Persona
from sidira_simulator.services.runtime_config import resolve_elicitation_mode
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.behavioral_profile import (
    render_behavioral_profile,
    render_individual_row,
)
from sidira_simulator.services.treatment_renderer import (
    render_state_diff,
    summarize_reverse_figma,
)

Arm = Literal["treatment", "control"]


# Shared preamble: persona identity + about-you + behavioral snapshot + product-today.
# Both arms see this verbatim — only the trailing task framing differs.
_PREAMBLE_TEMPLATE = """You are roleplaying a real user of {customer_id}'s product.

## Who you are

**{persona_name}**

{persona_description}

{jtbd_section}

{about_you_section}
## Behavioral snapshot

{behavioral_snapshot}

{behavioral_profile_section}## The product today

Below is how the **{capability_name}** capability works on the product right now. This
is the current experience you have as a user — your reactions should be grounded in
this reality.

### PRD (reverse-engineered from the live product)

{reverse_prd}

### Structural spec

{reverse_figma_summary}
"""


# #221 §4.1 persona-lift baseline preamble: a base-LLM user with NO persona
# conditioning. Deliberately drops EVERYTHING persona-specific — the name,
# description, jtbd, the #77 identity_seed "About you" block, the behavioral
# snapshot, and the §2 behavioral-profile section — keeping ONLY the generic
# "you are a user of {customer_id}'s product" framing plus the shared
# "## The product today" section. The trailing task block (treatment framing +
# the deterministic state-diff change view) is appended by the caller VERBATIM,
# byte-identical to the persona arm, so the ONLY difference between a persona
# agent and its no-persona shadow is the presence/absence of persona identity.
# That isolation is what makes persona-lift falsifiable: any sentiment delta
# between the arms is attributable to persona conditioning, not to different
# change framing (the "Funhouse Mirrors" guard — much of an LLM panel's output
# is the base model, not the personas).
_PREAMBLE_TEMPLATE_NO_PERSONA = """You are a real user of {customer_id}'s product.

## The product today

Below is how the **{capability_name}** capability works on the product right now. This
is the current experience you have as a user — your reactions should be grounded in
this reality.

### PRD (reverse-engineered from the live product)

{reverse_prd}

### Structural spec

{reverse_figma_summary}
"""


# Treatment-arm task: react to the PROPOSED change. The change framing
# ({change_view}) is produced by the deterministic treatment renderer
# (services.treatment_renderer.RenderedChange.state_plus_diff_view) — a typed
# changelog plus the mandatory "Explicitly NOT changing" guard — NOT hand-built
# prose. The renderer owns the "## What's changing" header and the NOT-changing
# block; this template only supplies the surrounding task framing + #77 openers.
_TREATMENT_TASK_BLOCK = """{change_view}

## Your task

React to this proposed change as **you** — this specific person, with your behaviors
and motivations. Be honest. If the change wouldn't affect you, say so. If it would
confuse, delight, or frustrate you, say exactly why. Reference specific copy and
flows from the current product when relevant. Do not invent flows you weren't told
about.

### How to open

Your first sentence MUST start from a concrete, in-the-moment detail about YOU:
- What you're doing right now (`current_state` above), OR
- Something that recently went wrong for you (`recent_gripe` above), OR
- The specific role-gated experience you have of this product (guest / member /
  premium_member — pick the one that matches your behavioral snapshot), OR
- A specific number, item, or flow step from the proposed change that lands
  on you first.

Do NOT open with these polite-hedge templates — they make you sound like every
other reviewer and erase what makes you *you*:
- "Honestly, I'm not sure / not thrilled / not too thrilled about..."
- "As someone who [persona summary], I..."
- "I have mixed feelings about..."
- "This is an interesting proposed change, but..."

Open like a real person reacting in the moment — plain, specific, first-person.
Not a balanced review.

When the PM follows up with questions later, answer as the same person — referring
back to what you just said and elaborating on your reasoning.
"""


# Control-arm task: react to the CURRENT product (no proposed change). Same
# anti-template guards from #77 stay applied (codex regression risk: any drift
# here breaks the paired comparison + lets templated hedges back into either
# arm). The opener anchors drop the "specific item from proposed change" bullet
# since there IS no proposed change in this arm; the other three anchors stay.
_CONTROL_TASK_BLOCK = """## Your task

React to the **{capability_name}** capability as it works for you TODAY, as
**you** — this specific person, with your behaviors and motivations. What
works? What frustrates you? What would you want changed?

Be honest. If the current experience works fine for you, say so. If something
specific breaks for you, say exactly what — reference the copy and flows you
actually see. Do not invent flows you weren't told about. Do not speculate
about hypothetical changes — react to the experience as it IS.

### How to open

Your first sentence MUST start from a concrete, in-the-moment detail about YOU:
- What you're doing right now (`current_state` above), OR
- Something that recently went wrong for you (`recent_gripe` above), OR
- The specific role-gated experience you have of this product (guest / member /
  premium_member — pick the one that matches your behavioral snapshot).

Do NOT open with these polite-hedge templates — they make you sound like every
other reviewer and erase what makes you *you*:
- "Honestly, I'm not sure / not thrilled / not too thrilled about..."
- "As someone who [persona summary], I..."
- "I have mixed feelings about..."
- "This is an interesting proposed change, but..."

Open like a real person reacting in the moment — plain, specific, first-person.
Not a balanced review.

When the PM follows up with questions later, answer as the same person — referring
back to what you just said and elaborating on your reasoning.
"""


def compose_identity_prompt(
    customer_id: str,
    persona: Persona,
    capability: Capability,
    hypothesis: Hypothesis,
    identity_seed: IdentitySeed | None = None,
    arm: Arm = "treatment",
    use_persona: bool = True,
    sample_index: int | None = None,
) -> str:
    """Build the frozen system prompt that defines this AgentInstance forever.

    Phase 4.6 #89: `arm` selects which task framing to apply.
    - `arm="treatment"` (default, backwards-compat): agent reacts to the
      proposed change. Unchanged from pre-4.6.
    - `arm="control"`: agent reacts to the current product, no proposed
      change. The `hypothesis` argument is still required for callers that
      hand the same object to both arms, but its prose is NOT injected into
      the control prompt — only `capability_name` is used to name what the
      agent is reacting to.

    #221 §4.1 persona-lift: `use_persona` (default True → byte-identical to
    pre-#221) selects the preamble. When False, the prompt drops ALL persona
    conditioning (name, description, jtbd, the #77 identity_seed block, the
    behavioral snapshot, and the §2 behavioral-profile section) and uses the
    generic `_PREAMBLE_TEMPLATE_NO_PERSONA` — a base-LLM user of the product.
    The trailing task block is appended VERBATIM regardless, so a no-persona
    shadow and its persona twin differ ONLY in the presence of persona
    identity, which is what makes the persona-lift baseline falsifiable. The
    runner pairs the no-persona shadow against the treatment arm, so callers
    that pass `use_persona=False` also pass `arm="treatment"`.

    agent-behavior-spec §2 layer 4: `sample_index` (the agent's per-persona
    index, same value identity_seed is keyed on) selects this agent's individual
    behavioral row when the persona carries Persona Pack v1.1 row inputs,
    rendering its within-cluster deltas in the §2 section (within-persona
    variety). When None — or on a v1.0 pack — the section degrades to the shared
    persona-centroid profile, byte-identical to pre-step-2. Keyed on
    `sample_index` alone (not the arm), so paired treatment/control twins draw
    the same row and the preamble stays byte-identical across arms.

    Identity continuity (memory/agent_memory.py): this output is persisted
    to R2 as `identity.md` and never recomputed. An agent created with
    `arm="control"` STAYS a control agent for all chat replay, even when
    a PM asks follow-ups months later. Re-computing the prompt with a
    different arm would silently change the agent's reality. (No-persona
    shadows are ephemeral and never persisted, so this guarantee is moot
    for them.)
    """
    if use_persona:
        jtbd_section = f"**What you're trying to do:** {persona.jtbd}" if persona.jtbd else ""

        snapshot = persona.behavioral_snapshot
        snapshot_lines = (
            "\n".join(f"- **{k}:** {v}" for k, v in snapshot.items())
            if snapshot
            else "_(no behavioral snapshot available)_"
        )

        preamble = _PREAMBLE_TEMPLATE.format(
            customer_id=customer_id,
            persona_name=persona.name,
            persona_description=persona.description,
            jtbd_section=jtbd_section,
            about_you_section=_about_you_section(identity_seed),
            behavioral_snapshot=snapshot_lines,
            behavioral_profile_section=_behavioral_profile_section(persona, sample_index),
            capability_name=capability.name,
            reverse_prd=capability.reverse_prd,
            reverse_figma_summary=_summarize_figma(capability),
        )
    else:
        preamble = _PREAMBLE_TEMPLATE_NO_PERSONA.format(
            customer_id=customer_id,
            capability_name=capability.name,
            reverse_prd=capability.reverse_prd,
            reverse_figma_summary=_summarize_figma(capability),
        )

    if arm == "treatment":
        # agent-behavior-spec §1: render the proposed change deterministically
        # (typed changelog + mandatory NOT-changing guard) instead of hand-
        # formatting prose. Same renderer the Tier-0 benchmark (#222) consumes,
        # so production and benchmark see byte-identical change framing. The
        # unblinded state_plus_diff_view is correct here: this is the "react to
        # the change / why" task, not the blinded metric-elicitation path (#221).
        rendered = render_state_diff(capability, hypothesis)
        task_block = _TREATMENT_TASK_BLOCK.format(
            change_view=rendered.state_plus_diff_view(),
        )
    else:  # arm == "control"
        task_block = _CONTROL_TASK_BLOCK.format(
            capability_name=capability.name,
        )

    return preamble + "\n" + task_block


# ─── §3a blinded metric-elicitation prompt (#221 / agent-behavior-spec §3a/§3b) ──
#
# The per-metric (conversion) pass MUST be blinded — "the single most important
# framing rule" (spec §3b/§4). The agent sees the state it faces as a *standalone
# product* with NO change framing, so demand characteristics can't inflate the
# TREATMENT arm's propensity specifically; an unblinded metric pass would bias the
# treatment side, and that bias does NOT cancel in the treatment−control delta —
# it corrupts the headline conversion lift. This is a SEPARATE pass from the
# unblinded reaction/identity prompt (`compose_identity_prompt`): the free-text
# reaction still feeds sentiment/chat unblinded; the metric pass is blinded and is
# NOT conditioned on that reaction. This prompt is EPHEMERAL — never persisted as
# `identity.md` — so it carries no frozen-identity obligation.
#
# Both arms render the product as a structural spec ONLY, via the SAME
# `summarize_reverse_figma` renderer (control → the current figma; treatment → the
# proposed figma's `standalone_state_view`). Holding the rendering and the
# PRD-absence constant across arms is deliberate: the proposed state has no clean
# standalone PRD (the proposed PRD is change-authored — "Add a $2 fee…" — and is
# omitted by `standalone_state_view` to keep the pass blinded), so equalizing by
# dropping the current PRD from the metric pass too leaves the ONLY cross-arm
# difference the structural state itself. A PRD-present-vs-absent asymmetry would
# be a confound that does not cancel in the delta. (The reaction/sentiment pass
# still uses the full unblinded PRD — only this metric pass is structural-only.)
#
# Fallback (treatment-rendering-layer.md §5b / §3b open Q2): when no faithful
# standalone view exists (removal / pure-mechanic / prose-only change —
# `has_standalone_view` False), a blinded view would silently show an *unchanged*
# product and miss the treatment entirely. The treatment pass then falls back to
# the unblinded `state_plus_diff_view` and the composer returns `blinded=False`, so
# the caller flags the conversion result low-confidence rather than reporting a
# clean blinded delta.
_METRIC_IDENTITY_BLOCK = """You are roleplaying a real user of {customer_id}'s product.

## Who you are

**{persona_name}**

{persona_description}

{jtbd_section}

{about_you_section}## Behavioral snapshot

{behavioral_snapshot}

{behavioral_profile_section}"""


_METRIC_IDENTITY_BLOCK_NO_PERSONA = """You are a real user of {customer_id}'s product.

"""


# Shared product framing for the metric pass — structural spec only, no "today"
# vs "proposed" language, no change framing. The {structural_spec} body is the
# arm's blinded state, rendered by summarize_reverse_figma in BOTH arms.
_METRIC_PRODUCT_TEMPLATE = """## The product

Below is how the **{capability_name}** capability works on the product you use.
This is your current experience — answer grounded in this reality, judging it on
its own terms.

### Structural spec

{structural_spec}
"""


# ─── #342 expert-forecaster framing (benchmark-validated, opt-in) ────────────────
# The metric pass above is first-person introspective roleplay ("you are a user;
# how would YOU react"). On real randomized ground truth (Hillstrom email RCT,
# Upworthy headline CTR) that framing produced a certified sign inversion — it read
# promotional content as self-reportedly off-putting and predicted emails LOWER
# visits/conversions when the RCT shows they RAISE them. Reframing the SAME pass as
# an expert forecasting how the described AUDIENCE actually behaves (3rd-person,
# population-grounded) removed the inversion (visit direction accuracy 0.0 -> 1.0 at
# power) and certified the who-responds-more heterogeneity claim (visit rank-ρ
# +0.42, p=0.01; gender-match +0.75, p=0.0004). Forecaster is the DEFAULT (#342);
# set SIDIRA_ELICITATION_MODE=roleplay to fall back to the historical introspective
# blocks (the certified baseline, retained for A/B). The option set, blinding
# (structural-only state), and #90 paired
# control/treatment invariant are all preserved — only the framing voice changes,
# symmetrically across arms, so it cancels in the paired delta.
_METRIC_IDENTITY_BLOCK_FORECASTER = """You are an expert at forecasting how real \
audiences behave. Predict how the audience described below actually responds — \
grounded in how real populations behave, NOT in how you personally would react. \
When a question asks how many of 10 "you" would take an action, answer it as a \
forecast: out of 10 representative members of this audience, how many would take \
that action.

## The audience you are forecasting

**{persona_name}**

{persona_description}

{jtbd_section}

{about_you_section}## Behavioral snapshot of this audience

{behavioral_snapshot}

{behavioral_profile_section}"""


_METRIC_IDENTITY_BLOCK_NO_PERSONA_FORECASTER = """You are an expert at forecasting \
how real audiences of {customer_id}'s product behave. Predict how a typical user \
actually responds, grounded in how real populations behave, NOT in how you \
personally would react. When a question asks how many of 10 "you" would take an \
action, answer it as a forecast: out of 10 typical users, how many would.

"""


_METRIC_PRODUCT_TEMPLATE_FORECASTER = """## The product

Below is how the **{capability_name}** capability works on the product this \
audience uses.

### Structural spec

{structural_spec}
"""


def compose_metric_prompt(
    customer_id: str,
    persona: Persona,
    capability: Capability,
    hypothesis: Hypothesis,
    identity_seed: IdentitySeed | None = None,
    arm: Arm = "treatment",
    use_persona: bool = True,
    sample_index: int | None = None,
    elicitation_mode: str | None = None,
) -> tuple[str, bool]:
    """Build the BLINDED system prompt for the §3a metric-elicitation pass (#221).

    Distinct from `compose_identity_prompt` (the unblinded reaction/identity
    prompt persisted as `identity.md`): the metric pass MUST be blinded so demand
    characteristics can't inflate the treatment arm and bias the treatment−control
    delta (agent-behavior-spec §3b/§4 — "the single most important framing rule").
    The agent sees the state it faces as a standalone product, with no "change"
    framing, and is never told a change is under test.

    The persona identity block (who-you-are / about-you / behavioral snapshot /
    behavioral profile) is byte-identical across arms — it is identity, not change
    framing — so the #90 pairing invariant holds for the metric pass too. Only the
    structural state differs: control renders the CURRENT figma, treatment the
    PROPOSED figma's `standalone_state_view`, both via `summarize_reverse_figma`.

    Returns `(prompt, blinded)`. `blinded` is True for control and for treatment
    whenever a faithful standalone view exists. It is False ONLY on the treatment
    fallback (no standalone view — removal / pure-mechanic / prose-only change):
    the pass then uses the unblinded `state_plus_diff_view`, and the caller must
    flag that conversion result low-confidence (treatment-rendering-layer.md §5b /
    §3b Q2). This prompt is EPHEMERAL — never persisted — so the identity-continuity
    guarantee does not apply.
    """
    # #342: select the framing voice. Default (None) resolves the runtime flag;
    # "roleplay" is byte-identical to the historical pass, "forecaster" reframes the
    # SAME blinded/option-set pass as an expert audience forecast.
    mode = elicitation_mode or resolve_elicitation_mode()
    forecaster = mode == "forecaster"
    identity_template = _METRIC_IDENTITY_BLOCK_FORECASTER if forecaster else _METRIC_IDENTITY_BLOCK
    no_persona_template = (
        _METRIC_IDENTITY_BLOCK_NO_PERSONA_FORECASTER if forecaster else _METRIC_IDENTITY_BLOCK_NO_PERSONA
    )
    product_template = _METRIC_PRODUCT_TEMPLATE_FORECASTER if forecaster else _METRIC_PRODUCT_TEMPLATE

    if use_persona:
        jtbd_section = f"**What you're trying to do:** {persona.jtbd}" if persona.jtbd else ""
        snapshot = persona.behavioral_snapshot
        snapshot_lines = (
            "\n".join(f"- **{k}:** {v}" for k, v in snapshot.items())
            if snapshot
            else "_(no behavioral snapshot available)_"
        )
        identity_block = identity_template.format(
            customer_id=customer_id,
            persona_name=persona.name,
            persona_description=persona.description,
            jtbd_section=jtbd_section,
            about_you_section=_about_you_section(identity_seed),
            behavioral_snapshot=snapshot_lines,
            behavioral_profile_section=_behavioral_profile_section(persona, sample_index),
        )
    else:
        identity_block = no_persona_template.format(customer_id=customer_id)

    blinded = True
    if arm == "control":
        # The current product, rendered as a standalone — the agent's real
        # status-quo experience, no change framing.
        product_block = product_template.format(
            capability_name=capability.name,
            structural_spec=summarize_reverse_figma(capability.reverse_figma),
        )
    else:  # arm == "treatment"
        rendered = render_state_diff(capability, hypothesis)
        if rendered.has_standalone_view and rendered.proposed_figma is not None:
            # The PROPOSED state rendered as just-the-product (structural spec
            # only; the change-authored proposed PRD is deliberately omitted to
            # keep the pass blinded). Same renderer/shape as the control arm, so
            # the only cross-arm difference is the structural state itself.
            product_block = product_template.format(
                capability_name=capability.name,
                structural_spec=summarize_reverse_figma(rendered.proposed_figma),
            )
        else:
            # Unblindable fallback: no faithful standalone view (a blinded view
            # would silently show an unchanged product and miss the treatment).
            # Show the current product + the explicit unblinded diff and flag it.
            blinded = False
            product_block = (
                product_template.format(
                    capability_name=capability.name,
                    structural_spec=summarize_reverse_figma(capability.reverse_figma),
                )
                + "\n"
                + rendered.state_plus_diff_view()
            )

    return identity_block + product_block, blinded


def _behavioral_profile_section(persona: Persona, sample_index: int | None = None) -> str:
    """agent-behavior-spec §2: this agent's behavioral-comparison block, rendered
    as salient natural-language deltas (services.behavioral_profile).

    Picks the most *individual* signal available (the SourceTier degradation
    contract), always answering "what is distinctive about THIS agent":

    - **Layer 4 — individual row** (`render_individual_row`): when a `sample_index`
      is supplied AND the persona carries Persona Pack v1.1 row inputs
      (`sample_rows` + `centroid_full` + `feature_scale`), render this agent's
      within-cluster deviation from the persona centroid — UNIQUE per agent, the
      §2 headline that creates within-persona variety.
    - **Centroid fallback** (`render_behavioral_profile`): otherwise (no
      `sample_index`, a v1.0 pack, or an all-typical row) render the persona's
      population-relative profile from `centroid_features` — shared by every agent
      in the persona. This is the pre-step-2 behavior, preserved unchanged.

    Additive and gated on real data: returns "" — so the prompt is byte-identical
    to the no-block case — when neither tier has anything salient. Both arms see
    whatever renders (it is identity, not change framing), and the individual-row
    selection is keyed on `sample_index` alone (not the arm), so the #90 pairing
    invariant — treatment and control preambles differ only in task framing —
    still holds. The trailing blank line keeps the spacing before "## The product
    today" identical to the no-block case.
    """
    if sample_index is not None:
        row_block = render_individual_row(persona, sample_index).render()
        if row_block:
            return f"{row_block}\n\n"
    block = render_behavioral_profile(persona).render()
    return f"{block}\n\n" if block else ""


def _about_you_section(seed: IdentitySeed | None) -> str:
    if seed is None:
        return ""

    def _field(value: str) -> str:
        return value if value else "_(unknown)_"

    return (
        "## About you specifically\n"
        "\n"
        f"- **Age:** {_field(seed.age_band)}\n"
        f"- **Location:** {_field(seed.locale_band)}\n"
        f"- **Time on product:** {_field(seed.tenure_band)}\n"
        f"- **Right now:** {_field(seed.current_state)}\n"
        f"- **Recent friction:** {_field(seed.recent_gripe)}\n"
    )


def _summarize_figma(capability: Capability) -> str:
    """Compact rendering of the reverse-Figma for prompt embedding.

    Delegates to the shared `treatment_renderer.summarize_reverse_figma` so the
    unblinded reaction view and the blinded metric/standalone views stay byte-for-
    byte format-identical — including the gated, transition-graph-derived affordance
    clause (#221/#222). Sharing the one renderer is what keeps the #90 paired
    comparison clean and the affordance rule symmetric across arms.
    """
    return summarize_reverse_figma(capability.reverse_figma)
