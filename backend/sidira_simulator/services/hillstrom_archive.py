"""Hillstrom MineThatData e-mail RCT → typed rows loader (#222 Hillstrom ingestion).

The directional-uplift benchmark (PLAN.md) needs the real Hillstrom 2008 e-mail
challenge dataset: a 64,000-customer randomized 3-arm e-mail A/B (Mens E-Mail /
Womens E-Mail / No E-Mail) with 8 pre-treatment features and binary visit /
conversion outcomes. This module is the *ingestion* edge — the Hillstrom mirror of
`services.upworthy_archive` — turning the public CSV into typed `HillstromRow`
objects the `services.hillstrom_adapter` turns into `BenchmarkCase`s.

Two halves, deliberately separated (same split as `upworthy_archive`):

  - `load_hillstrom_csv(csv_path, ...)` / `parse_hillstrom_rows(rows, ...)` — a
    pure-ish stdlib `csv` parse of an ALREADY-PRESENT local CSV into typed
    `HillstromRow`s, with a `HillstromLoadSummary` accounting for every dropped
    row (no silent truncation). The parsing core takes an iterable of dict rows so
    it is testable on an in-memory CSV string with ZERO file I/O.

  - `fetch_hillstrom_archive(dest_path)` — a GATED helper that downloads the
    public CSV. It refuses to run under pytest / CI (same guard
    `benchmark_runner.score_with_engine` / `upworthy_archive.fetch_upworthy_archive`
    use): fetching is a deliberate manual step, never a test/CI side effect. The
    raw CSV is NEVER committed (no explicit license → fetch-don't-redistribute,
    PLAN.md §1); only the DERIVED persona pack (PR-B) is committed.

No uplift / ground-truth math is computed here — that is the adapter's
(`hillstrom_adapter`) job, exactly as the Upworthy loader leaves CTR to its
adapter. The loader only carries the typed per-customer arm + features + outcomes.
"""

from __future__ import annotations

import csv
import logging
import math
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)

# ── public archive coordinates ───────────────────────────────────────────────
#
# The Kevin Hillstrom MineThatData E-Mail Analytics And Data Mining Challenge
# dataset (2008): a real randomized e-mail A/B/n. No explicit license; de-facto
# public (bundled by TFDS, scikit-uplift, causeinfer) and the author explicitly
# invited analysis + sharing of findings — but RE-HOSTING is a grey area, so we
# fetch-don't-redistribute (PLAN.md §1). The CSV is ≈3-4 MiB, 64k rows.
FETCH_URL = (
    "http://www.minethatdata.com/"
    "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv"
)

# The three randomized arms, exactly as the `segment` column spells them.
SEGMENT_NO_EMAIL = "No E-Mail"
SEGMENT_MENS = "Mens E-Mail"
SEGMENT_WOMENS = "Womens E-Mail"
VALID_SEGMENTS = frozenset({SEGMENT_NO_EMAIL, SEGMENT_MENS, SEGMENT_WOMENS})

# Default CSV column → loader field mapping. Verified against the dataset's data
# dictionary. Defensive by design: pass a partial `column_map` to override any
# single name if the file is re-published with a renamed column, without touching
# the rest. The 12 columns: 8 pre-treatment features, the arm, and 3 outcomes.
DEFAULT_COLUMN_MAP: dict[str, str] = {
    # 8 pre-treatment features
    "recency": "recency",
    "history_segment": "history_segment",
    "history": "history",
    "mens": "mens",
    "womens": "womens",
    "zip_code": "zip_code",
    "newbie": "newbie",
    "channel": "channel",
    # randomized arm
    "segment": "segment",
    # outcomes (spend carried but DROPPED from v1 scoring — no elicitor, PLAN.md §5)
    "visit": "visit",
    "conversion": "conversion",
    "spend": "spend",
}


