"""Tests for the Hillstrom CSV loader (#222 Hillstrom ingestion).

Mirrors `test_upworthy_archive`: the pure parse core is exercised on a tiny inline
CSV fixture (no file I/O), drops are counted and surfaced (no silent truncation),
a missing required column raises loud, and the gated network fetch refuses under
pytest / CI.
"""

from __future__ import annotations

import csv
import io

import pytest

from sidira_simulator.services.hillstrom_archive import (
    HillstromRow,
    fetch_hillstrom_archive,
    load_hillstrom_csv,
    parse_hillstrom_rows,
)

_HEADER = (
    "recency,history_segment,history,mens,womens,zip_code,newbie,channel,"
    "segment,visit,conversion,spend"
)


def _rows(*lines: str):
    return csv.DictReader(io.StringIO("\n".join((_HEADER, *lines))))


def test_parse_typed_rows_on_inline_fixture() -> None:
    rows, summary = parse_hillstrom_rows(
        _rows(
            "1,1) $0 - $100,142.44,1,0,Surburban,0,Phone,Mens E-Mail,1,1,42.0",
            "6,2) $100 - $200,329.08,0,1,Rural,1,Web,Womens E-Mail,1,0,0.0",
            "9,1) $0 - $100,180.65,1,0,Urban,0,Multichannel,No E-Mail,0,0,0.0",
        )
    )
    assert summary.rows_read == 3
    assert summary.rows_kept == 3
    assert all(isinstance(r, HillstromRow) for r in rows)
    first = rows[0]
    assert first.recency == 1
    assert first.history == pytest.approx(142.44)
    assert first.mens == 1 and first.womens == 0
    assert first.segment == "Mens E-Mail"
    assert first.visit == 1 and first.conversion == 1
    assert first.spend == pytest.approx(42.0)


def test_bad_segment_is_dropped_and_counted() -> None:
    rows, summary = parse_hillstrom_rows(
        _rows(
            "1,1) $0 - $100,100.0,1,0,Urban,0,Web,Mens E-Mail,1,1,10.0",
            "1,1) $0 - $100,100.0,1,0,Urban,0,Web,Bogus Arm,1,1,10.0",
        )
    )
    assert summary.rows_read == 2
    assert summary.rows_kept == 1
    assert summary.rows_dropped_bad_segment == 1
    assert rows[0].segment == "Mens E-Mail"
    assert any("Bogus Arm" in r for r in summary.drop_reasons)


def test_unparseable_numeric_is_dropped_and_counted() -> None:
    rows, summary = parse_hillstrom_rows(
        _rows(
            "1,1) $0 - $100,not-a-number,1,0,Urban,0,Web,No E-Mail,0,0,0.0",
            "1,1) $0 - $100,100.0,1,0,Urban,0,Web,No E-Mail,0,0,0.0",
        )
    )
    assert summary.rows_kept == 1
    assert summary.rows_dropped_unparseable == 1


def test_non_binary_outcome_is_dropped() -> None:
    _rows_, summary = parse_hillstrom_rows(
        _rows("1,1) $0 - $100,100.0,1,0,Urban,0,Web,No E-Mail,2,0,0.0"),
    )
    assert summary.rows_kept == 0
    assert summary.rows_dropped_unparseable == 1


def test_missing_required_field_drops_row() -> None:
    rows, summary = parse_hillstrom_rows(
        _rows(
            "1,,100.0,1,0,Urban,0,Web,No E-Mail,0,0,0.0",  # blank history_segment
            "1,1) $0 - $100,100.0,1,0,Urban,0,Web,No E-Mail,0,0,0.0",
        )
    )
    assert summary.rows_kept == 1
    assert summary.rows_dropped_missing_field == 1


def test_missing_required_column_raises_loud() -> None:
    bad_header = _HEADER.replace(",segment,", ",arm,")
    reader = csv.DictReader(io.StringIO(bad_header + "\n1,x,1.0,1,0,Z,0,Web,No E-Mail,0,0,0.0"))
    with pytest.raises(ValueError, match="missing required column"):
        parse_hillstrom_rows(reader)


def test_renamed_column_bound_via_column_map() -> None:
    header = _HEADER.replace(",segment,", ",arm,")
    reader = csv.DictReader(
        io.StringIO(header + "\n1,1) $0 - $100,100.0,1,0,Urban,0,Web,No E-Mail,0,0,0.0")
    )
    rows, summary = parse_hillstrom_rows(reader, column_map={"segment": "arm"})
    assert summary.rows_kept == 1
    assert rows[0].segment == "No E-Mail"


def test_empty_input_returns_empty() -> None:
    rows, summary = parse_hillstrom_rows(iter([]))
    assert rows == []
    assert summary.rows_read == 0


def test_load_hillstrom_csv_reads_local_file(tmp_path) -> None:
    p = tmp_path / "hillstrom.csv"
    p.write_text(
        "\n".join(
            (
                _HEADER,
                "1,1) $0 - $100,100.0,1,0,Urban,0,Web,Mens E-Mail,1,1,10.0",
                "2,2) $100 - $200,200.0,0,1,Rural,1,Phone,No E-Mail,0,0,0.0",
            )
        ),
        encoding="utf-8",
    )
    rows, summary = load_hillstrom_csv(p)
    assert summary.rows_kept == 2
    assert {r.segment for r in rows} == {"Mens E-Mail", "No E-Mail"}


def test_fetch_refuses_under_pytest(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="must\\s+not run under pytest / CI"):
        fetch_hillstrom_archive(tmp_path / "out.csv")


def test_fetch_refuses_under_ci(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CI", "true")
    with pytest.raises(RuntimeError, match="must\\s+not run under pytest / CI"):
        fetch_hillstrom_archive(tmp_path / "out.csv")
