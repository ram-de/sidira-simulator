"""CSV connector (#19) — works end-to-end NOW, no credentials required.

Parses an uploaded CSV into normalized ``{column -> value}`` rows, profiles its
columns for the mapping UI, and ships a downloadable sample + template so the
customer can see the expected shape. The actual field mapping + Experiment
construction lives in :mod:`mapping` (the firewall boundary); this module only
handles the CSV-specific I/O.
"""

from __future__ import annotations

import csv
import io

from sidira_simulator.schemas.connector import ColumnProfile

# The canonical column order for the downloadable template + sample. Matches the
# nine Experiment fields the mapping targets (variants delimited by '|').
TEMPLATE_COLUMNS: tuple[str, ...] = (
    "change_description",
    "variants",
    "primary_metric",
    "category",
    "winner",
    "result",
    "effect_size_pct",
    "n",
    "date",
)

# A small, realistic sample so a customer can download → edit → re-upload. Three
# rows spanning win/loss/flat and three of the four categories, so a fresh CSV
# import is demoable without any real data file. Mirrors the seed-archive voice.
_SAMPLE_ROWS: tuple[tuple[str, ...], ...] = (
    (
        "Reframe the pricing-page headline from feature-led to outcome-led",
        "feature headline|outcome headline",
        "pricing page signup rate",
        "copy",
        "outcome headline",
        "win",
        "9.4",
        "10250",
        "2024-09-03",
    ),
    (
        "Add an urgency countdown banner to the cart page",
        "no banner|countdown banner",
        "cart conversion rate",
        "ui",
        "no banner",
        "loss",
        "-6.1",
        "14800",
        "2024-10-17",
    ),
    (
        "Switch the trial length from 14 to 30 days",
        "14-day trial|30-day trial",
        "trial-to-paid conversion",
        "flow",
        "no winner",
        "flat",
        "0.7",
        "8200",
        "2024-11-05",
    ),
)


class CsvParseError(ValueError):
    """The uploaded bytes could not be read as CSV (encoding / malformed)."""


def parse_csv(raw: bytes) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV bytes into (header columns, normalized rows).

    Every value is coerced to a stripped string so downstream mapping treats all
    connectors uniformly. Raises :class:`CsvParseError` on an undecodable or
    headerless file rather than guessing.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CsvParseError(
            "file is not valid UTF-8 text — re-export the CSV as UTF-8"
        ) from exc

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None or not any(
        (name or "").strip() for name in reader.fieldnames
    ):
        raise CsvParseError("CSV has no header row")

    columns = [(name or "").strip() for name in reader.fieldnames]

    # Reject ambiguous headers UP FRONT. csv.DictReader silently collapses
    # duplicate column names (last value wins) and turns a blank header into an
    # un-addressable column — either makes the field mapping ambiguous (which
    # source column did the customer mean?), so we refuse rather than guess
    # (MAJOR 6).
    if any(not name for name in columns):
        raise CsvParseError(
            "CSV has a blank column header — every column must be named so the "
            "mapping is unambiguous"
        )
    seen: set[str] = set()
    duplicates: list[str] = []
    for name in columns:
        key = name.lower()
        if key in seen and name not in duplicates:
            duplicates.append(name)
        seen.add(key)
    if duplicates:
        raise CsvParseError(
            "CSV has duplicate column header(s): "
            + ", ".join(sorted(duplicates))
            + " — rename them so the mapping is unambiguous"
        )
    rows: list[dict[str, str]] = []
    for raw_row in reader:
        rows.append(
            {
                (k or "").strip(): (v if isinstance(v, str) else "").strip()
                for k, v in raw_row.items()
                if k is not None
            }
        )
    return columns, rows


def profile_columns(
    columns: list[str], rows: list[dict[str, str]], *, sample_size: int = 3
) -> list[ColumnProfile]:
    """Build per-column sample values for the mapping UI (non-empty, deduped)."""
    profiles: list[ColumnProfile] = []
    for col in columns:
        seen: list[str] = []
        for row in rows:
            val = row.get(col, "")
            if val and val not in seen:
                seen.append(val)
            if len(seen) >= sample_size:
                break
        profiles.append(ColumnProfile(name=col, sample_values=seen))
    return profiles


def template_csv() -> str:
    """The downloadable header-only template (the expected column shape)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_COLUMNS)
    return buf.getvalue()


def sample_csv() -> str:
    """A downloadable filled-in sample CSV (header + a few realistic rows)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(TEMPLATE_COLUMNS)
    for row in _SAMPLE_ROWS:
        writer.writerow(row)
    return buf.getvalue()
