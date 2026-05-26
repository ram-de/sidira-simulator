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


# Per-persona overrides for the 6 demo personas (#78 stopgap).
#
# Why this exists: the v1.0 persona pack doesn't emit per-persona
# `behavioral_seeds`, so identity_seed falls through to
# _DEFAULT_BEHAVIORAL_SEEDS. The default pools are broad — they include
# `tenure_band = "veteran (3y+)"`, which can land on a "New explorer (first
# 60 days)" persona and produce a visibly contradictory agent. Until the
# pythia-personas v1.1 work emits per-persona pools, this table constrains
# the demo personas to coherent draws. Each entry is a partial schema:
# fields not listed here fall through to the default pool.
#
# **This is a stopgap.** Delete when v1.1 packs ship.
# Each constraint is grounded in the persona description in
# local-artifacts/customers/demo/personas/v_1/persona_pack.json — don't
# tweak without re-reading the persona prose.
_PERSONA_OVERRIDES: dict[str, dict[str, list[str]]] = {
    "maya_late_night_premium": {
        # "32-year-old DashPass subscriber" → established/veteran tenure,
        # 25-34 age band. "Orders 3-4 times a week between 9pm and 1am" →
        # late-night state dominates.
        "age_bands": ["25-34"],
        "tenure_bands": ["established (1-3y)", "veteran (3y+)"],
        "current_state_pool": [
            "late night, comfort-food mood",
            "post-work, tired, decision-fatigued",
        ],
    },
    "dom_promo_driven_restaurant": {
        # "28-year-old member... 14 months" → 25-34 age band. 14 months IS
        # `established (1-3y)`, NOT `early (3-12mo)` — fixed per codex #79 P1.
        # Promo-driven → fee/promo gripes resonate.
        "age_bands": ["25-34"],
        "tenure_bands": ["established (1-3y)"],
        "recent_gripe_pool": [
            "fees added up more than expected at checkout",
            "promo code didn't apply at checkout",
            "favorite restaurant disappeared from the app",
        ],
    },
    "priya_grocery_stockup": {
        # "36-year-old DashPass subscriber, one large grocery order most
        # weeks" → 35-44 age band. Prose doesn't quantify tenure; she could
        # be a DashPass convert at any tenure ≥ early. Codex #79 P2: don't
        # narrow more than the prose justifies. Two-kids household →
        # group-order states. Grocery-side gripes (cold, wrong door).
        "age_bands": ["35-44"],
        "tenure_bands": ["early (3-12mo)", "established (1-3y)", "veteran (3y+)"],
        "current_state_pool": [
            "hosting friends, ordering for a group",
            "weekend, no rush, browsing options",
        ],
        "recent_gripe_pool": [
            "last order arrived cold",
            "courier left the bag at the wrong door",
            "favorite restaurant disappeared from the app",
        ],
    },
    "lex_new_explorer": {
        # "24-year-old who signed up six weeks ago" → 18-24 age, NEW tenure
        # ONLY (this was the original contradiction case in #78).
        "age_bands": ["18-24"],
        "tenure_bands": ["new (<3mo)"],
        # Browsing-mode states fit a new user discovering the product.
        "current_state_pool": [
            "weekend, no rush, browsing options",
            "busy weekday evening, looking for something quick",
            "late night, comfort-food mood",
        ],
    },
    "jordan_lapsing_disengaged": {
        # "41-year-old who was active a year ago" → 35-44 age, has been on
        # the platform for more than a year so established at minimum.
        "age_bands": ["35-44"],
        "tenure_bands": ["established (1-3y)", "veteran (3y+)"],
        # Lapsing → fatigue/decision-fatigue states are thematically right.
        "current_state_pool": [
            "post-work, tired, decision-fatigued",
            "weekend, no rush, browsing options",
        ],
    },
    "sam_speed_pragmatist": {
        # "30-year-old member, orders 2-3 times a week, usually lunch
        # within a fifteen-minute window" → 25-34 age, lunch-break state
        # dominates. Codex #79 P2: prose is silent on tenure ("a member"
        # could be any duration), so DON'T narrow out veteran. Heavy
        # repeat behavior is consistent with any tenure ≥ early.
        # Speed-sensitive → late-delivery gripe is the natural one.
        "age_bands": ["25-34"],
        "tenure_bands": ["early (3-12mo)", "established (1-3y)", "veteran (3y+)"],
        "current_state_pool": [
            "lunch break at work, time-boxed",
            "busy weekday evening, looking for something quick",
        ],
        "recent_gripe_pool": [
            "delivery was 20 minutes later than estimated",
            "courier left the bag at the wrong door",
        ],
    },
}


def _schema_with_overrides(persona_id: str, base: BehavioralSeedSchema) -> BehavioralSeedSchema:
    """Return a copy of `base` with any per-persona overrides for `persona_id`
    applied. Fields not in the override pass through unchanged."""
    overrides = _PERSONA_OVERRIDES.get(persona_id)
    if not overrides:
        return base
    return BehavioralSeedSchema(
        age_bands=overrides.get("age_bands", base.age_bands),
        locale_bands=overrides.get("locale_bands", base.locale_bands),
        tenure_bands=overrides.get("tenure_bands", base.tenure_bands),
        current_state_pool=overrides.get(
            "current_state_pool", base.current_state_pool
        ),
        recent_gripe_pool=overrides.get(
            "recent_gripe_pool", base.recent_gripe_pool
        ),
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

    # #78 stopgap: when the pack didn't supply per-persona constraints,
    # narrow the default pools per-persona so a "New explorer" can't be
    # handed `tenure_band = "veteran (3y+)"`. Pack-supplied schemas pass
    # through untouched.
    if persona.behavioral_seeds is None:
        schema = _schema_with_overrides(persona.id, schema)

    rng = _seed_rng(persona.id, sample_index, run_seed)
    return IdentitySeed(
        age_band=_safe_choice(rng, schema.age_bands),
        locale_band=_safe_choice(rng, schema.locale_bands),
        tenure_band=_safe_choice(rng, schema.tenure_bands),
        current_state=_safe_choice(rng, schema.current_state_pool),
        recent_gripe=_safe_choice(rng, schema.recent_gripe_pool),
        prose=None,
    )
