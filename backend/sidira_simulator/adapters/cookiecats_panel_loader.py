"""Cookie Cats persona-pack loader — the real v1.1 engagement-tier panel.

For the Cookie Cats gate-move benchmark the simulated audience is a v1.1 persona
pack DERIVED from the trial's own players' engagement feature (`sum_gamerounds`)
via the sidira-personas GMM pipeline
(`services.cookiecats_archive.build_cookiecats_panel_pack`). Like the Hillstrom
pack, it carries the v1.1 quantitative quad (``centroid_full`` / ``feature_scale``
/ ``sample_rows`` / ``posterior_mean``), so it EXERCISES the
``render_individual_row`` (``individual_row_synthetic``) tier with real data
rather than the centroid fallback.

The pack is built ONCE offline and the DERIVED JSON is committed
(``cookiecats_panel_v1.json``) — it is statistics (cluster centroids + privacy-
clean GMM draws), not raw rows, so it is safe to redistribute. This loader is the
Cookie Cats mirror of ``hillstrom_panel_loader``: it loads + validates the
committed pack once (cached) and exposes the pre-registration metadata a run
reports, plus the per-engagement-stratum conditioning the by-segment endpoint
needs.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from sidira_simulator.schemas.persona import PersonaPack, WeightSchemes
from sidira_simulator.services.cookiecats_adapter import N_ENGAGEMENT_STRATA
from sidira_simulator.services.cookiecats_archive import COOKIECATS_PANEL_VERSION

# The pre-registered panel id (reported as panel_id so a run is traceable to the
# exact population). It IS the PersonaPack.version stamped at build time.
COOKIECATS_PANEL_ID = COOKIECATS_PANEL_VERSION

# The single weight scheme this pack carries (the trial has no order / revenue
# signal; allocate() defaults to head_count).
COOKIECATS_PANEL_WEIGHT_SCHEME = "head_count"

_PANEL_PATH = Path(__file__).with_name("cookiecats_panel_v1.json")

# The engagement feature the clusters separate on (the only pre-treatment
# covariate Cookie Cats carries).
_ENGAGEMENT_FEATURE = "sum_gamerounds"


@dataclass(frozen=True)
class CookieCatsPanelRegistration:
    """Pre-registration metadata a Cookie Cats benchmark run should report.

    ``is_individual_row_capable`` is True iff EVERY persona carries the v1.1 quad,
    so the run can assert it exercised the individual-row tier rather than the
    centroid fallback. ``is_synthetic_generic`` is False — this is a measured pack
    derived from the trial's own players.
    """

    panel_id: str
    version: str
    persona_count: int
    weight_scheme: str
    schema_version: str
    is_synthetic_generic: bool
    is_individual_row_capable: bool


@lru_cache(maxsize=1)
def load_cookiecats_panel() -> PersonaPack:
    """Load + validate the committed Cookie Cats panel once, then cache it."""
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


def _engagement_ordered_personas(pack: PersonaPack) -> list:
    """Personas sorted ascending by their `sum_gamerounds` centroid (low→heavy).

    The engagement tier ordering the octile→persona mapping conditions on. Read
    straight off `centroid_full`, so it tracks whatever the committed pack
    actually clustered (never an outcome — outcomes are excluded from the build).
    """
    return sorted(
        pack.personas,
        key=lambda p: (p.centroid_full or {}).get(_ENGAGEMENT_FEATURE, 0.0),
    )


def _octile_index(segment_key: str) -> int:
    """The 1-based octile number from an `eng_o<n>` stratum key (validated)."""
    if not segment_key.startswith("eng_o"):
        raise ValueError(f"unknown Cookie Cats segment key {segment_key!r}")
    try:
        n = int(segment_key[len("eng_o") :])
    except ValueError as exc:
        raise ValueError(f"unknown Cookie Cats segment key {segment_key!r}") from exc
    if not (1 <= n <= N_ENGAGEMENT_STRATA):
        raise ValueError(
            f"Cookie Cats octile {n} out of range 1..{N_ENGAGEMENT_STRATA} "
            f"(segment key {segment_key!r})"
        )
    return n


def segment_persona_ids(pack: PersonaPack, segment_key: str) -> list[str]:
    """The persona(s) whose engagement tier matches an octile stratum.

    The per-segment scoring endpoint is only valid if the SIMULATED AUDIENCE is
    conditioned on the stratum — otherwise every octile case reuses the identical
    full panel + identical stimulus and the blind engine cannot tell one octile
    from another. This maps an engagement octile (`eng_o1`..`eng_o8`) to the
    pack's matching engagement-tier persona by splitting the octile range evenly
    across the clusters sorted low→heavy by their `sum_gamerounds` centroid::

        with 8 octiles and 3 clusters: o1-o3 → low tier, o4-o6 → mid, o7-o8 → heavy

    So the lowest-engagement octiles condition on the low-engagement persona, etc.
    The mapping scales with whatever persona count the committed pack carries
    (octile → cluster by proportional position), so it stays valid if k changes.

    STRUCTURALLY BLIND: keyed only on the persona's pre-treatment engagement
    centroid — never on any observed retention / ground truth (which the pack does
    not carry). An UNKNOWN stratum key raises. Returns the matching persona ids.
    """
    octile = _octile_index(segment_key)  # validates 1..8
    ordered = _engagement_ordered_personas(pack)
    k = len(ordered)
    if k == 0:
        raise ValueError("Cookie Cats pack carries no personas")
    # Proportional position of this octile (0-based) mapped onto the k clusters.
    cluster_idx = ((octile - 1) * k) // N_ENGAGEMENT_STRATA
    cluster_idx = min(cluster_idx, k - 1)
    return [ordered[cluster_idx].id]


def cookiecats_segment_subpack(pack: PersonaPack, segment_key: str) -> PersonaPack:
    """A sub-pack restricted to a stratum's personas, head_count renormalized.

    Conditions the simulated audience on an engagement-octile stratum: the
    returned pack carries ONLY the personas :func:`segment_persona_ids` matches,
    with their head_count weights renormalized to sum to 1. The optional
    order/revenue schemes are dropped (this pack carries head_count only). The
    version is suffixed with the stratum so a run's panel_id traces to the
    conditioned cohort. Raises ValueError (via `segment_persona_ids`) on an
    unknown stratum.
    """
    ids = set(segment_persona_ids(pack, segment_key))
    sub_personas = [p for p in pack.personas if p.id in ids]
    raw = {p.id: pack.weights.head_count.get(p.id, 0.0) for p in sub_personas}
    total = sum(raw.values())
    if total <= 0.0:
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


def cookiecats_panel_registration() -> CookieCatsPanelRegistration:
    """The pre-registration metadata for the Cookie Cats panel.

    ``is_synthetic_generic`` is False — a measured pack derived from the trial's
    own players. ``is_individual_row_capable`` reports whether the pack actually
    drives the v1.1 individual-row tier.
    """
    pack = load_cookiecats_panel()
    return CookieCatsPanelRegistration(
        panel_id=COOKIECATS_PANEL_ID,
        version=pack.version,
        persona_count=len(pack.personas),
        weight_scheme=COOKIECATS_PANEL_WEIGHT_SCHEME,
        schema_version=pack.schema_version,
        is_synthetic_generic=False,
        is_individual_row_capable=_is_individual_row_capable(pack),
    )
