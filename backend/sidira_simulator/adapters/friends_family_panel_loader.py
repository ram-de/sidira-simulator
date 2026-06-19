"""Friends-&-Family validation game persona-pack loader — the v1.1 panel.

The F&F validation game's simulated audience is a v1.1 persona pack DERIVED from
the game's pre-treatment Table A (``player_features``) via the sidira-personas
GMM pipeline (``services.friends_family_archive.build_friends_family_panel_pack``).
Like the Hillstrom / Cookie Cats RCT packs it carries the v1.1 quantitative quad
(``centroid_full`` / ``feature_scale`` / ``sample_rows`` / ``posterior_mean``),
so it EXERCISES the ``render_individual_row`` (``individual_row_synthetic``) tier
rather than the centroid fallback.

Unlike the no-LLM Hillstrom / Cookie Cats builds, this pack is built with
``require_llm=True`` so EVERY persona ALSO carries non-null ``behavioral_seeds``
(the five identity-draw pools). That is what keeps the simulator's
``identity_seed.draw_identity_seed`` from logging ``identity_seed fallback
active`` for this pack — the cross-persona texture path fires from real
per-persona pools, not the generic default.

⚠️  The COMMITTED pack (``friends_family_panel_v1.json``) is currently DERIVED
from a SYNTHETIC ``player_features.csv`` (ticket #443) so the data → pack →
loader path is testable before any real player exists. It is statistics (cluster
centroids + privacy-clean GMM draws), not raw rows, so it is safe to commit /
redistribute. When real players have played, the real Table A export replaces the
source and the pack is rebuilt from THAT at run time.

This loader is the F&F mirror of ``hillstrom_panel_loader`` / ``cookiecats_panel_
loader``: it loads + validates the committed pack once (cached) and exposes the
pre-registration metadata a run reports, including whether the pack drives the
v1.1 individual-row tier.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.services.friends_family_archive import FRIENDS_FAMILY_PANEL_VERSION

# The pre-registered panel id (reported as panel_id so a run is traceable to the
# exact population). It IS the PersonaPack.version stamped at build time; sourced
# from the build module so the two can never drift.
FRIENDS_FAMILY_PANEL_ID = FRIENDS_FAMILY_PANEL_VERSION

# The single weight scheme this pack carries. The F&F game has no order / revenue
# signal, so the build runs headcount-only and allocate() defaults to head_count.
FRIENDS_FAMILY_PANEL_WEIGHT_SCHEME = "head_count"

_PANEL_PATH = Path(__file__).with_name("friends_family_panel_v1.json")


@dataclass(frozen=True)
class FriendsFamilyPanelRegistration:
    """Pre-registration metadata an F&F validation run should report.

    Lets a run surface exactly which fixed population it ran against without
    re-deriving anything from the pack body. ``is_individual_row_capable`` is True
    iff EVERY persona carries the v1.1 quad, so the run can assert it exercised the
    individual-row tier rather than the centroid fallback.
    ``is_behavioral_seeds_complete`` is the F&F-specific signal: True iff EVERY
    persona carries non-null ``behavioral_seeds`` (the cross-persona identity
    texture), so a run can assert ``identity_seed`` will NOT fall back to the
    generic default pool for this pack.
    """

    panel_id: str
    version: str
    persona_count: int
    weight_scheme: str
    schema_version: str
    is_synthetic_generic: bool
    is_individual_row_capable: bool
    is_behavioral_seeds_complete: bool


@lru_cache(maxsize=1)
def load_friends_family_panel() -> PersonaPack:
    """Load + validate the committed F&F panel once, then cache it.

    Returns a fully-validated :class:`PersonaPack`. Cached so repeated runs (and
    the accessor below) don't re-parse the bundled JSON.
    """
    return PersonaPack.model_validate_json(_PANEL_PATH.read_text())


def _is_individual_row_capable(pack: PersonaPack) -> bool:
    """True iff every persona carries the v1.1 individual-row inputs.

    ``render_individual_row`` fires (rather than degrading to the centroid tier)
    only when a persona has all of ``sample_rows`` + ``centroid_full`` +
    ``feature_scale``. A single degraded persona flips this to False.
    """
    return all(
        bool(p.sample_rows) and bool(p.centroid_full) and bool(p.feature_scale)
        for p in pack.personas
    )


def _is_behavioral_seeds_complete(pack: PersonaPack) -> bool:
    """True iff every persona carries non-null, non-empty ``behavioral_seeds``.

    When this holds, ``identity_seed.draw_identity_seed`` reads each persona's own
    pools and never logs ``identity_seed fallback active`` — the cross-persona
    texture is real, not the generic default. A persona with ``behavioral_seeds is
    None`` (a no-LLM / v1.0 build) flips this to False.
    """
    return all(
        p.behavioral_seeds is not None
        and any(
            (
                p.behavioral_seeds.age_bands,
                p.behavioral_seeds.locale_bands,
                p.behavioral_seeds.tenure_bands,
                p.behavioral_seeds.current_state_pool,
                p.behavioral_seeds.recent_gripe_pool,
            )
        )
        for p in pack.personas
    )


def friends_family_panel_registration() -> FriendsFamilyPanelRegistration:
    """The pre-registration metadata for the F&F validation panel.

    ``is_synthetic_generic`` is False — this is a measured/derived pack (clustered
    from the game's pre-treatment features), the opposite of a product-agnostic
    starter pack. ``is_individual_row_capable`` and ``is_behavioral_seeds_complete``
    report whether the pack actually drives the v1.1 individual-row tier and the
    per-persona identity pools (no ``identity_seed`` fallback).
    """
    pack = load_friends_family_panel()
    return FriendsFamilyPanelRegistration(
        panel_id=FRIENDS_FAMILY_PANEL_ID,
        version=pack.version,
        persona_count=len(pack.personas),
        weight_scheme=FRIENDS_FAMILY_PANEL_WEIGHT_SCHEME,
        schema_version=pack.schema_version,
        is_synthetic_generic=False,
        is_individual_row_capable=_is_individual_row_capable(pack),
        is_behavioral_seeds_complete=_is_behavioral_seeds_complete(pack),
    )
