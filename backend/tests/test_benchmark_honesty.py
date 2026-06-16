"""Tests for the stratified honesty table (#222, ablation-protocol §4 reporting).

The honesty table breaks a blind-eval down per stratum and presents it honestly.
The load-bearing assertions:

- per-stratum direction-accuracy / rank-ρ / baselines are correct on a hand-built
  fixture, computed by the SAME helpers the runner uses;
- report-every-cell (§4 line 71): a deliberately-bad (negative-ρ) stratum still
  appears as a row, never dropped;
- a stratum where EVERY case was dropped still appears (n_cases=0, n_dropped>0) —
  source-specific total failures are not hidden behind only the global drop list;
- the underpowered flag fires below the certification floor, and the cell is
  STILL reported (not hidden);
- a VOID run propagates to a void table (whole table untrustworthy);
- per-stratum baselines (always-flat + random-rank) are correct for that stratum;
- the build is deterministic and consumes the run's EXACT per-case predictions
  (no second predictor pass);
- runner-level drop counters are carried through onto the table.

Fixtures are small, in-memory, and LLM-free: cases are built from the benchmark
schema (one real adapter-produced template, copied), predictions are supplied per
case, and the run result is produced through the REAL `run_blind_eval` so
`case_results` is populated end-to-end.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.benchmark import (
    BenchmarkCase,
    GroundTruth,
    UpworthyTest,
    UpworthyVariant,
)
from sidira_simulator.schemas.scoring import (
    BenchmarkCaseResult,
    BenchmarkRunResult,
    StratifiedHonestyTable,
)
from sidira_simulator.services.benchmark_adapter import upworthy_test_to_cases
from sidira_simulator.services.benchmark_honesty import (
    by_effect_magnitude,
    by_source,
    render,
    stratify,
)
from sidira_simulator.services.null_integrity import _MIN_EXPERIMENTS


def _template_case() -> BenchmarkCase:
    """One structurally-valid case from the REAL adapter, used as a template.

    The table reads only `source` + `observed_lift` + the supplied prediction, so
    each fixture case is this template with `source` + `ground_truth` overridden —
    a real `(Capability, Hypothesis)` pair without hand-constructing the schema.
    """
    test = UpworthyTest(
        test_id="fixture",
        variants=[
            UpworthyVariant(headline="base", clicks=100, impressions=10_000, eyecatcher_id=None),
            UpworthyVariant(headline="chal", clicks=150, impressions=10_000, eyecatcher_id=None),
        ],
    )
    return upworthy_test_to_cases(test).cases[0]


_TEMPLATE = _template_case()


def _case(case_id: str, source: str, observed_lift: float) -> BenchmarkCase:
    """A scorable case carrying a source label + a signed observed lift."""
    if observed_lift > 0:
        winner = "treatment"
    elif observed_lift < 0:
        winner = "control"
    else:
        winner = "tie"
    control = 0.10
    treatment = control + observed_lift
    if treatment < 0:
        treatment = 0.10
        control = treatment - observed_lift
    gt = GroundTruth(
        metric_name="ctr",
        control_metric=control,
        treatment_metric=treatment,
        observed_lift=observed_lift,
        winner=winner,
    )
    return _TEMPLATE.model_copy(update={"case_id": case_id, "source": source, "ground_truth": gt})


# A sentinel marking "the predictor drops this case" in a fixture spec.
DROP = object()


def _run(
    specs: list[tuple[BenchmarkCase, object]],
    *,
    void: bool = False,
    void_reason: str | None = None,
) -> BenchmarkRunResult:
    """Build a `BenchmarkRunResult` from (case, prediction-or-DROP) specs.

    Drives the REAL `run_blind_eval` with a lookup-table predictor so
    `case_results` (scored + dropped, in input order) is populated end-to-end —
    the exact wiring the honesty table consumes. `void` can be forced on after the
    fact to test void propagation without contriving a leaking predictor.
    """
    cases = [c for c, _ in specs]
    lookup = {c.case_id: pred for c, pred in specs}

    def predictor(case: BenchmarkCase) -> float:
        pred = lookup[case.case_id]
        if pred is DROP:
            raise RuntimeError("fixture drop")
        return float(pred)  # type: ignore[arg-type]

    from sidira_simulator.services.benchmark_runner import run_blind_eval

    result = run_blind_eval(cases, predictor, seed=7, n_permutations=50, n_resamples=50)
    if void:
        return result.model_copy(update={"void": True, "void_reason": void_reason})
    return result


# ── Per-stratum metrics + baselines ──────────────────────────────────────────


def test_by_source_partitions_and_scores_each_stratum():
    # Two sources; in source A predictions perfectly track actuals (ρ=1, dir=1),
    # in source B they are anti-correlated (ρ=-1) — a deliberately-bad stratum.
    a = [_case(f"a{i}", "upworthy", lift) for i, lift in enumerate([0.01, 0.02, 0.03])]
    b = [_case(f"b{i}", "hillstrom", lift) for i, lift in enumerate([0.01, 0.02, 0.03])]
    specs = [(c, c.ground_truth.observed_lift) for c in a]
    specs += [(c, -c.ground_truth.observed_lift) for c in b]

    table = stratify(_run(specs), by_source, stratifier_name="source")
    by_key = {s.key: s for s in table.strata}
    assert set(by_key) == {"upworthy", "hillstrom"}

    good = by_key["upworthy"]
    assert good.n_cases == 3
    assert good.direction_accuracy == pytest.approx(1.0)
    assert good.rank_rho == pytest.approx(1.0)

    bad = by_key["hillstrom"]
    assert bad.n_cases == 3
    assert bad.direction_accuracy == pytest.approx(0.0)
    assert bad.rank_rho == pytest.approx(-1.0)


def test_report_every_cell_bad_stratum_is_not_dropped():
    """§4 line 71: a deliberately-bad stratum still appears — no silent truncation."""
    good = [_case(f"g{i}", "good", lift) for i, lift in enumerate([0.01, 0.02, 0.03])]
    bad = [_case(f"b{i}", "bad", lift) for i, lift in enumerate([0.01, 0.02, 0.03])]
    specs = [(c, c.ground_truth.observed_lift) for c in good]
    specs += [(c, -c.ground_truth.observed_lift) for c in bad]

    table = stratify(_run(specs), by_source, stratifier_name="source")
    keys = {s.key for s in table.strata}
    assert "bad" in keys, "the poor-rho stratum must be reported, not dropped"
    assert "good" in keys


def test_dropped_only_stratum_is_still_reported():
    """A source where EVERY prediction failed must STILL appear as a row (§4) —
    not be visible only through the global drop list."""
    scored = [_case(f"s{i}", "ok", 0.01 * (i + 1)) for i in range(3)]
    failed = [_case(f"f{i}", "all_failed", 0.01 * (i + 1)) for i in range(2)]
    specs = [(c, c.ground_truth.observed_lift) for c in scored]
    specs += [(c, DROP) for c in failed]

    table = stratify(_run(specs), by_source, stratifier_name="source")
    by_key = {s.key: s for s in table.strata}
    assert "all_failed" in by_key, "dropped-only stratum must be reported"
    af = by_key["all_failed"]
    assert af.n_cases == 0
    assert af.n_dropped == 2
    assert af.underpowered is True
    assert af.caveat is not None and "dropped" in af.caveat


def test_unscorable_case_result_is_treated_as_dropped_not_a_crash():
    """The schema permits observed_lift=None with dropped=False (a prediction but
    no scorable label). Such a member must NOT enter the scored denominator (it
    would length-mismatch spearman_rho) — it is counted as dropped instead."""
    good = [
        BenchmarkCaseResult(case_id=f"g{i}", source="s", observed_lift=0.01 * (i + 1), prediction=p)
        for i, p in enumerate([0.01, 0.02, 0.03])
    ]
    # prediction present, but observed_lift None and NOT flagged dropped.
    unscorable = BenchmarkCaseResult(
        case_id="u0", source="s", observed_lift=None, prediction=0.5, dropped=False
    )
    run = BenchmarkRunResult(
        rank_rho=1.0,
        direction_accuracy=1.0,
        n_cases=3,
        n_dropped=0,
        case_results=[*good, unscorable],
        seed=7,
    )
    table = stratify(run, by_source, stratifier_name="source")
    s = table.strata[0]
    assert s.n_cases == 3  # the unscorable one excluded from the scored denominator
    assert s.n_dropped == 1
    assert s.rank_rho is not None  # no crash


def test_per_stratum_baselines_are_correct():
    # A sign-mixed stratum: actuals [-0.02,-0.01,0,0.01,0.02] → 2 neg, 1 flat, 2 pos.
    lifts = [-0.02, -0.01, 0.0, 0.01, 0.02]
    cases = [_case(f"c{i}", "s", lift) for i, lift in enumerate(lifts)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    table = stratify(_run(specs), by_source, stratifier_name="source")
    s = table.strata[0]
    by_name = {bl.name: bl for bl in s.baselines}
    assert by_name["always_flat"].direction_accuracy == pytest.approx(1 / 5)
    assert by_name["always_flat"].rank_rho == 0.0
    expected_rand = (2 / 5) ** 2 + (1 / 5) ** 2 + (2 / 5) ** 2
    assert by_name["random_rank"].direction_accuracy == pytest.approx(expected_rand)
    assert by_name["random_rank"].rank_rho == 0.0


# ── Underpowered flag ────────────────────────────────────────────────────────


def test_underpowered_flag_fires_below_min_n_but_cell_is_reported():
    small = [_case(f"s{i}", "tiny", lift) for i, lift in enumerate([0.01, 0.02])]
    big = [_case(f"B{i}", "big", 0.01 * (i + 1)) for i in range(_MIN_EXPERIMENTS)]
    specs = [(c, c.ground_truth.observed_lift) for c in small + big]
    table = stratify(_run(specs), by_source, stratifier_name="source")
    by_key = {s.key: s for s in table.strata}

    assert by_key["tiny"].underpowered is True
    assert by_key["tiny"].caveat is not None and "underpowered" in by_key["tiny"].caveat
    assert by_key["tiny"].n_cases == 2
    assert by_key["tiny"].direction_accuracy is not None
    assert "underpowered" in by_key["tiny"].regime

    assert by_key["big"].underpowered is False
    assert "underpowered" not in by_key["big"].regime


# ── Void propagation ─────────────────────────────────────────────────────────


def test_void_run_propagates_to_void_table():
    cases = [_case(f"c{i}", "s", 0.01 * (i + 1)) for i in range(_MIN_EXPERIMENTS)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    run = _run(specs, void=True, void_reason="leakage: null did not center")
    table = stratify(run, by_source, stratifier_name="source")
    assert table.void is True
    assert "leakage" in table.void_reason
    assert "VOID" in table.caveat
    assert table.strata  # strata still computed; void is a table-level trust flag


# ── Drop counters carried through ────────────────────────────────────────────


def test_runner_drop_counters_are_carried_through():
    scored = [_case(f"c{i}", "s", 0.01 * (i + 1)) for i in range(3)]
    dropped = [_case("dropped-x", "s", 0.01), _case("dropped-y", "s", 0.02)]
    specs = [(c, c.ground_truth.observed_lift) for c in scored]
    specs += [(c, DROP) for c in dropped]
    run = _run(specs)
    table = stratify(run, by_source, stratifier_name="source")
    assert table.n_dropped_at_runner == 2
    assert set(table.dropped_case_ids) == {"dropped-x", "dropped-y"}
    assert table.total_n_scored == 3
    assert "dropped at the runner level: 2" in table.caveat


# ── Consumes the run's exact predictions (no second pass) ─────────────────────


def test_table_consumes_run_case_results_not_a_replay():
    cases = [_case(f"c{i}", "s", 0.01 * (i + 1)) for i in range(3)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    run = _run(specs)
    # The run carries per-case results; the table is built from THOSE.
    assert run.case_results and all(isinstance(r, BenchmarkCaseResult) for r in run.case_results)
    table = stratify(run, by_source, stratifier_name="source")
    assert sum(s.n_cases for s in table.strata) == run.n_cases


# ── Effect-magnitude stratifier ──────────────────────────────────────────────


def test_by_effect_magnitude_buckets_on_absolute_lift():
    lifts = [0.001, 0.01, 0.05, -0.05]
    cases = [_case(f"c{i}", "s", lift) for i, lift in enumerate(lifts)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    table = stratify(_run(specs), by_effect_magnitude(), stratifier_name="effect_magnitude")
    by_key = {s.key: s.n_cases for s in table.strata}
    assert len(table.strata) == 3
    top = [n for k, n in by_key.items() if ">=" in k][0]
    assert top == 2  # the two |0.05| cases share the top bucket


def test_by_effect_magnitude_custom_edges_above_zero_use_underflow_bucket():
    # Custom edges whose first boundary is ABOVE zero: a sub-boundary magnitude
    # must land in an explicit "< first-edge" bucket, NOT the first half-open one.
    lifts = [0.001, 0.01, 0.05]
    cases = [_case(f"c{i}", "s", lift) for i, lift in enumerate(lifts)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    table = stratify(
        _run(specs), by_effect_magnitude([0.005, 0.02]), stratifier_name="effect_magnitude"
    )
    keys = {s.key for s in table.strata}
    assert any(k.startswith("|effect| <") for k in keys)
    assert len(table.strata) == 3
    assert sum(s.n_cases for s in table.strata) == 3


def test_by_effect_magnitude_rejects_bad_edges():
    with pytest.raises(ValueError, match="at least two"):
        by_effect_magnitude([0.0])
    with pytest.raises(ValueError, match="ascending"):
        by_effect_magnitude([0.0, 0.02, 0.01])


# ── Determinism ──────────────────────────────────────────────────────────────


def test_stratify_is_deterministic():
    cases = [_case(f"c{i}", "upworthy" if i % 2 else "hillstrom", 0.01 * (i + 1)) for i in range(6)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    run = _run(specs)
    t1 = stratify(run, by_source, stratifier_name="source")
    t2 = stratify(run, by_source, stratifier_name="source")
    assert t1.model_dump() == t2.model_dump()
    # First-seen key order is preserved (hillstrom seen first at i=0).
    assert [s.key for s in t1.strata] == ["hillstrom", "upworthy"]


# ── Empty input + rendering ──────────────────────────────────────────────────


def test_stratify_empty_raises():
    empty = BenchmarkRunResult(n_cases=0, void=True, seed=7)
    with pytest.raises(ValueError, match="case_results"):
        stratify(empty, by_source, stratifier_name="source")


def test_render_is_pure_and_lists_every_stratum():
    good = [_case(f"g{i}", "good", lift) for i, lift in enumerate([0.01, 0.02, 0.03])]
    bad = [_case(f"b{i}", "bad", lift) for i, lift in enumerate([0.01, 0.02, 0.03])]
    specs = [(c, c.ground_truth.observed_lift) for c in good]
    specs += [(c, -c.ground_truth.observed_lift) for c in bad]
    table = stratify(_run(specs), by_source, stratifier_name="source")
    text = render(table)
    assert isinstance(text, str)
    assert "good" in text and "bad" in text
    assert "by source" in text
    assert "caveat:" in text


def test_render_marks_void_table():
    cases = [_case(f"c{i}", "s", 0.01 * (i + 1)) for i in range(_MIN_EXPERIMENTS)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    run = _run(specs, void=True, void_reason="leakage")
    text = render(stratify(run, by_source, stratifier_name="source"))
    assert "VOID" in text


def test_table_is_a_typed_schema():
    cases = [_case(f"c{i}", "s", 0.01 * (i + 1)) for i in range(3)]
    specs = [(c, c.ground_truth.observed_lift) for c in cases]
    table = stratify(_run(specs), by_source, stratifier_name="source")
    assert isinstance(table, StratifiedHonestyTable)
    assert StratifiedHonestyTable.model_validate(table.model_dump()) == table
