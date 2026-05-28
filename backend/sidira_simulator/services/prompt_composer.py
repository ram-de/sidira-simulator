"""Prompt composition — builds the FROZEN identity_prompt for an AgentInstance.

This is called ONCE per agent, at simulation time. The output is persisted to
R2 as `identity.md` and is never recomputed. See the identity-continuity
guarantee in sidira_simulator/memory/agent_memory.py.

Phase 4.6 #89 adds the `arm` parameter to support A/B mode. The treatment-arm
prompt is unchanged from the single-arm/pre-4.6 shape. The control-arm prompt
drops the proposed-change section and replaces the task framing with a
status-quo reaction prompt. Both arms share the persona/identity_seed/
behavioral_snapshot/product-today preamble AND the #77 opener guidance
(identity-grounded openers + the anti-polite-hedge template list).
"""

from __future__ import annotations

from typing import Literal

from sidira_simulator.schemas.feature_pack import Capability
from sidira_simulator.schemas.identity import IdentitySeed
from sidira_simulator.schemas.persona import Persona
from sidira_simulator.schemas.simulation import Hypothesis

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

## The product today

Below is how the **{capability_name}** capability works on the product right now. This
is the current experience you have as a user — your reactions should be grounded in
this reality.

### PRD (reverse-engineered from the live product)

{reverse_prd}

### Structural spec

{reverse_figma_summary}
"""


# Treatment-arm task: react to the PROPOSED change. Unchanged from pre-4.6.
_TREATMENT_TASK_BLOCK = """## The proposed change

The product team is considering this change:

{hypothesis_prose}

{proposed_prd_section}

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

    Identity continuity (memory/agent_memory.py): this output is persisted
    to R2 as `identity.md` and never recomputed. An agent created with
    `arm="control"` STAYS a control agent for all chat replay, even when
    a PM asks follow-ups months later. Re-computing the prompt with a
    different arm would silently change the agent's reality.
    """
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
        capability_name=capability.name,
        reverse_prd=capability.reverse_prd,
        reverse_figma_summary=_summarize_figma(capability),
    )

    if arm == "treatment":
        proposed_prd_section = (
            f"### Proposed PRD\n\n{hypothesis.proposed_prd}" if hypothesis.proposed_prd else ""
        )
        task_block = _TREATMENT_TASK_BLOCK.format(
            hypothesis_prose=hypothesis.prose,
            proposed_prd_section=proposed_prd_section,
        )
    else:  # arm == "control"
        task_block = _CONTROL_TASK_BLOCK.format(
            capability_name=capability.name,
        )

    return preamble + "\n" + task_block


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
    """Compact rendering of the reverse-Figma for prompt embedding."""
    lines = []
    for screen in capability.reverse_figma.screens:
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
    if capability.reverse_figma.transitions:
        lines.append("\nTransitions:")
        for t in capability.reverse_figma.transitions:
            gate = f" [role-gated: {', '.join(t.role_gated)}]" if t.role_gated else ""
            lines.append(f"- {t.trigger}: `{t.from_screen}` → `{t.to_screen}`{gate}")
    return "\n".join(lines)
