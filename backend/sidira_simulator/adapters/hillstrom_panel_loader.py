"""Hillstrom RCT persona-pack loader — the real v1.1 directional-uplift panel.

For the Hillstrom email-uplift benchmark (#222) the simulated audience is NOT a
synthetic generic panel (the Upworthy approach) — it is a REAL v1.1 persona pack
DERIVED from the trial's own 64,000 customers via the sidira-personas GMM
pipeline (services.hillstrom_archive.build_hillstrom_panel_pack). This is the
first benchmark with real per-customer covariates, so the first one whose pack
carries the v1.1 quantitative quad (``centroid_full`` / ``feature_scale`` /
``sample_rows`` / ``posterior_mean``) — which means it EXERCISES the
``render_individual_row`` (``individual_row_synthetic``) tier with real data,
not the centroid fallback the synthetic Upworthy panel degrades to.

The pack is built ONCE offline and the DERIVED JSON is committed
(``hillstrom_panel_v1.json``) — it is statistics (cluster centroids + privacy-
clean GMM draws), not raw rows, so it is safe to redistribute (PLAN §1). This
loader is the Hillstrom mirror of ``upworthy_panel_loader``: it loads + validates
the committed pack once (cached) and exposes the pre-registration metadata a
benchmark run reports.

Unlike the Upworthy panel, this pack is ``is_synthetic_generic=False``: it is a
real measured pack, so the registration says so and a run's panel_id traces to
the exact pre-registered population.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sidira_simulator.schemas.persona import PersonaPack, WeightSchemes
from sidira_simulator.services.hillstrom_archive import HILLSTROM_PANEL_VERSION

# The pre-registered panel id (reported as panel_id so a run is traceable to the
# exact population). It IS the PersonaPack.version stamped at build time; sourced
# from the build module so the two can never drift.
HILLSTROM_PANEL_ID = HILLSTROM_PANEL_VERSION

# The single weight scheme this pack carries. The build runs headcount-only (the
# RCT has no order / revenue signal), and population_sampler.allocate defaults to
# head_count — same as the Upworthy panel.
HILLSTROM_PANEL_WEIGHT_SCHEME = "head_count"

_PANEL_PATH = Path(__file__).with_name("hillstrom_panel_v1.json")


@dataclass(frozen=True)
class HillstromPanelRegistration:
    """Pre-registration metadata a Hillstrom benchmark run should report.

    Lets a run surface exactly which fixed population it ran against without
    re-deriving anything from the pack body. ``is_individual_row_capable`` is the
    Hillstrom-specific signal the Upworthy registration lacks: True iff EVERY
    persona carries the v1.1 quad, so the run can assert it exercised the
    individual-row tier rather than the centroid fallback.
    """

    panel_id: str
    version: str
    persona_count: int
    weight_scheme: str
    schema_version: str
    is_synthetic_generic: bool
    is_individual_row_capable: bool


@lru_cache(maxsize=1)
def load_hillstrom_panel() -> PersonaPack:
    """Load + validate the committed Hillstrom panel once, then cache it.

    Returns a fully-validated :class:`PersonaPack`. Cached so repeated benchmark
    runs (and the accessor below) don't re-parse the bundled JSON.
    """
    return PersonaPack.model_validate_json(_PANEL_PATH.read_text())


def _is_individual_row_capable(pack: PersonaPack) -> bool:
    """True iff every persona carries the v1.1 individual-row inputs.

    ``render_individual_row`` fires (rather than degrading to the centroid tier)
    only when a persona has all of ``sample_rows`` + ``centroid_full`` +
    ``feature_scale``. The benchmark's headline is that it exercises that tier, so
    the registration asserts the WHOLE pack supports it — a single degraded
    persona (which would silently fall back) flips this to False.
    """
    return all(
        bool(p.sample_rows) and bool(p.centroid_full) and bool(p.feature_scale)
        for p in pack.personas
    )


# The 4 heterogeneity strata, aligned to the committed pack's 4 GMM personas
# (services.hillstrom_adapter._segment_key). Each maps to ONE distinct cohort so
# the audience is meaningfully conditioned per stratum (endpoint #3 signal). The
# spend axis (high-spender vs mid-tier, which split the both-gender clusters) is
# read off the `history` centroid coordinate — the GMM clusters separate the
# both-buyer population into a high-history (P03) and a mid-history (P04) cluster.
_GENDER_HIGH = 0.5  # a flag-mean above this = the cluster predominantly buys it


def segment_persona_ids(pack: PersonaPack, segment_key: str) -> list[str]:
    """The personas whose centroid matches a heterogeneity stratum (endpoint #3).

    The per-segment scoring endpoint is only valid if the SIMULATED AUDIENCE is
    conditioned on the stratum — otherwise every segment case for an arm reuses
    the identical full panel + identical stimulus and the blind engine cannot tell
    one stratum from another, so its predictions measure seed noise, not
    heterogeneous response. This maps a stratum (the adapter's `_segment_key`) to
    the pack's matching personas by centroid, aligned to the 4 GMM clusters::

        mens_buyer    → mens-centroid high, womens-centroid low      (P02)
        womens_buyer  → womens-centroid high, mens-centroid low      (P01)
        high_spender  → BOTH genders high AND high `history` centroid (P03)
        mid_tier      → BOTH genders high AND lower `history`         (P04)

    Read straight off `centroid_full` (raw 0..1 flag means + the `history` score),
    so it tracks whatever the committed pack actually clustered. The high/mid split
    is RELATIVE: among the both-gender clusters, those at or above the MEDIAN
    `history` centroid are high_spender, the rest mid_tier — so the boundary tracks
    the pack instead of pinning a magic dollar threshold the GMM might shift.

    STRUCTURALLY BLIND: keyed only on the persona's pre-treatment centroid
    coordinates (gender flags, spend history) — never on any observed outcome /
    ground truth, which the pack does not even carry (outcomes are excluded from
    the clustering, hillstrom_archive.HILLSTROM_FEATURE_GROUPS).

    NEAREST-COHORT FALLBACK (never the full panel). If the EXACT predicate matches
    no persona we fall back to the single CLOSEST cohort by distance to the
    stratum's prototype, NOT to the full panel. A whole-panel fallback would
    re-introduce the exact undifferentiated-audience degenerate the conditioning
    exists to prevent; the nearest single cohort keeps the audience conditioned (a
    still-honest, still-distinct sub-panel) so the endpoint stays valid even on
    strata the committed pack under-represents. Only an UNKNOWN stratum key raises.
    Returns the matching persona ids in pack order.
    """
    # Prototype (mens, womens, history) affinity each stratum represents — used for
    # the nearest-cohort fallback distance. `history` is a z-like score; the
    # high/mid prototypes use a coarse ±1 so the fallback still orders sensibly.
    prototypes = {
        "mens_buyer": (1.0, 0.0, 0.0),
        "womens_buyer": (0.0, 1.0, 0.0),
        "high_spender": (1.0, 1.0, 1.0),
        "mid_tier": (1.0, 1.0, -1.0),
    }
    if segment_key not in prototypes:
        raise ValueError(f"unknown Hillstrom segment key {segment_key!r}")

    def _gender(p) -> tuple[float, float]:
        cf = p.centroid_full or {}
        return cf.get("mens", 0.0), cf.get("womens", 0.0)

    # Among the both-gender clusters, the median `history` centroid is the relative
    # high/mid boundary (so the split tracks the pack, not a magic dollar value).
    both_personas = [p for p in pack.personas if all(g >= _GENDER_HIGH for g in _gender(p))]
    history_vals = sorted((p.centroid_full or {}).get("history", 0.0) for p in both_personas)
    if history_vals:
        mid = len(history_vals) // 2
        spend_boundary = (
            history_vals[mid]
            if len(history_vals) % 2
            else (history_vals[mid - 1] + history_vals[mid]) / 2.0
        )
    else:
        spend_boundary = 0.0

    matches: list[str] = []
    for p in pack.personas:
        mens, womens = _gender(p)
        history = (p.centroid_full or {}).get("history", 0.0)
        if segment_key == "mens_buyer":
            ok = mens >= _GENDER_HIGH and womens < _GENDER_HIGH
        elif segment_key == "womens_buyer":
            ok = womens >= _GENDER_HIGH and mens < _GENDER_HIGH
        elif segment_key == "high_spender":
            ok = mens >= _GENDER_HIGH and womens >= _GENDER_HIGH and history >= spend_boundary
        else:  # mid_tier
            ok = mens >= _GENDER_HIGH and womens >= _GENDER_HIGH and history < spend_boundary
        if ok:
            matches.append(p.id)
    if matches:
        return matches

    # No exact match — condition on the single NEAREST cohort (never the full panel).
    px, py, ph = prototypes[segment_key]

    def _dist(p) -> float:
        cf = p.centroid_full or {}
        return (
            (cf.get("mens", 0.0) - px) ** 2
            + (cf.get("womens", 0.0) - py) ** 2
            + (cf.get("history", 0.0) - ph) ** 2
        )

    nearest = min(pack.personas, key=_dist)
    return [nearest.id]


def hillstrom_segment_subpack(pack: PersonaPack, segment_key: str) -> PersonaPack:
    """A sub-pack restricted to a stratum's personas, head_count renormalized.

    Conditions the simulated audience on a heterogeneity stratum: the returned
    pack carries ONLY the personas :func:`segment_persona_ids` matches, with their
    head_count weights renormalized to sum to 1 (so the full population lands on
    the conditioned cohort, not a proportional slice). The optional order/revenue
    schemes are dropped (the Hillstrom pack carries head_count only). All other
    pack metadata is preserved; the version is suffixed with the stratum so a run's
    panel_id traces to the conditioned cohort. Raises ValueError (via
    `segment_persona_ids`) if the stratum has no matching persona.
    """
    ids = set(segment_persona_ids(pack, segment_key))
    sub_personas = [p for p in pack.personas if p.id in ids]
    raw = {p.id: pack.weights.head_count.get(p.id, 0.0) for p in sub_personas}
    total = sum(raw.values())
    if total <= 0.0:
        # Degenerate weights (all zero) — fall back to an equal split so allocate()
        # still gets a valid, summing-to-1 scheme rather than failing the cohort.
        renorm = {pid: 1.0 / len(sub_personas) for pid in raw}
    else:
        renorm = {pid: w / total for pid, w in raw.items()}
    return pack.model_copy(
        update={
            "version": f"{pack.version}:{segment_key}",
            "personas": sub_personas,
            "weights": WeightSchemes(head_count=renorm),
        }
    )


def hillstrom_panel_registration() -> HillstromPanelRegistration:
    """The pre-registration metadata for the Hillstrom panel.

    ``is_synthetic_generic`` is False — this is a REAL measured pack derived from
    the trial's own customers, the opposite of the Upworthy synthetic-generic
    panel. ``is_individual_row_capable`` reports whether the pack actually drives
    the v1.1 individual-row tier (the benchmark's headline claim).
    """
    pack = load_hillstrom_panel()
    return HillstromPanelRegistration(
        panel_id=HILLSTROM_PANEL_ID,
        version=pack.version,
        persona_count=len(pack.personas),
        weight_scheme=HILLSTROM_PANEL_WEIGHT_SCHEME,
        schema_version=pack.schema_version,
        is_synthetic_generic=False,
        is_individual_row_capable=_is_individual_row_capable(pack),
    )
