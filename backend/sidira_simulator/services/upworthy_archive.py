"""Upworthy Research Archive → `UpworthyTest` loader (#222 Tier-0 ingestion).

The benchmark harness (adapter → runner → null-cert → honesty-table →
pre-registration) and the archive → `Hypothesis` *adapter*
(`services.benchmark_adapter`) are built. The missing link this module supplies
is the *ingestion* edge: turning the real, public Upworthy Research Archive CSV
into `UpworthyTest` objects whose shape feeds `build_upworthy_case` /
`upworthy_test_to_cases` directly.

Two halves, deliberately separated:

  - `load_upworthy_archive(csv_path, ...)` — pure-ish parse/group of an
    ALREADY-PRESENT local CSV (stdlib `csv`, no pandas). Groups rows by
    `clickability_test_id`, builds one `UpworthyTest` per group, and reports a
    `LoadSummary` of what was dropped and why — no silent truncation. The
    parsing core (`parse_upworthy_rows`) takes an iterable of dict rows so it is
    testable on an in-memory CSV string with zero file I/O.

  - `fetch_upworthy_archive(dest_path)` — a GATED helper that downloads the
    public CSV. It refuses to run under pytest / CI (same guard
    `benchmark_runner.score_with_engine` uses): fetching is a deliberate manual
    step, never a test/CI side effect. The loader operates on the resulting file.

CTR is intentionally NOT computed here: the adapter's `_ground_truth` derives it
from clicks / impressions. The loader only carries the raw counts plus the image
identity, exactly as `UpworthyVariant` requires.
"""

from __future__ import annotations

import csv
import logging
import math
import os
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from itertools import chain
from pathlib import Path
from typing import Iterable, Mapping

from pydantic import ValidationError

from sidira_simulator.schemas.benchmark import UpworthyTest, UpworthyVariant

logger = logging.getLogger(__name__)

# ── public archive coordinates ───────────────────────────────────────────────
#
# The Upworthy Research Archive (Matias et al., Scientific Data 2021;
# https://www.nature.com/articles/s41597-021-00934-7) is published CC-BY 4.0 on
# the Open Science Framework. The canonical project is osf.io/jd64p; the
# *exploratory* split this loader targets is the file
# `upworthy-archive-exploratory-packages-03.12.2020.csv` (≈22.7k packages across
# ≈4.9k tests). One CSV row is one tested headline package; rows sharing a
# `clickability_test_id` form one A/B/n test.
#
# OSF serves a stable per-file download endpoint at
# https://osf.io/<file_id>/download. The exploratory-packages file id is set
# below; if OSF re-keys the file, update FETCH_OSF_FILE_ID — `fetch_upworthy_
# archive` validates the response is CSV-shaped before writing, so a stale id
# fails loudly rather than silently saving an HTML error page.
ARCHIVE_PROJECT_URL = "https://osf.io/jd64p/"
ARCHIVE_FILENAME = "upworthy-archive-exploratory-packages-03.12.2020.csv"
# File-level OSF id (guid) for the exploratory-packages CSV. Confirm against the
# live project (osf.io/jd64p → upworthy-archive-datasets/) before a fetch run.
# Verified 2026-06-15 via the OSF API (api.osf.io/v2/nodes/jd64p/files/osfstorage/)
# against `upworthy-archive-exploratory-packages-03.12.2020.csv` (≈14.3 MB,
# 22,666 package rows); a successful fetch + header check confirmed the guid.
FETCH_OSF_FILE_ID = "3vqmp"
FETCH_URL = f"https://osf.io/{FETCH_OSF_FILE_ID}/download"

# Default archive column → loader field mapping. Verified against the archive's
# data dictionary (upworthy.natematias.com/about-the-archive.html). Defensive by
# design: pass a partial `column_map` to override any single name if the archive
# is re-published with a renamed column, without touching the rest.
DEFAULT_COLUMN_MAP: dict[str, str] = {
    "test_id": "clickability_test_id",
    "headline": "headline",
    "clicks": "clicks",
    "impressions": "impressions",
    "eyecatcher_id": "eyecatcher_id",
}


@dataclass
class LoadSummary:
    """Honest accounting of one load: what became a test, what was dropped, why.

    Every input row is conserved: ``rows_read`` equals the rows that landed in a
    retained test plus every per-row and per-group drop. Nothing is silently
    truncated — a caller can assert full coverage from these counts.
    """

    rows_read: int = 0
    tests_built: int = 0
    variants_kept: int = 0
    rows_dropped_missing_field: int = 0
    rows_dropped_unparseable: int = 0
    rows_dropped_invalid_variant: int = 0
    groups_dropped_too_few_variants: int = 0
    groups_dropped_low_impressions: int = 0
    drop_reasons: list[str] = field(default_factory=list)

    def note(self, reason: str) -> None:
        # Keep a bounded, human-readable trail without exploding memory on a
        # 150k-row file: record the first handful of each kind via the caller's
        # discretion (callers append specific, deduplicated reasons).
        self.drop_reasons.append(reason)


