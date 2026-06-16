"""Tests for the Upworthy Research Archive loader (#222 Tier-0 ingestion).

The loader's job is to turn the real public archive CSV into `UpworthyTest`
objects that flow straight into the adapter — so the assertions here are:
1. grouping by `clickability_test_id` builds one test per group with the right
   variant fields (clicks / impressions / eyecatcher);
2. drops are HONEST — <2 variants and zero-impression groups are dropped and
   *counted*, never silently truncated;
3. a `column_map` override absorbs a renamed column;
4. the output flows into `build_upworthy_case` / `upworthy_test_to_cases` with no
   error (integration smoke);
5. nothing is downloaded, and `fetch_upworthy_archive` refuses under pytest.
"""

from __future__ import annotations

import io

import pytest

from sidira_simulator.schemas.benchmark import UpworthyTest
from sidira_simulator.services.benchmark_adapter import (
    build_upworthy_case,
    upworthy_test_to_cases,
)
from sidira_simulator.services.upworthy_archive import (
    DEFAULT_COLUMN_MAP,
    FETCH_URL,
    fetch_upworthy_archive,
    load_upworthy_archive,
    parse_upworthy_rows,
)

# A small archive in the real column layout. Tests:
#   t1 — 2 variants, same eyecatcher → valid headline swap, retained
#   t2 — 1 variant → dropped (too few variants)
#   t3 — 2 variants but BOTH zero impressions → variants rejected at schema
#         (impressions must be > 0), so the group collapses to 0 variants → dropped
#   t4 — 3 variants, differing eyecatchers → retained (adapter decides per-pair)
EMBEDDED_CSV = """clickability_test_id,headline,eyecatcher_id,impressions,clicks,slug
t1,Headline A about a dog,img_a,10000,150,dog-a
t1,Headline B about a dog,img_a,10000,210,dog-b
t2,Lonely single variant,img_x,5000,80,lonely
t3,Zero impressions one,img_z,0,0,zero-1
t3,Zero impressions two,img_z,0,0,zero-2
t4,Cat headline one,img_c1,8000,100,cat-1
t4,Cat headline two,img_c2,8000,140,cat-2
t4,Cat headline three,img_c3,8000,90,cat-3
"""


def _rows(csv_text: str) -> list[dict[str, str]]:
    import csv

    return list(csv.DictReader(io.StringIO(csv_text)))


# ── grouping + field mapping ─────────────────────────────────────────────────


def test_groups_rows_by_test_id_into_upworthy_tests():
    tests, summary = parse_upworthy_rows(_rows(EMBEDDED_CSV))
    by_id = {t.test_id: t for t in tests}

    # t1 and t4 survive; t2 (1 variant) and t3 (zero-impression rows) drop.
    assert set(by_id) == {"t1", "t4"}
    assert summary.rows_read == 8
    assert summary.tests_built == 2

    t1 = by_id["t1"]
    assert isinstance(t1, UpworthyTest)
    assert [v.headline for v in t1.variants] == [
        "Headline A about a dog",
        "Headline B about a dog",
    ]
    assert [v.clicks for v in t1.variants] == [150, 210]
    assert [v.impressions for v in t1.variants] == [10000, 10000]
    assert {v.eyecatcher_id for v in t1.variants} == {"img_a"}


def test_ctr_is_not_precomputed_only_raw_counts_carried():
    # The loader must NOT compute CTR — the adapter's _ground_truth derives it.
    # We assert the carried counts, and that ctr (a schema property) matches them.
    tests, _ = parse_upworthy_rows(_rows(EMBEDDED_CSV))
    t1 = next(t for t in tests if t.test_id == "t1")
    v = t1.variants[1]
    assert v.clicks == 210 and v.impressions == 10000
    assert v.ctr == pytest.approx(210 / 10000)


