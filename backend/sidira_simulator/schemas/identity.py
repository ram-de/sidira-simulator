"""Per-agent identity-seed types (Phase 2.5).

Drawn deterministically from a persona's BehavioralSeedSchema using
(persona_id, sample_index, run_seed) as RNG seed. Spliced into the agent's
identity prompt so agents within the same persona feel distinct rather
than collapsing to a single LLM-temperature noise band.
"""

from __future__ import annotations

from pydantic import BaseModel


class IdentitySeed(BaseModel):
    """One agent's personal context within its persona."""

    age_band: str
    locale_band: str
    tenure_band: str
    current_state: str
    recent_gripe: str
    prose: str | None = None
