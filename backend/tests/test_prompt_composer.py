"""Tests for services.prompt_composer (Phase 2.5, issue #5, T3).

Covers the optional `identity_seed` splice: when present, the
"About you specifically" section appears between `## Who you are`
and `## Behavioral snapshot`; when absent, the prompt is unchanged
(back-compat for pre-#5 agents).
"""

from __future__ import annotations

from pythia_simulator.schemas.feature_pack import Capability, ReverseFigma
from pythia_simulator.schemas.identity import IdentitySeed
from pythia_simulator.schemas.persona import Persona
from pythia_simulator.schemas.simulation import Hypothesis
from pythia_simulator.services.prompt_composer import compose_identity_prompt


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
