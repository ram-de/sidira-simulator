"""Cookie Cats mobile-game A/B test → typed rows loader (in-scope product-change benchmark).

The accuracy campaign certified that the simulator is directionally BACKWARDS on
out-of-scope "marketing nudge" stimuli (the Hillstrom e-mail RCT: direction
accuracy 0.0, confirmed model-independent). This module is the ingestion edge for
the IN-SCOPE class the product actually sells: a deliberative reaction to a
PRODUCT change. The best obtainable external real-world dataset is **Cookie Cats**
— a ~90,189-player mobile-game A/B test where the first progress GATE was moved
from level 30 (`gate_30`, control) to level 40 (`gate_40`, treatment).

This is the Cookie Cats mirror of `services.hillstrom_archive`: it turns the
public CSV into typed `CookieCatsRow` objects the `services.cookiecats_adapter`
turns into `BenchmarkCase`s. Same two-halves split as Hillstrom / Upworthy:

  - `load_cookiecats_csv(csv_path, ...)` / `parse_cookiecats_rows(rows, ...)` — a
    pure-ish stdlib `csv` parse of an ALREADY-PRESENT local CSV into typed
    `CookieCatsRow`s, with a `CookieCatsLoadSummary` accounting for every dropped
    row (no silent truncation). The parsing core takes an iterable of dict rows so
    it is testable on an in-memory CSV string with ZERO file I/O.

  - `fetch_cookiecats_archive(dest_path)` — a GATED helper that downloads the
    public CSV. It refuses to run under pytest / CI (same guard
    `benchmark_runner.score_with_engine` / `hillstrom_archive.fetch_hillstrom_archive`
    use): fetching is a deliberate manual step, never a test/CI side effect.

No uplift / ground-truth math is computed here — that is the adapter's
(`cookiecats_adapter`) job. The loader only carries the typed per-player
arm + engagement + retention outcomes.
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping

logger = logging.getLogger(__name__)

# ── public archive coordinates ───────────────────────────────────────────────
#
# The Cookie Cats A/B dataset, widely mirrored for teaching (DataCamp project
# "Mobile Games A/B Testing with Cookie Cats", Kaggle, et al.). No single
# canonical license; de-facto public for analysis. We fetch-don't-redistribute
# (mirroring the Hillstrom discipline): the raw CSV is NEVER committed — only the
# DERIVED persona pack (statistics, not raw rows) is committed. The CSV is ≈4 MiB,
# ~90k rows. The default URL points at a stable mirror; pass --csv-path to a
# locally-placed file in every automated/prod context.
FETCH_URL = (
    "https://raw.githubusercontent.com/datacamp/"
    "careerhub-data/master/Mobile%20Games%20A-B%20Testing/datasets/cookie_cats.csv"
)

# The two randomized arms, exactly as the `version` column spells them.
VERSION_GATE_30 = "gate_30"  # control: first progress gate at level 30
VERSION_GATE_40 = "gate_40"  # treatment: gate moved to level 40
CONTROL_VERSION = VERSION_GATE_30
TREATMENT_VERSION = VERSION_GATE_40
VALID_VERSIONS = frozenset({VERSION_GATE_30, VERSION_GATE_40})

# Default CSV column → loader field mapping. Verified against the dataset's data
# dictionary. Defensive by design: pass a partial `column_map` to override any
# single name if the file is re-published with a renamed column. The 5 columns:
# userid, version (arm), sum_gamerounds (engagement feature), and 2 retention
# outcomes.
DEFAULT_COLUMN_MAP: dict[str, str] = {
    "userid": "userid",
    "version": "version",
    "sum_gamerounds": "sum_gamerounds",
    "retention_1": "retention_1",
    "retention_7": "retention_7",
}

# Truthy / falsy spellings the boolean retention cells may carry. The raw dataset
# uses Python-style `True`/`False`; a re-export may use 1/0 or true/false. We
# accept all three families and drop+count anything else (never silently coerce).
_TRUE_TOKENS = frozenset({"true", "1", "1.0", "yes", "t"})
_FALSE_TOKENS = frozenset({"false", "0", "0.0", "no", "f"})


@dataclass(frozen=True)
class CookieCatsRow:
    """One typed player record from the A/B test.

    `sum_gamerounds` is the pre-retention engagement feature that drives the
    offline GMM persona-pack build and the by-segment stratification. `version`
    is the randomized arm; `retention_1` / `retention_7` are the binary outcomes
    the directional benchmark scores (`retention_7` primary, `retention_1`
    secondary).
    """

    userid: int
    version: str
    sum_gamerounds: int
    retention_1: int
    retention_7: int


@dataclass
class CookieCatsLoadSummary:
    """Honest accounting of one load: what became a row, what was dropped, why.

    Every input row is conserved: ``rows_read`` equals ``rows_kept`` plus every
    drop. Nothing is silently truncated — a caller can assert full coverage from
    these counts (the no-silent-degradation rule shared with the Hillstrom loader).
    """

    rows_read: int = 0
    rows_kept: int = 0
    rows_dropped_missing_field: int = 0
    rows_dropped_unparseable: int = 0
    rows_dropped_bad_version: int = 0
    drop_reasons: list[str] = field(default_factory=list)

    def note(self, reason: str) -> None:
        # Bounded human-readable trail: cap so a 90k-row file with a systematic
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
        if f != int(f):
            return None
        return int(f)


def _parse_bool01(raw: str | None) -> int | None:
    """Parse a boolean retention cell into 0/1.

    Accepts True/False, 1/0, yes/no, t/f (case-insensitive). Returns None for
    blank/unrecognized so the caller drops + counts the row rather than coercing
    an unknown token into a ground-truth label.
    """
    if raw is None:
        return None
    text = raw.strip().lower()
    if not text:
        return None
    if text in _TRUE_TOKENS:
        return 1
    if text in _FALSE_TOKENS:
        return 0
    return None


def _clean(raw: str | None) -> str:
    return raw.strip() if raw is not None else ""


def parse_cookiecats_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    column_map: Mapping[str, str] | None = None,
    fieldnames: Iterable[str] | None = None,
) -> tuple[list[CookieCatsRow], CookieCatsLoadSummary]:
    """Parse CSV dict rows into typed `CookieCatsRow`s. The pure, I/O-free core.

    Takes an iterable of already-parsed dict rows (e.g. from `csv.DictReader`, or
    a hand-built list in tests) so the typing/validation logic is exercised
    without touching the filesystem.

    Column presence is verified up front (from `fieldnames` if given, else from
    the first row's keys). A MISSING mapped column is a structural ingestion error
    that raises `ValueError`, NOT a silent per-row drop — a renamed/absent column
    must fail loud, exactly as the Hillstrom loader treats its required columns.

    Per-row drops are counted and surfaced (never silently removed): a blank
    required cell, an unparseable numeric, a non-binary retention token, or a
    `version` outside the two arms drops that single row and keeps the load going.
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
            return [], CookieCatsLoadSummary()
        present = set(first.keys())
        rows_iter = chain([first], rows_iter)
    else:
        present = set(fieldnames)

    missing = [c for c in required_cols if c not in present]
    if missing:
        raise ValueError(
            f"Cookie Cats CSV is missing required column(s) {missing}; present "
            f"columns: {sorted(present)}. Pass a `column_map` to bind renamed "
            "columns."
        )

    summary = CookieCatsLoadSummary()
    out: list[CookieCatsRow] = []
    for row in rows_iter:
        summary.rows_read += 1

        version = _clean(row.get(cmap["version"]))
        if not version:
            summary.rows_dropped_missing_field += 1
            continue
        if version not in VALID_VERSIONS:
            summary.rows_dropped_bad_version += 1
            summary.note(f"unrecognized version {version!r}")
            continue

        userid = _parse_int(row.get(cmap["userid"]))
        sum_gamerounds = _parse_int(row.get(cmap["sum_gamerounds"]))
        retention_1 = _parse_bool01(row.get(cmap["retention_1"]))
        retention_7 = _parse_bool01(row.get(cmap["retention_7"]))
        if None in (userid, sum_gamerounds, retention_1, retention_7):
            summary.rows_dropped_unparseable += 1
            continue

        out.append(
            CookieCatsRow(
                userid=userid,  # type: ignore[arg-type]
                version=version,
                sum_gamerounds=sum_gamerounds,  # type: ignore[arg-type]
                retention_1=retention_1,  # type: ignore[arg-type]
                retention_7=retention_7,  # type: ignore[arg-type]
            )
        )
        summary.rows_kept += 1

    return out, summary


def load_cookiecats_csv(
    csv_path: str | Path,
    *,
    column_map: Mapping[str, str] | None = None,
    encoding: str = "utf-8",
) -> tuple[list[CookieCatsRow], CookieCatsLoadSummary]:
    """Load a LOCAL Cookie Cats CSV into typed `CookieCatsRow`s.

    Thin file-I/O wrapper over `parse_cookiecats_rows`: opens `csv_path` with
    stdlib `csv.DictReader` and delegates all typing / validation / drop
    accounting to the pure core. Returns the retained rows and a
    `CookieCatsLoadSummary`.

    This never downloads anything — the file must already be present (use the
    gated `fetch_cookiecats_archive` for the deliberate one-time download).
    """
    path = Path(csv_path)
    with path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        rows, summary = parse_cookiecats_rows(
            reader,
            column_map=column_map,
            fieldnames=reader.fieldnames,
        )
    logger.info(
        "Loaded Cookie Cats CSV %s: %d rows kept from %d read (dropped: %d "
        "missing-field, %d unparseable, %d bad-version)",
        path.name,
        summary.rows_kept,
        summary.rows_read,
        summary.rows_dropped_missing_field,
        summary.rows_dropped_unparseable,
        summary.rows_dropped_bad_version,
    )
    return rows, summary


def fetch_cookiecats_archive(dest_path: str | Path, *, timeout: float = 120.0) -> Path:
    """GATED download of the public Cookie Cats CSV to `dest_path`.

    Refuses to run under pytest / CI — fetching the real dataset is a deliberate
    manual step, never a test or CI side effect (same guard
    `benchmark_runner.score_with_engine` / `hillstrom_archive.fetch_hillstrom_archive`
    apply). Use a pre-downloaded file with `load_cookiecats_csv` in every
    automated context. The raw CSV is NEVER committed (fetch-don't-redistribute).

    Validates that the response looks like the Cookie Cats CSV (header contains
    the `version` column) before writing, so a moved URL or an HTML error page
    fails loudly instead of silently saving garbage. Returns the path written.
    """
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "fetch_cookiecats_archive downloads the live public dataset and must "
            "not run under pytest / CI. Pre-download the CSV once, then point "
            "load_cookiecats_csv at the local file in tests and automation. The raw "
            "CSV is never committed (fetch-don't-redistribute)."
        )

    import urllib.request

    dest = Path(dest_path)
    logger.info("Fetching Cookie Cats A/B CSV from %s", FETCH_URL)
    req = urllib.request.Request(FETCH_URL, headers={"User-Agent": "sidira-benchmark-loader/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed mirror URL
        data = resp.read()

    # Defensive content check: the first line must carry the key arm column so a
    # moved URL or HTML error page fails loudly rather than saving garbage.
    head = data[:4096].decode("utf-8", errors="replace").splitlines()
    first_line = head[0] if head else ""
    if DEFAULT_COLUMN_MAP["version"] not in first_line:
        raise RuntimeError(
            "Downloaded content does not look like the Cookie Cats CSV (header "
            f"missing {DEFAULT_COLUMN_MAP['version']!r}). The URL may have moved "
            f"or the host returned an error page. Verify {FETCH_URL}."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    logger.info("Wrote %d bytes to %s", len(data), dest)
    return dest


# ── offline persona-pack build ───────────────────────────────────────────────
#
# The Cookie Cats directional benchmark needs a REAL v1.1 persona pack built from
# the player engagement feature. Cookie Cats carries ONLY `sum_gamerounds` as a
# pre-treatment covariate (the retention outcomes must be EXCLUDED — they are the
# answer key). With one continuous feature the GMM clusters players into
# engagement tiers (low / mid / heavy). The pack is built ONCE offline from the
# fetched CSV by the sidira-personas GMM pipeline and the DERIVED pack JSON is
# committed (`adapters/cookiecats_panel_v1.json`). It is statistics (cluster
# centroids + privacy-clean synthetic GMM draws), NOT raw rows, so it is safe to
# redistribute — unlike the raw CSV, which is never committed.
#
# The build is gated (refuses under pytest / CI) for the SAME reason as the
# fetcher and `score_with_engine`: it imports the heavy ML stack (pandas /
# scikit-learn via the separate `sidira-personas` repo) which is intentionally
# absent from the API image, and it is a deliberate, reproducible offline step.
# Tests validate the COMMITTED pack instead.
#
# KNOWN GAP — behavioral_seeds (cross-persona texture). As with the Hillstrom
# pack, the producer emits no behavioral_seeds; the committed pack carries
# behavioral_seeds=None and the simulator's identity_seed falls back to its
# generic default pools, flagged honestly via AgentReaction.behavioral_seeds_
# fallback. The Cookie Cats trial carries NO age / locale / tenure / gripe signal
# (only engagement), so populating those pools could only be fabricated. The
# WITHIN-persona individual-row path still fires correctly on the v1.1 quad.

# The producer column → FeatureGroup map, frozen here as the pre-registered
# feature-mapping for the build (researcher-DOF freeze). The outcome columns
# (version / retention_1 / retention_7) are DELIBERATELY absent: they must never
# enter the clustering or the pack would leak the answer key into the persona
# identities. Adapter types are pinned (not inferred) so the build is reproducible
# byte-for-byte from this source.
COOKIECATS_FEATURE_GROUPS: dict[str, list[dict[str, str]]] = {
    "engagement_intensity": [
        {"name": "sum_gamerounds", "type": "count"},
    ],
}

# k is FIXED at 3 (low / mid / heavy engagement tiers). A single continuous
# feature naturally separates into a small number of engagement tiers; 3 keeps
# each cluster well-populated (the dataset's sum_gamerounds is heavily
# right-skewed) while still giving distinct centroids. k is pinned, not BIC-auto,
# so the offline build is reproducible.
COOKIECATS_PANEL_K = 3

# The pre-registered panel id (the PersonaPack.version, reported as panel_id so a
# run is traceable to the exact population).
COOKIECATS_PANEL_VERSION = "cookiecats-gate-ab-v1"


def _cookiecats_pipeline_config() -> dict:
    """The frozen sidira-personas pipeline config for the Cookie Cats pack build.

    Mirrors the shape `persona_builder._build_pipeline_config` produces, but with
    adapter types and k PINNED (not inferred) so the offline build is reproducible.
    """
    return {
        "company_id": "cookiecats",
        "run_id_prefix": "cookiecats",
        "source": {"type": "local", "user_id_column": "userid"},
        "feature_groups": COOKIECATS_FEATURE_GROUPS,
        "clustering_exclude_groups": [],
        "encoder": {"method": "pca", "embedding_dim_per_group": 1},
        "cluster": {
            "method": "gmm",
            "k_range": [COOKIECATS_PANEL_K, COOKIECATS_PANEL_K],
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


def build_cookiecats_panel_pack(csv_path: str | Path):
    """Build the DERIVED Cookie Cats v1.1 persona pack from a local CSV (gated).

    Loads the local Cookie Cats CSV, runs the `sidira-personas` GMM pipeline over
    the engagement feature (outcomes excluded), and translates the producer pack
    into the simulator's :class:`PersonaPack` (carrying the v1.1 quad so the
    individual-row tier fires). Returns the validated `PersonaPack`; the caller
    writes the JSON to `adapters/cookiecats_panel_v1.json`.

    GATED: refuses under pytest / CI. It imports the heavy ML stack (pandas +
    `sidira-personas`, absent from the API image) and is a deliberate offline
    build, never a test side effect. Tests validate the committed pack.

    Raises RuntimeError under pytest / CI or if `sidira-personas` is not installed.
    """
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "build_cookiecats_panel_pack imports the heavy ML stack and runs the GMM "
            "pipeline; it must not run under pytest / CI. The committed pack "
            "(adapters/cookiecats_panel_v1.json) is what tests validate; rebuild it "
            "offline with this function when the source / mapping changes."
        )

    try:
        import pandas as pd

        from sidira_personas import run_pipeline
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "sidira-personas not installed — install it (Python 3.11+) to rebuild "
            "the Cookie Cats persona pack: `python3.11 -m pip install -e "
            "~/Projects/sidira-personas`."
        ) from exc

    from sidira_simulator.services.persona_pack_translator import translate_producer_pack

    rows, summary = load_cookiecats_csv(csv_path)
    if not rows:
        raise RuntimeError(f"no Cookie Cats rows loaded from {csv_path} — cannot build pack")
    logger.info("Building Cookie Cats panel pack from %d rows", summary.rows_kept)

    df = pd.DataFrame([{"userid": r.userid, "sum_gamerounds": r.sum_gamerounds} for r in rows])

    result = run_pipeline(
        df, _cookiecats_pipeline_config(), run_id=COOKIECATS_PANEL_VERSION, no_llm=True
    )
    from dataclasses import asdict

    producer_pack = asdict(result.pack)
    pack = translate_producer_pack(producer_pack, version=COOKIECATS_PANEL_VERSION)
    logger.info(
        "Built Cookie Cats pack: k=%d, %d personas, stability=%.3f",
        result.pack.k_selected,
        len(pack.personas),
        pack.stability_score,
    )
    return pack


def write_cookiecats_panel_pack(csv_path: str | Path, dest_path: str | Path) -> Path:
    """Build + serialize the Cookie Cats panel pack to `dest_path` (gated).

    The reproducible offline build entry point: regenerates the committed
    `adapters/cookiecats_panel_v1.json`. Refuses under pytest / CI via
    :func:`build_cookiecats_panel_pack`. Returns the path written.
    """
    pack = build_cookiecats_panel_pack(csv_path)
    dest = Path(dest_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(pack.model_dump_json(indent=2))
    logger.info("Wrote Cookie Cats panel pack to %s", dest)
    return dest
