"""Runtime config helpers shared by API routes and UI config endpoints."""

from __future__ import annotations

import os

DEFAULT_MAX_AGENTS = 50
# #221 distribution elicitation. Defaults reproduce the historical single-reaction,
# temperature=0 path byte-for-byte, so the feature is opt-in via env.
DEFAULT_ELICITATION_SAMPLES = 1
DEFAULT_ELICITATION_TEMPERATURE = 0.0
# #221 §3e paraphrase ensemble. Default 1 reproduces the historical single-prompt
# conversion pass byte-for-byte (paraphrase index 0 is the canonical wording), so
# the ensemble is opt-in via env — same cost posture as the resampling knob above.
DEFAULT_CONVERSION_PARAPHRASES = 1
# #221/#222 affordance rendering. Default OFF reproduces the historical structural
# render byte-for-byte: an interactive component on a screen with an outbound
# cross-screen transition is shown as a static structural component, with the
# transition listed separately. When ON, the renderer appends a neutral, graph-
# derived affordance clause naming the destination screen(s) so the model can
# connect the component to where it leads (treatment_renderer.summarize_reverse_figma).
# The flag is symmetric across arms and the clause cancels in the paired delta, so
# blinding (compose_metric_prompt) is preserved.
DEFAULT_STIMULUS_AFFORDANCE = False
PRIMARY_ENV_PREFIX = "SIDIRA_"
LEGACY_ENV_PREFIX = "PYTHIA_"


def _non_blank_env(name: str) -> str | None:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return None
    return raw


def resolve_sidira_env(suffix: str, default: str | None = None) -> str | None:
    """Resolve a Sidira env var with legacy Pythia fallback.

    During the pre-launch rename, `SIDIRA_*` is canonical. Existing local and
    deployed `PYTHIA_*` environments keep working until follow-up cleanup.
    Blank values are treated as unset so copied `.env` templates do not mask
    real legacy values.
    """
    primary = _non_blank_env(f"{PRIMARY_ENV_PREFIX}{suffix}")
    if primary is not None:
        return primary
    legacy = _non_blank_env(f"{LEGACY_ENV_PREFIX}{suffix}")
    if legacy is not None:
        return legacy
    return default


def resolve_max_agents_per_simulation() -> int:
    """Resolve the effective simulation cap used by POST /simulations.

    Malformed env values fail open to the default. Non-positive values clamp to
    one so a bad deployment env cannot create zero-agent simulations.
    """
    raw = resolve_sidira_env("MAX_AGENTS", str(DEFAULT_MAX_AGENTS))
    assert raw is not None
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_MAX_AGENTS
    if parsed < 1:
        return 1
    return parsed


def resolve_elicitation_samples() -> int:
    """Number of candidate reactions elicited per agent (#221).

    Default 1 reproduces the historical single-reaction path. Malformed values
    fail open to the default; values < 1 clamp to 1, so a bad env can never
    disable elicitation entirely (an agent with zero reactions has no signal).
    """
    raw = resolve_sidira_env("ELICITATION_SAMPLES", str(DEFAULT_ELICITATION_SAMPLES))
    assert raw is not None
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_ELICITATION_SAMPLES
    return max(1, parsed)


def resolve_conversion_paraphrases() -> int:
    """Number of question paraphrases to ensemble for the conversion metric (#221 §3e).

    Each paraphrase rewords ONLY the elicitation question; the identity and the
    blinded rendered state are held byte-identical, so the ensemble isolates
    prompt-sensitivity, not content variation. The per-agent `p_conv` is the mean
    over the K paraphrases. Default 1 reproduces the historical single-prompt path
    byte-for-byte (paraphrase index 0 is the canonical wording). Malformed values
    fail open to the default; values < 1 clamp to 1, so a bad env can never disable
    the conversion pass entirely. The elicitor caps K to the number of hand-authored
    paraphrases available, so an oversized env can't request a paraphrase that
    doesn't exist.
    """
    raw = resolve_sidira_env("CONVERSION_PARAPHRASES", str(DEFAULT_CONVERSION_PARAPHRASES))
    assert raw is not None
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_CONVERSION_PARAPHRASES
    return max(1, parsed)


def resolve_stimulus_affordance_rendering() -> bool:
    """Whether to render interactive components with their affordance/destination (#221/#222).

    Default False reproduces the historical structural render byte-for-byte. When
    enabled, `treatment_renderer.summarize_reverse_figma` appends a neutral,
    transition-graph-derived affordance clause to a component that lives on a screen
    with an outbound cross-screen transition, naming the destination screen(s). The
    clause states only the navigation MECHANIC ("opens: <screen>"), never intent
    or valence, and is derived purely from the structural transition graph — it
    fires identically for a button, a re-engagement push, a sale banner, or an
    email. The rule is symmetric across arms, so the clause cancels in the paired
    treatment-control delta and blinding is preserved.

    Truthiness mirrors the project convention: "1", "true", "yes", "on" (any case)
    enable it; everything else (including unset, blank, and malformed) is False, so
    a bad deployment env can never silently turn the feature on.
    """
    raw = resolve_sidira_env("STIMULUS_AFFORDANCE")
    if raw is None:
        return DEFAULT_STIMULUS_AFFORDANCE
    return raw.strip().lower() in ("1", "true", "yes", "on")


def resolve_elicitation_temperature() -> float:
    """Sampling temperature for distribution elicitation (#221).

    Default 0.0 reproduces the historical deterministic path. Negative values
    clamp to 0.0; malformed values fail open to the default. No upper clamp here
    — provider-specific ceilings (Anthropic 1.0, OpenAI/Groq 2.0) are enforced by
    the adapter / provider, and clamping to one provider's ceiling would silently
    mis-cap another.
    """
    raw = resolve_sidira_env("ELICITATION_TEMPERATURE", str(DEFAULT_ELICITATION_TEMPERATURE))
    assert raw is not None
    try:
        parsed = float(raw)
    except ValueError:
        return DEFAULT_ELICITATION_TEMPERATURE
    return max(0.0, parsed)
