"""Per-agent identity seed drawing (Phase 2.5, issue #5).

Deterministic, pure: given (persona, sample_index, run_seed) returns the
same IdentitySeed every time, across processes and Python versions.

When a persona has no behavioral_seeds (v1.0 packs), falls back to
_DEFAULT_BEHAVIORAL_SEEDS and emits a structlog WARN once per
(persona_id) pair so the degraded mode is named in logs.
"""

from __future__ import annotations

import hashlib
import random

import structlog

from pythia_simulator.schemas.identity import IdentitySeed
from pythia_simulator.schemas.persona import BehavioralSeedSchema, Persona

log = structlog.get_logger()


_DEFAULT_BEHAVIORAL_SEEDS = BehavioralSeedSchema(
    age_bands=["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
    locale_bands=[
        "urban_us",
        "suburban_us",
        "rural_us",
        "urban_intl",
        "suburban_intl",
    ],
    tenure_bands=[
        "new (<3mo)",
        "early (3-12mo)",
        "established (1-3y)",
        "veteran (3y+)",
    ],
    current_state_pool=[
        "busy weekday evening, looking for something quick",
        "weekend, no rush, browsing options",
        "post-work, tired, decision-fatigued",
        "lunch break at work, time-boxed",
        "late night, comfort-food mood",
        "hosting friends, ordering for a group",
    ],
    recent_gripe_pool=[
        "last order arrived cold",
        "promo code didn't apply at checkout",
        "delivery was 20 minutes later than estimated",
        "favorite restaurant disappeared from the app",
        "fees added up more than expected at checkout",
        "courier left the bag at the wrong door",
    ],
)


_fallback_warned: set[str] = set()


def _seed_rng(persona_id: str, sample_index: int, run_seed: int) -> random.Random:
    """Build a Python-version-stable RNG from (persona_id, sample_index, run_seed).

    Uses sha256 -> first 8 bytes -> big-endian int64 rather than
    random.Random(str), which has implementation-defined string hashing.
    """
    key = f"{persona_id}|{sample_index}|{run_seed}".encode()
    digest = hashlib.sha256(key).digest()
    seed_int = int.from_bytes(digest[:8], "big")
    return random.Random(seed_int)


def _safe_choice(rng: random.Random, pool: list[str]) -> str:
    """Choose from pool; if pool is empty, return '(unknown)' so a half-formed
    section never reaches the prompt (FM-3 mitigation)."""
    if not pool:
        return "(unknown)"
    return rng.choice(pool)


def draw_identity_seed(
    persona: Persona,
    sample_index: int,
    run_seed: int,
) -> IdentitySeed:
    """Deterministically draw an IdentitySeed for one agent within a persona.

    Pure: no I/O beyond the structlog warning for v1.0 fallback.
    `prose` is left as None in v1; LLM synthesis is a follow-up PR.
    """
    schema = persona.behavioral_seeds
    if schema is None:
        if persona.id not in _fallback_warned:
            _fallback_warned.add(persona.id)
            log.warning(
                "identity_seed fallback active - cross-persona variance degraded, upgrade pack to v1.1",
                persona_id=persona.id,
            )
        schema = _DEFAULT_BEHAVIORAL_SEEDS

    rng = _seed_rng(persona.id, sample_index, run_seed)
    return IdentitySeed(
        age_band=_safe_choice(rng, schema.age_bands),
        locale_band=_safe_choice(rng, schema.locale_bands),
        tenure_band=_safe_choice(rng, schema.tenure_bands),
        current_state=_safe_choice(rng, schema.current_state_pool),
        recent_gripe=_safe_choice(rng, schema.recent_gripe_pool),
        prose=None,
    )
