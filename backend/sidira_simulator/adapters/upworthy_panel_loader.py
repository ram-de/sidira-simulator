"""Upworthy Tier-0 panel loader — the pre-registered general-US-news audience.

For the Upworthy CTR benchmark (#222) the simulated audience must be a broad
US online-news / social-feed population — NOT the SaaS-product starter pack
(power / casual / new / at-risk PRODUCT users), which is the wrong latent
audience for sensational-headline CTR.

A methodology consult decided to build a purpose-built SYNTHETIC
general-US-news-audience persona pack, fixed and PRE-REGISTERED as the Upworthy
panel. It is intentionally a *generic* pack: identity-depth correctly degrades
to generic for Upworthy (no real behavioral rows / centroid features), because
Upworthy validates the engine's headline rendering + CTR elicitation, not the
persona-building pipeline. The personas therefore carry description / jtbd only;
``behavioral_snapshot``, ``centroid_features``, ``centroid_full``,
``feature_scale``, ``sample_rows``, ``posterior_mean`` and ``behavioral_seeds``
are all left absent so the simulator falls back to its generic identity path.

The pack ships with the application image (not the artifact store) because it is
application data — a pre-registered benchmark fixture — not a customer artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sidira_simulator.schemas.persona import PersonaPack

# The pre-registered panel id. This is the PersonaPack.version of the fixture;
# the benchmark reports it as the panel_id so a run is traceable to the exact
# pre-registered population.
UPWORTHY_PANEL_ID = "upworthy-general-us-news-v1"

# The single weight scheme this generic pack carries. head_count is the only
# scheme meaningful for a synthetic panel (there is no order / revenue signal),
# and population_sampler.allocate defaults to it.
UPWORTHY_PANEL_WEIGHT_SCHEME = "head_count"

_PANEL_PATH = Path(__file__).with_name("upworthy_general_panel_v1.json")


@dataclass(frozen=True)
class UpworthyPanelRegistration:
    """Pre-registration metadata a benchmark run should report.

    Lets a benchmark surface exactly which fixed population it ran against
    without re-deriving anything from the pack body.
    """

    panel_id: str
    version: str
    persona_count: int
    weight_scheme: str
    is_synthetic_generic: bool


@lru_cache(maxsize=1)
def load_upworthy_panel() -> PersonaPack:
    """Load + validate the pre-registered Upworthy panel once, then cache it.

    Returns a fully-validated :class:`PersonaPack`. Cached so repeated benchmark
    runs (and the accessor below) don't re-parse the bundled JSON.
    """
    return PersonaPack.model_validate_json(_PANEL_PATH.read_text())


def upworthy_panel_registration() -> UpworthyPanelRegistration:
    """The pre-registration metadata for the Upworthy panel.

    Synthetic-generic by construction: ``is_synthetic_generic`` is True because
    the pack carries no measured behavioral data — it exists to drive the
    benchmark's rendering + CTR-elicitation path at generic identity depth.
    """
    pack = load_upworthy_panel()
    return UpworthyPanelRegistration(
        panel_id=UPWORTHY_PANEL_ID,
        version=pack.version,
        persona_count=len(pack.personas),
        weight_scheme=UPWORTHY_PANEL_WEIGHT_SCHEME,
        is_synthetic_generic=True,
    )