def test_blank_eyecatcher_becomes_none_sentinel():
    csv_text = (
        "clickability_test_id,headline,eyecatcher_id,impressions,clicks\n"
        "tn,No image one,,9000,100\n"
        "tn,No image two,,9000,120\n"
    )
    tests, _ = parse_upworthy_rows(_rows(csv_text))
    assert len(tests) == 1
    assert all(v.eyecatcher_id is None for v in tests[0].variants)


# ── honest drops ─────────────────────────────────────────────────────────────


def test_too_few_variants_group_is_dropped_and_counted():
    _, summary = parse_upworthy_rows(_rows(EMBEDDED_CSV))
    # t2 (1 variant) and t3 (both rows fail schema → 0 surviving variants) both
    # land here: a collapsed group still surfaces a group-level drop, not silence.
    assert summary.groups_dropped_too_few_variants == 2
    assert any("t2" in r for r in summary.drop_reasons)


def test_zero_impression_rows_rejected_and_group_collapses():
    _, summary = parse_upworthy_rows(_rows(EMBEDDED_CSV))
    # Both t3 rows fail the schema's impressions > 0 guard...
    assert summary.rows_dropped_invalid_variant == 2
    # ...leaving t3 with 0 variants → dropped as too-few.
    assert any("t3" in r for r in summary.drop_reasons)


def test_min_impressions_floor_drops_low_traffic_groups():
    csv_text = (
        "clickability_test_id,headline,eyecatcher_id,impressions,clicks\n"
        "low,Tiny one,img,5,1\n"
        "low,Tiny two,img,5,2\n"
    )
    tests, summary = parse_upworthy_rows(_rows(csv_text), min_impressions=100)
    assert tests == []
    assert summary.groups_dropped_low_impressions == 1


def test_unparseable_and_missing_field_rows_are_counted_not_crashing():
    csv_text = (
        "clickability_test_id,headline,eyecatcher_id,impressions,clicks\n"
        "tm,Good one,img,9000,100\n"
        "tm,Bad clicks,img,9000,not-a-number\n"
        ",Missing test id,img,9000,100\n"
        "tm,Good two,img,9000,120\n"
    )
    tests, summary = parse_upworthy_rows(_rows(csv_text))
    assert summary.rows_dropped_unparseable == 1
    assert summary.rows_dropped_missing_field == 1
    # the two good rows still form a retained test
    assert len(tests) == 1
    assert summary.tests_built == 1
    assert summary.variants_kept == 2


def test_nan_and_inf_cells_are_unparseable_not_crashing():
    # pandas/R exports encode missing numerics as NaN/inf; float() parses them
    # but int() would crash. They must be counted as unparseable, not explode.
    csv_text = (
        "clickability_test_id,headline,eyecatcher_id,impressions,clicks\n"
        "tg,Good one,img,9000,100\n"
        "tg,NaN clicks,img,9000,NaN\n"
        "tg,Inf impressions,img,inf,100\n"
        "tg,Good two,img,9000,120\n"
    )
    tests, summary = parse_upworthy_rows(_rows(csv_text))
    assert summary.rows_dropped_unparseable == 2
    assert len(tests) == 1
    assert summary.variants_kept == 2


def test_float_like_integer_cells_are_tolerated():
    csv_text = (
        "clickability_test_id,headline,eyecatcher_id,impressions,clicks\n"
        "tf,One,img,10000.0,150.0\n"
        "tf,Two,img,10000.0,200.0\n"
    )
    tests, _ = parse_upworthy_rows(_rows(csv_text))
    assert tests[0].variants[0].impressions == 10000
    assert tests[0].variants[0].clicks == 150


# ── column_map override ──────────────────────────────────────────────────────


def test_column_map_override_absorbs_renamed_columns():
    # Archive re-published with different names; a partial override fixes only the
    # changed ones (test_id + headline here), defaults cover the rest.
    csv_text = (
        "test_uuid,title,eyecatcher_id,impressions,clicks\n"
        "r1,Renamed A,img,10000,150\n"
        "r1,Renamed B,img,10000,210\n"
    )
    tests, summary = parse_upworthy_rows(
        _rows(csv_text),
        column_map={"test_id": "test_uuid", "headline": "title"},
    )
    assert len(tests) == 1
    assert tests[0].test_id == "r1"
    assert [v.headline for v in tests[0].variants] == ["Renamed A", "Renamed B"]
    assert summary.tests_built == 1