@dataclass(frozen=True)
class HillstromRow:
    """One typed customer record from the RCT.

    The 8 pre-treatment features feed the offline GMM persona-pack build (PR-B);
    `segment` is the randomized arm; `visit` / `conversion` are the binary outcomes
    the directional benchmark scores. `spend` (continuous, zero-inflated) is
    carried for completeness but is OUT of v1 scoring scope (no elicitor, PLAN §5).
    """

    # pre-treatment features
    recency: int
    history_segment: str
    history: float
    mens: int
    womens: int
    zip_code: str
    newbie: int
    channel: str
    # randomized arm
    segment: str
    # outcomes
    visit: int
    conversion: int
    spend: float


@dataclass
class HillstromLoadSummary:
    """Honest accounting of one load: what became a row, what was dropped, why.

    Every input row is conserved: ``rows_read`` equals ``rows_kept`` plus every
    drop. Nothing is silently truncated — a caller can assert full coverage from
    these counts (the no-silent-degradation rule shared with the Upworthy loader).
    """

    rows_read: int = 0
    rows_kept: int = 0
    rows_dropped_missing_field: int = 0
    rows_dropped_unparseable: int = 0
    rows_dropped_bad_segment: int = 0
    drop_reasons: list[str] = field(default_factory=list)

    def note(self, reason: str) -> None:
        # Bounded human-readable trail: cap so a 64k-row file with a systematic
        # parse fault can't explode memory with one reason per row.
        if len(self.drop_reasons) < 50:
            self.drop_reasons.append(reason)


def _parse_int(raw: str | None) -> int | None:
    """Parse an integer cell, tolerating floats like ``"1.0"``.

    Returns None for blank/unparseable so the caller can drop the row with an
    honest count rather than crashing the whole load on one bad cell.
    """
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        try:
            f = float(text)
        except ValueError:
            return None
        if not math.isfinite(f) or f != int(f):
            return None
        return int(f)


def _parse_float(raw: str | None) -> float | None:
    """Parse a float cell (history / spend). Returns None for blank/unparseable
    or non-finite (NaN/inf) so the caller drops + counts the row."""
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None
    try:
        f = float(text)
    except ValueError:
        return None
    if not math.isfinite(f):
        return None
    return f


def _clean(raw: str | None) -> str:
    return raw.strip() if raw is not None else ""


