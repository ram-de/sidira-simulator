"""Runtime config helpers shared by API routes and UI config endpoints."""

from __future__ import annotations

import os

DEFAULT_MAX_AGENTS = 50
# #221 distribution elicitation. Defaults reproduce the historical single-reaction,
# temperature=0 path byte-for-byte, so the feature is opt-in via env.
DEFAULT_ELICITATION_SAMPLES = 1
DEFAULT_ELICITATION_TEMPERATURE = 0.0
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