# ── missing column is a loud structural error, not a silent no-image ─────────


def test_missing_eyecatcher_column_raises_not_silent_no_image():
    # Absent eyecatcher column must NOT be read as "every card has no image"
    # (the UpworthyVariant.eyecatcher_id contract). It is a structural error.
    csv_text = (
        "clickability_test_id,headline,impressions,clicks\n"
        "tx,One,10000,150\n"
        "tx,Two,10000,210\n"
    )
    with pytest.raises(ValueError, match="missing required column"):
        parse_upworthy_rows(_rows(csv_text))


def test_blank_eyecatcher_cell_in_present_column_is_still_allowed():
    # The None sentinel is only legitimate when the column EXISTS but the cell is
    # blank — distinct from the column being absent.
    csv_text = (
        "clickability_test_id,headline,eyecatcher_id,impressions,clicks\n"
        "ty,One,,10000,150\n"
        "ty,Two,,10000,210\n"
    )
    tests, _ = parse_upworthy_rows(_rows(csv_text))
    assert len(tests) == 1
    assert all(v.eyecatcher_id is None for v in tests[0].variants)


def test_empty_input_yields_no_tests():
    tests, summary = parse_upworthy_rows([])
    assert tests == []
    assert summary.rows_read == 0


# ── file-I/O wrapper ─────────────────────────────────────────────────────────


def test_load_from_local_csv_file(tmp_path):
    path = tmp_path / "archive.csv"
    path.write_text(EMBEDDED_CSV, encoding="utf-8")
    tests, summary = load_upworthy_archive(path)
    assert {t.test_id for t in tests} == {"t1", "t4"}
    assert summary.rows_read == 8


# ── integration smoke: loader output flows into the adapter ──────────────────


def test_loaded_tests_flow_into_the_adapter():
    tests, _ = parse_upworthy_rows(_rows(EMBEDDED_CSV))
    by_id = {t.test_id: t for t in tests}

    # t1: pure headline swap (same eyecatcher) → a real case.
    case = build_upworthy_case(by_id["t1"], 0, 1)
    assert case.source == "upworthy"
    assert case.ground_truth.winner == "treatment"  # 210 > 150 clicks at equal impressions

    # t4: differing eyecatchers → enumerator records skips, produces no faked
    # copy case, but flows without raising (the no-silent-degradation contract).
    result = upworthy_test_to_cases(by_id["t4"])
    assert result.cases == []
    assert len(result.skipped) == 2


# ── the fetch helper is gated ────────────────────────────────────────────────


def test_fetch_refuses_under_pytest(tmp_path):
    # PYTEST_CURRENT_TEST is set by pytest for every test → must refuse, and must
    # NOT touch the network or write a file.
    dest = tmp_path / "should-not-exist.csv"
    with pytest.raises(RuntimeError, match="must.*not run under pytest"):
        fetch_upworthy_archive(dest)
    assert not dest.exists()


def test_fetch_refuses_under_ci_env(tmp_path, monkeypatch):
    # Even outside pytest's own markers, a CI job (CI=true) must not fetch. We
    # simulate the non-pytest path by clearing the pytest marker but setting CI.
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("CI", "true")
    dest = tmp_path / "nope.csv"
    with pytest.raises(RuntimeError, match="must.*not run under pytest / CI"):
        fetch_upworthy_archive(dest)
    assert not dest.exists()


def test_fetch_url_is_documented_https_osf():
    assert FETCH_URL.startswith("https://osf.io/")
    assert FETCH_URL.endswith("/download")
    assert DEFAULT_COLUMN_MAP["test_id"] == "clickability_test_id"