def parse_hillstrom_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    column_map: Mapping[str, str] | None = None,
    fieldnames: Iterable[str] | None = None,
) -> tuple[list[HillstromRow], HillstromLoadSummary]:
    """Parse CSV dict rows into typed `HillstromRow`s. The pure, I/O-free core.

    Takes an iterable of already-parsed dict rows (e.g. from `csv.DictReader`, or a
    hand-built list in tests) so the typing/validation logic is exercised without
    touching the filesystem.

    Column presence is verified up front (from `fieldnames` if given, else from the
    first row's keys). A MISSING mapped column is a structural ingestion error that
    raises `ValueError`, NOT a silent per-row drop — a renamed/absent column must
    fail loud, exactly as the Upworthy loader treats its required columns.

    Per-row drops are counted and surfaced (never silently removed): a blank
    required cell, an unparseable numeric, or a `segment` outside the three RCT arms
    drops that single row and keeps the load going.
    """
    cmap = {**DEFAULT_COLUMN_MAP, **(column_map or {})}
    required_cols = tuple(cmap[k] for k in DEFAULT_COLUMN_MAP)

    rows_iter = iter(rows)
    if fieldnames is None:
        # Peek the first row to learn the header, then chain it back so it is still
        # parsed. A header-less / empty input has no columns to check.
        from itertools import chain

        try:
            first = next(rows_iter)
        except StopIteration:
            return [], HillstromLoadSummary()
        present = set(first.keys())
        rows_iter = chain([first], rows_iter)
    else:
        present = set(fieldnames)

    missing = [c for c in required_cols if c not in present]
    if missing:
        raise ValueError(
            f"Hillstrom CSV is missing required column(s) {missing}; present "
            f"columns: {sorted(present)}. Pass a `column_map` to bind renamed "
            "columns."
        )

    summary = HillstromLoadSummary()
    out: list[HillstromRow] = []
    for row in rows_iter:
        summary.rows_read += 1

        segment = _clean(row.get(cmap["segment"]))
        history_segment = _clean(row.get(cmap["history_segment"]))
        zip_code = _clean(row.get(cmap["zip_code"]))
        channel = _clean(row.get(cmap["channel"]))
        if not segment or not history_segment or not zip_code or not channel:
            summary.rows_dropped_missing_field += 1
            continue

        if segment not in VALID_SEGMENTS:
            summary.rows_dropped_bad_segment += 1
            summary.note(f"unrecognized segment {segment!r}")
            continue

        recency = _parse_int(row.get(cmap["recency"]))
        mens = _parse_int(row.get(cmap["mens"]))
        womens = _parse_int(row.get(cmap["womens"]))
        newbie = _parse_int(row.get(cmap["newbie"]))
        visit = _parse_int(row.get(cmap["visit"]))
        conversion = _parse_int(row.get(cmap["conversion"]))
        history = _parse_float(row.get(cmap["history"]))
        spend = _parse_float(row.get(cmap["spend"]))
        if None in (
            recency,
            mens,
            womens,
            newbie,
            visit,
            conversion,
            history,
            spend,
        ):
            summary.rows_dropped_unparseable += 1
            continue

        # visit / conversion are binary RCT outcomes; anything else means a
        # mis-mapped column — drop + count rather than mislabel a ground truth.
        if visit not in (0, 1) or conversion not in (0, 1):
            summary.rows_dropped_unparseable += 1
            summary.note(f"non-binary outcome visit={visit} conversion={conversion}")
            continue

        out.append(
            HillstromRow(
                recency=recency,  # type: ignore[arg-type]
                history_segment=history_segment,
                history=history,  # type: ignore[arg-type]
                mens=mens,  # type: ignore[arg-type]
                womens=womens,  # type: ignore[arg-type]
                zip_code=zip_code,
                newbie=newbie,  # type: ignore[arg-type]
                channel=channel,
                segment=segment,
                visit=visit,  # type: ignore[arg-type]
                conversion=conversion,  # type: ignore[arg-type]
                spend=spend,  # type: ignore[arg-type]
            )
        )
        summary.rows_kept += 1

    return out, summary


def load_hillstrom_csv(
    csv_path: str | Path,
    *,
    column_map: Mapping[str, str] | None = None,
    encoding: str = "utf-8",
) -> tuple[list[HillstromRow], HillstromLoadSummary]:
    """Load a LOCAL Hillstrom CSV into typed `HillstromRow`s.

    Thin file-I/O wrapper over `parse_hillstrom_rows`: opens `csv_path` with stdlib
    `csv.DictReader` and delegates all typing / validation / drop accounting to the
    pure core. Returns the retained rows and a `HillstromLoadSummary`.

    This never downloads anything — the file must already be present (use the gated
    `fetch_hillstrom_archive` for the deliberate one-time download).
    """
    path = Path(csv_path)
    with path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        rows, summary = parse_hillstrom_rows(
            reader,
            column_map=column_map,
            fieldnames=reader.fieldnames,
        )
    logger.info(
        "Loaded Hillstrom CSV %s: %d rows kept from %d read (dropped: %d "
        "missing-field, %d unparseable, %d bad-segment)",
        path.name,
        summary.rows_kept,
        summary.rows_read,
        summary.rows_dropped_missing_field,
        summary.rows_dropped_unparseable,
        summary.rows_dropped_bad_segment,
    )
    return rows, summary


