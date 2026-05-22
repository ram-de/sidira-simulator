"""Prompt composition — builds the FROZEN identity_prompt for an AgentInstance.

This is called ONCE per agent, at simulation time. The output is persisted to
R2 as `identity.md` and is never recomputed. See the identity-continuity
guarantee in pythia_simulator/memory/agent_memory.py.
"""

from __future__ import annotations

from pythia_simulator.schemas.feature_pack import Capability
from pythia_simulator.schemas.identity import IdentitySeed
from pythia_simulator.schemas.persona import Persona
from pythia_simulator.schemas.simulation import Hypothesis


_TEMPLATE = """You are roleplaying a real user of {customer_id}'s product.

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

## The proposed change

The product team is considering this change:

{hypothesis_prose}

{proposed_prd_section}

## Your task

React to this proposed change as **you** — this specific person, with your behaviors
and motivations. Be honest. If the change wouldn't affect you, say so. If it would
confuse, delight, or frustrate you, say exactly why. Reference specific copy and
flows from the current product when relevant. Do not invent flows you weren't told
about.

When the PM follows up with questions later, answer as the same person — referring
back to what you just said and elaborating on your reasoning.
"""


def compose_identity_prompt(
    customer_id: str,
    persona: Persona,
    capability: Capability,
    hypothesis: Hypothesis,
    identity_seed: IdentitySeed | None = None,
) -> str:
    """Build the frozen system prompt that defines this AgentInstance forever."""
    jtbd_section = f"**What you're trying to do:** {persona.jtbd}" if persona.jtbd else ""

    snapshot = persona.behavioral_snapshot
    snapshot_lines = (
        "\n".join(f"- **{k}:** {v}" for k, v in snapshot.items())
        if snapshot
        else "_(no behavioral snapshot available)_"
    )

    proposed_prd_section = (
        f"### Proposed PRD\n\n{hypothesis.proposed_prd}" if hypothesis.proposed_prd else ""
    )

    return _TEMPLATE.format(
        customer_id=customer_id,
        persona_name=persona.name,
        persona_description=persona.description,
        jtbd_section=jtbd_section,
        about_you_section=_about_you_section(identity_seed),
        behavioral_snapshot=snapshot_lines,
        capability_name=capability.name,
        reverse_prd=capability.reverse_prd,
        reverse_figma_summary=_summarize_figma(capability),
        hypothesis_prose=hypothesis.prose,
        proposed_prd_section=proposed_prd_section,
    )


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