def _parse_int(raw: str | None) -> int | None:
    """Parse an archive integer cell, tolerating floats like ``"1000.0"``.

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
        # NaN / inf / -inf parse as floats but cannot become ints — pandas/R
        # exports encode missing numerics this way. Treat them as unparseable
        # (caller drops + counts the row) rather than letting int() crash the
        # whole load.
        if not math.isfinite(f) or f != int(f):
            return None
        return int(f)


def _clean(raw: str | None) -> str:
    return raw.strip() if raw is not None else ""


def parse_upworthy_rows(
    rows: Iterable[Mapping[str, str]],
    *,
    column_map: Mapping[str, str] | None = None,
    min_variants: int = 2,
    min_impressions: int = 1,
    fieldnames: Iterable[str] | None = None,
) -> tuple[list[UpworthyTest], LoadSummary]:
    """Group archive rows into `UpworthyTest`s. The pure, I/O-free core.

    Parameters mirror `load_upworthy_archive`; this variant takes an iterable of
    already-parsed dict rows (e.g. from `csv.DictReader`, or a hand-built list in
    tests) so the grouping logic is exercised without touching the filesystem.

    Grouping: rows are bucketed by the mapped `test_id` column in first-seen
    order (deterministic output). Each surviving row becomes one
    `UpworthyVariant` (headline, clicks, impressions, eyecatcher_id). A group is
    retained only if it has ≥ `min_variants` variants AND total impressions ≥
    `min_impressions`; otherwise the whole group is dropped with a recorded
    reason. CTR is never computed here — the adapter derives it.

    Column presence is verified up front (from `fieldnames` if given, else from
    the first row's keys). A MISSING mapped column — including
    `eyecatcher_id` — is a structural ingestion error that raises `ValueError`,
    NOT a silent per-row drop: an absent eyecatcher column must never be read as
    "every card has no image" (the `UpworthyVariant.eyecatcher_id` contract). A
    *blank cell* in a present column remains the legitimate None no-image
    sentinel.
    """
    cmap = {**DEFAULT_COLUMN_MAP, **(column_map or {})}
    col_test = cmap["test_id"]
    col_headline = cmap["headline"]
    col_clicks = cmap["clicks"]
    col_impressions = cmap["impressions"]
    col_eyecatcher = cmap["eyecatcher_id"]
    required = (col_test, col_headline, col_clicks, col_impressions, col_eyecatcher)

    rows = iter(rows)
    if fieldnames is None:
        # Peek the first row to learn the header, then chain it back so it is
        # still parsed. A header-less / empty input has no columns to check.
        try:
            first = next(rows)
        except StopIteration:
            return [], LoadSummary()
        present = set(first.keys())
        rows = chain([first], rows)
    else:
        present = set(fieldnames)

    missing = [c for c in required if c not in present]
    if missing:
        raise ValueError(
            f"Upworthy archive CSV is missing required column(s) {missing}; "
            f"present columns: {sorted(present)}. Pass a `column_map` to bind "
            "renamed columns. A missing eyecatcher column must not be silently "
            "read as 'no image' — fix the mapping."
        )

    summary = LoadSummary()
    # Buffer per group: list of validated variants, applied the group-level
    # min_variants / min_impressions floors after seeing every row in the group.
    buckets: "OrderedDict[str, list[UpworthyVariant]]" = OrderedDict()
    # Every test_id that appeared with a usable id, in first-seen order — even if
    # all its rows were later dropped. Lets a fully-collapsed group (e.g. every
    # row failed the schema) still surface a group-level drop reason instead of
    # vanishing without a trace.
    seen_test_ids: "OrderedDict[str, None]" = OrderedDict()

    for row in rows:
        summary.rows_read += 1

        test_id = _clean(row.get(col_test))
        headline = _clean(row.get(col_headline))
        if not test_id or not headline:
            summary.rows_dropped_missing_field += 1
            continue
        seen_test_ids.setdefault(test_id, None)

        clicks = _parse_int(row.get(col_clicks))
        impressions = _parse_int(row.get(col_impressions))
        if clicks is None or impressions is None:
            summary.rows_dropped_unparseable += 1
            continue

        # eyecatcher: a present id names the image; a blank cell is the explicit
        # "no distinguishing image on this card" sentinel (None) — the contract
        # documented on UpworthyVariant.eyecatcher_id.
        eyecatcher_raw = _clean(row.get(col_eyecatcher))
        eyecatcher_id: str | None = eyecatcher_raw or None

        try:
            variant = UpworthyVariant(
                headline=headline,
                clicks=clicks,
                impressions=impressions,
                eyecatcher_id=eyecatcher_id,
            )
        except ValidationError:
            # impressions <= 0, clicks > impressions, etc. — the schema's
            # boundary guards. Drop the single bad row, keep the load going.
            summary.rows_dropped_invalid_variant += 1
            continue

        buckets.setdefault(test_id, []).append(variant)

    tests: list[UpworthyTest] = []
    for test_id in seen_test_ids:
        variants = buckets.get(test_id, [])
        if len(variants) < min_variants:
            summary.groups_dropped_too_few_variants += 1
            summary.note(f"{test_id}: {len(variants)} variant(s) < min_variants={min_variants}")
            continue
        total_impressions = sum(v.impressions for v in variants)
        if total_impressions < min_impressions:
            summary.groups_dropped_low_impressions += 1
            summary.note(
                f"{test_id}: total impressions {total_impressions} < "
                f"min_impressions={min_impressions}"
            )
            continue
        try:
            test = UpworthyTest(test_id=test_id, variants=variants)
        except ValidationError as exc:  # pragma: no cover - guarded above
            summary.groups_dropped_too_few_variants += 1
            summary.note(f"{test_id}: rejected by UpworthyTest schema ({exc.error_count()} errs)")
            continue
        tests.append(test)
        summary.tests_built += 1
        summary.variants_kept += len(variants)

    return tests, summary


def load_upworthy_archive(
    csv_path: str | Path,
    *,
    column_map: Mapping[str, str] | None = None,
    min_variants: int = 2,
    min_impressions: int = 1,
    encoding: str = "utf-8",
) -> tuple[list[UpworthyTest], LoadSummary]:
    """Load a LOCAL Upworthy archive CSV into `UpworthyTest`s.

    Thin file-I/O wrapper over `parse_upworthy_rows`: opens `csv_path` with
    stdlib `csv.DictReader` and delegates all grouping / validation / drop
    accounting to the pure core. Returns the retained tests and a `LoadSummary`.

    This never downloads anything — the file must already be present (use the
    gated `fetch_upworthy_archive` for the deliberate one-time download).
    """
    path = Path(csv_path)
    with path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        tests, summary = parse_upworthy_rows(
            reader,
            column_map=column_map,
            min_variants=min_variants,
            min_impressions=min_impressions,
            fieldnames=reader.fieldnames,
        )
    logger.info(
        "Loaded Upworthy archive %s: %d tests / %d variants from %d rows "
        "(dropped: %d missing-field, %d unparseable, %d invalid-variant, "
        "%d groups<%d-variants, %d groups<%d-impressions)",
        path.name,
        summary.tests_built,
        summary.variants_kept,
        summary.rows_read,
        summary.rows_dropped_missing_field,
        summary.rows_dropped_unparseable,
        summary.rows_dropped_invalid_variant,
        summary.groups_dropped_too_few_variants,
        min_variants,
        summary.groups_dropped_low_impressions,
        min_impressions,
    )
    return tests, summary


def fetch_upworthy_archive(dest_path: str | Path, *, timeout: float = 120.0) -> Path:
    """GATED download of the public exploratory-packages CSV to `dest_path`.

    Refuses to run under pytest / CI — fetching the real archive is a deliberate
    manual step, never a test or CI side effect (same guard
    `benchmark_runner.score_with_engine` applies). Use a pre-downloaded file with
    `load_upworthy_archive` in every automated context.

    Validates that the response looks like the archive CSV (header contains the
    `clickability_test_id` column) before writing, so a re-keyed OSF id or an OSF
    HTML error page fails loudly instead of silently saving garbage. Returns the
    path written.
    """
    # Refuse under pytest AND under CI. The pytest checks catch the test harness;
    # the CI check catches a script/helper running in CI outside pytest, where
    # the standard `CI` env var (set by GitHub Actions, GitLab, etc.) is truthy —
    # so an automated job can never accidentally hit the live network.
    if (
        "PYTEST_CURRENT_TEST" in os.environ
        or "pytest" in sys.modules
        or os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}
    ):
        raise RuntimeError(
            "fetch_upworthy_archive downloads the live public archive and must "
            "not run under pytest / CI. Pre-download the CSV once, then point "
            "load_upworthy_archive at the local file in tests and automation."
        )

    import urllib.request

    dest = Path(dest_path)
    logger.info("Fetching Upworthy exploratory-packages archive from %s", FETCH_URL)
    req = urllib.request.Request(FETCH_URL, headers={"User-Agent": "sidira-benchmark-loader/1"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 - fixed https OSF URL
        data = resp.read()

    # Defensive content check: the first line must carry the key archive column.
    head = data[:4096].decode("utf-8", errors="replace").splitlines()
    first_line = head[0] if head else ""
    if DEFAULT_COLUMN_MAP["test_id"] not in first_line:
        raise RuntimeError(
            "Downloaded content does not look like the Upworthy archive CSV "
            f"(header missing {DEFAULT_COLUMN_MAP['test_id']!r}). The OSF file id "
            f"({FETCH_OSF_FILE_ID}) may be stale or OSF returned an error page. "
            f"Verify the file at {ARCHIVE_PROJECT_URL} and update FETCH_OSF_FILE_ID."
        )

    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    logger.info("Wrote %d bytes to %s", len(data), dest)
    return dest