def fetch_hillstrom_archive(dest_path: str | Path, *, timeout: float = 120.0) -> Path:
    """GATED download of the public Hillstrom CSV to `dest_path`.

    Refuses to run under pytest / CI — fetching the real dataset is a deliberate
    manual step, never a test or CI side effect (same guard
    `benchmark_runner.score_with_engine` / `upworthy_archive.fetch_upworthy_archive`
    apply). Use a pre-downloaded file with `load_hillstrom_csv` in every automated
    context. The raw CSV is NEVER committed (fetch-don't-redistribute, PLAN.md §1).

    Validates that the response looks like the Hillstrom CSV (header contains the
    `segment` column) before writing, so a moved URL or an HTML error page fails
    loudly instead of silently saving garbage. Returns the path written.
    """
    # Refuse under pytest AND under CI. The pytest checks catch the test harness;
    # the CI check catches a script/helper running in CI outside pytest, where the
    # standard `CI` env var (set by GitHub Actions, GitLab, etc.) is truthy — so an
    # automated job can never accidentally hit the live network.
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "fetch_hillstrom_archive downloads the live public dataset and must "
            "not run under pytest / CI. Pre-download the CSV once, then point "
            "load_hillstrom_csv at the local file in tests and automation. The raw "
            "CSV is never committed (fetch-don't-redistribute)."
        )

    import urllib.request

    dest = Path(dest_path)
    logger.info("Fetching Hillstrom e-mail RCT CSV from %s", FETCH_URL)
    req = urllib.request.Request(FETCH_URL, headers={"User-Agent": "sidira-benchmark-loader/1"})
    with urllib.request.urlopen(
        req, timeout=timeout
    ) as resp:  # noqa: S310 - fixed minethatdata URL
        data = resp.read()

    # Defensive content check: the first line must carry the key arm column so a
    # moved URL or HTML error page fails loudly rather than saving garbage.
    head = data[:4096].decode("utf-8", errors="replace").splitlines()
    first_line = head[0] if head else ""
    if DEFAULT_COLUMN_MAP["segment"] not in first_line:
        raise RuntimeError(
            "Downloaded content does not look like the Hillstrom CSV (header "
            f"missing {DEFAULT_COLUMN_MAP['segment']!r}). The URL may have moved "
            f"or the host returned an error page. Verify {FETCH_URL}."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    logger.info("Wrote %d bytes to %s", len(data), dest)
    return dest


# ── offline persona-pack build (PR-B) ────────────────────────────────────────
#
# The Hillstrom directional benchmark needs a REAL v1.1 persona pack built from
# the trial's 8 pre-treatment features — the first benchmark with real per-
# customer covariates, so the FIRST one to exercise the individual-row
# (`render_individual_row`) tier with real data. The pack is built ONCE offline
# from the fetched CSV by the sidira-personas GMM pipeline and the DERIVED pack
# JSON is committed (`adapters/hillstrom_panel_v1.json`). It is statistics
# (cluster centroids + privacy-clean synthetic GMM draws), NOT raw rows, so it is
# safe to redistribute — unlike the raw CSV, which is never committed (PLAN §1).
#
# The build is gated (refuses under pytest / CI) for the SAME reason as the
# fetcher and `score_with_engine`: it imports the heavy ML stack (pandas /
# scikit-learn via the separate `sidira-personas` repo) which is intentionally
# absent from the API image, and it is a deliberate, reproducible offline step,
# never a test/CI side effect. Tests validate the COMMITTED pack instead.
#
# KNOWN GAP — behavioral_seeds (cross-persona texture), DEFERRED (#222 PR-C).
# The committed pack's personas carry behavioral_seeds=None, so the simulator's
# `identity_seed.draw_identity_seed` falls back to its generic default pools for
# EVERY Hillstrom persona and logs "identity_seed fallback active - cross-persona
# variance degraded". This is the CROSS-persona texture path only; the WITHIN-
# persona individual-row path (render_individual_row via the v1.1 sample_rows
# quad) already fires correctly (test_render_individual_row_fires_not_fallback),
# and the fallback NEVER affects any numeric output — it is flagged honestly via
# AgentReaction.behavioral_seeds_fallback. It is deferred, not fixed, because:
#   1. The producer (sidira-personas GMM pipeline) emits NO behavioral_seeds at
#      all — `persona_pack_translator` defaults the field to None for every
#      translated pack (see its module docstring). This is an upstream producer
#      gap, not a Hillstrom-build bug; fixing it in the producer would benefit
#      every real pack, not just this one.
#   2. behavioral_seeds is FIVE pools (age_bands / locale_bands / tenure_bands /
#      current_state_pool / recent_gripe_pool). The Hillstrom trial carries NO
#      age, locale, tenure, current-state, or gripe signal — only recency,
#      history, gender flags, zip-tier, newbie, channel. Four of the five pools
#      could only be FABRICATED (authored, not measured), which would dress the
#      pack's real-measured-statistics provenance (PLAN §1) in invented texture.
#   3. Populating them requires REGENERATING the committed pack via this gated
#      GMM build, which risks perturbing the centroids / sample_rows the #222
#      PR-C by-segment stratification + the committed-pack tests are pinned to.
# FIX PATH (when prioritized): add a `behavioral_seeds` emitter to the producer
# (sidira-personas) — or, if Hillstrom-only, hand-author domain-appropriate
# RETAIL pools per cluster here and inject them post-translate before serialize
# (mirroring identity_seed._PERSONA_OVERRIDES) — then rebuild + re-commit the
# pack and assert is_individual_row_capable stays True and the centroids are
# unchanged. Until then the honest fallback is the correct behavior.

# The producer column → FeatureGroup map, frozen here as the pre-registered
# feature-mapping for the build (PLAN §3a, researcher-DOF freeze). The outcome
# columns (segment / visit / conversion / spend) are DELIBERATELY absent: they
# must never enter the clustering or the pack would leak the answer key into the
# persona identities. Adapter types are pinned (not inferred) so the build is
# reproducible byte-for-byte from this source.
HILLSTROM_FEATURE_GROUPS: dict[str, list[dict[str, str]]] = {
    "loyalty_lifecycle": [
        {"name": "recency", "type": "count"},
        {"name": "newbie", "type": "flag"},
    ],
    "value_sensitivity": [
        {"name": "history", "type": "score"},
        {"name": "history_segment", "type": "categorical"},
    ],
    "motivations_jtbd": [
        {"name": "mens", "type": "flag"},
        {"name": "womens", "type": "flag"},
    ],
    "demographic_identity": [
        {"name": "zip_code", "type": "categorical"},
    ],
    "channel_tech_behavior": [
        {"name": "channel", "type": "categorical"},
    ],
}

# k is FIXED at 4, not BIC-auto. A spike (STAGE 1) showed the stability/gender-
# separation tradeoff is non-monotonic over k: BIC-auto (k=8) over-segments
# (stability ≈ 0.43, below the 0.5 floor); k=3 is very stable (≈ 0.86) but
# collapses the gender signal (every cluster ≈ 50/50 mens/womens, affinity range
# ≈ 0.006) — fatal to the heterogeneity claim; k=4 is the only setting that BOTH
# clears the stability floor (≈ 0.52) AND yields a clean men's-buyer cluster
# (mens=1, womens=0) and women's-buyer cluster (mens=0, womens=1). The benchmark's
# sellable endpoint #3 REQUIRES that gender separation, so k is pinned to 4.
HILLSTROM_PANEL_K = 4

# The pre-registered panel id (the PersonaPack.version, reported as panel_id so a
# run is traceable to the exact population). Versioned independently of the on-disk
# filename, mirroring the Upworthy panel convention.
HILLSTROM_PANEL_VERSION = "hillstrom-email-rct-v1"


def _hillstrom_pipeline_config() -> dict:
    """The frozen sidira-personas pipeline config for the Hillstrom pack build.

    Mirrors the shape `persona_builder._build_pipeline_config` produces, but with
    adapter types and k PINNED (not inferred) so the offline build is reproducible.
    No group is excluded from clustering — the gender-affinity group
    (`motivations_jtbd`) MUST drive the clusters for the heterogeneity endpoint.
    """
    return {
        "company_id": "hillstrom",
        "run_id_prefix": "hillstrom",
        "source": {"type": "local", "user_id_column": "customer_id"},
        "feature_groups": HILLSTROM_FEATURE_GROUPS,
        "clustering_exclude_groups": [],
        "encoder": {"method": "pca", "embedding_dim_per_group": 4},
        "cluster": {
            "method": "gmm",
            "k_range": [HILLSTROM_PANEL_K, HILLSTROM_PANEL_K],
            "selection": "bic",
            "random_state": 42,
            "bootstrap_iters": 10,
            "stability_threshold": 0.5,
            "holdout_frac": 0.2,
        },
        "weights": {"schemes": ["headcount"], "orders_column": None, "revenue_column": None},
        "sampling": {"n_synthetic_rows": 32, "random_state": 42},
        "prompt_compiler": {"top_n_distinctive_features_per_group": 4, "threshold_sigma": 0.3},
    }


def build_hillstrom_panel_pack(csv_path: str | Path):
    """Build the DERIVED Hillstrom v1.1 persona pack from a local CSV (gated).

    Loads the local Hillstrom CSV, runs the `sidira-personas` GMM pipeline over
    the 8 pre-treatment features (PLAN §3a, outcomes excluded), and translates the
    producer pack into the simulator's :class:`PersonaPack` (carrying the v1.1
    quad — centroid_full / feature_scale / sample_rows / posterior_mean — so the
    individual-row tier fires). Returns the validated `PersonaPack`; the caller
    writes the JSON to `adapters/hillstrom_panel_v1.json`.

    GATED: refuses under pytest / CI. It imports the heavy ML stack (pandas +
    `sidira-personas`, absent from the API image) and is a deliberate offline
    build, never a test side effect — exactly the discipline `score_with_engine`
    and `fetch_hillstrom_archive` apply. Tests validate the committed pack.

    Raises RuntimeError under pytest / CI or if `sidira-personas` is not installed.
    """
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "build_hillstrom_panel_pack imports the heavy ML stack and runs the GMM "
            "pipeline; it must not run under pytest / CI. The committed pack "
            "(adapters/hillstrom_panel_v1.json) is what tests validate; rebuild it "
            "offline with this function when the source / mapping changes."
        )

    try:
        import pandas as pd

        from sidira_personas import run_pipeline
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sidira-personas not installed — install it (Python 3.11+) to rebuild "
            "the Hillstrom persona pack: `python3.11 -m pip install -e "
            "~/Projects/sidira-personas`."
        ) from exc

    from sidira_simulator.services.persona_pack_translator import translate_producer_pack

    rows, summary = load_hillstrom_csv(csv_path)
    if not rows:
        raise RuntimeError(f"no Hillstrom rows loaded from {csv_path} — cannot build pack")
    logger.info("Building Hillstrom panel pack from %d rows", summary.rows_kept)

    df = pd.DataFrame(
        [
            {
                "customer_id": i,
                "recency": r.recency,
                "history": r.history,
                "history_segment": r.history_segment,
                "mens": r.mens,
                "womens": r.womens,
                "zip_code": r.zip_code,
                "newbie": r.newbie,
                "channel": r.channel,
            }
            for i, r in enumerate(rows)
        ]
    )

    result = run_pipeline(
        df, _hillstrom_pipeline_config(), run_id=HILLSTROM_PANEL_VERSION, no_llm=True
    )
    from dataclasses import asdict

    producer_pack = asdict(result.pack)
    pack = translate_producer_pack(producer_pack, version=HILLSTROM_PANEL_VERSION)
    logger.info(
        "Built Hillstrom pack: k=%d, %d personas, stability=%.3f",
        result.pack.k_selected,
        len(pack.personas),
        pack.stability_score,
    )
    return pack


def write_hillstrom_panel_pack(csv_path: str | Path, dest_path: str | Path) -> Path:
    """Build + serialize the Hillstrom panel pack to `dest_path` (gated).

    The reproducible offline build entry point: regenerates the committed
    `adapters/hillstrom_panel_v1.json`. Refuses under pytest / CI via
    :func:`build_hillstrom_panel_pack`. Returns the path written.
    """
    pack = build_hillstrom_panel_pack(csv_path)
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(pack.model_dump_json(indent=2))
    logger.info("Wrote Hillstrom panel pack to %s", dest)
    return dest
