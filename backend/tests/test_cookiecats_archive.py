"""Tests for the Cookie Cats CSV loader (in-scope product-change benchmark).

Mirrors `test_hillstrom_archive`: the pure parse core is exercised on a tiny
inline CSV fixture (no file I/O), drops are counted and surfaced (no silent
truncation), a missing required column raises loud, boolean retention cells parse
in all accepted spellings, and the gated network fetch refuses under pytest / CI.
"""

from __future__ import annotations

import csv
import io

import pytest

from sidira_simulator.services.cookiecats_archive import (
    CookieCatsRow,
    fetch_cookiecats_archive,
    load_cookiecats_csv,
    parse_cookiecats_rows,
)

_HEADER = "userid,version,sum_gamerounds,retention_1,retention_7"


def _rows(*lines: str):
    return csv.DictReader(io.StringIO("\n".join((_HEADER, *lines))))


def test_parse_typed_rows_on_inline_fixture() -> None:
    rows, summary = parse_cookiecats_rows(
        _rows(
            "116,gate_30,3,False,False",
            "337,gate_30,38,True,False",
            "377,gate_40,165,True,True",
        )
    )
    assert summary.rows_read == 3
    assert summary.rows_kept == 3
    assert all(isinstance(r, CookieCatsRow) for r in rows)
    first = rows[0]
    assert first.userid == 116
    assert first.version == "gate_30"
    assert first.sum_gamerounds == 3
    assert first.retention_1 == 0 and first.retention_7 == 0
    assert rows[2].retention_1 == 1 and rows[2].retention_7 == 1


def test_boolean_spellings_accepted() -> None:
    """True/False, 1/0, true/false all parse to 0/1; an unknown token drops."""
    rows, summary = parse_cookiecats_rows(
        _rows(
            "1,gate_30,10,True,False",
            "2,gate_40,20,1,0",
            "3,gate_30,30,true,FALSE",
            "4,gate_40,40,maybe,True",  # unparseable retention_1 → drop
        )
    )
    assert summary.rows_kept == 3
    assert summary.rows_dropped_unparseable == 1
    assert [r.retention_1 for r in rows] == [1, 1, 1]
    assert [r.retention_7 for r in rows] == [0, 0, 0]


def test_bad_version_is_dropped_and_counted() -> None:
    rows, summary = parse_cookiecats_rows(
        _rows(
            "1,gate_30,10,True,False",
            "2,gate_50,20,True,False",  # not one of the two arms
        )
    )
    assert summary.rows_read == 2
    assert summary.rows_kept == 1
    assert summary.rows_dropped_bad_version == 1
    assert rows[0].version == "gate_30"
    assert any("gate_50" in r for r in summary.drop_reasons)


def test_unparseable_numeric_is_dropped_and_counted() -> None:
    rows, summary = parse_cookiecats_rows(
        _rows(
            "1,gate_30,not-a-number,True,False",
            "2,gate_40,20,True,False",
        )
    )
    assert summary.rows_kept == 1
    assert summary.rows_dropped_unparseable == 1


def test_missing_required_field_drops_row() -> None:
    rows, summary = parse_cookiecats_rows(
        _rows(
            "1,,10,True,False",  # blank version
            "2,gate_40,20,True,False",
        )
    )
    assert summary.rows_kept == 1
    assert summary.rows_dropped_missing_field == 1


def test_missing_required_column_raises_loud() -> None:
    bad_header = _HEADER.replace(",version,", ",arm,")
    reader = csv.DictReader(io.StringIO(bad_header + "\n1,gate_30,10,True,False"))
    with pytest.raises(ValueError, match="missing required column"):
        parse_cookiecats_rows(reader)


def test_renamed_column_bound_via_column_map() -> None:
    header = _HEADER.replace(",version,", ",arm,")
    reader = csv.DictReader(io.StringIO(header + "\n1,gate_30,10,True,False"))
    rows, summary = parse_cookiecats_rows(reader, column_map={"version": "arm"})
    assert summary.rows_kept == 1
    assert rows[0].version == "gate_30"


def test_empty_input_returns_empty() -> None:
    rows, summary = parse_cookiecats_rows(iter([]))
    assert rows == []
    assert summary.rows_read == 0


def test_load_cookiecats_csv_reads_local_file(tmp_path) -> None:
    p = tmp_path / "cookie_cats.csv"
    p.write_text(
        "\n".join(
            (
                _HEADER,
                "1,gate_30,10,True,False",
                "2,gate_40,20,False,True",
            )
        ),
        encoding="utf-8",
    )
    rows, summary = load_cookiecats_csv(p)
    assert summary.rows_kept == 2
    assert {r.version for r in rows} == {"gate_30", "gate_40"}


def test_fetch_refuses_under_pytest(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="must\\s+not run under pytest / CI"):
        fetch_cookiecats_archive(tmp_path / "out.csv")


def test_fetch_refuses_under_ci(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("CI", "true")
    with pytest.raises(RuntimeError, match="must\\s+not run under pytest / CI"):
        fetch_cookiecats_archive(tmp_path / "out.csv")
