"""Smoke test for the `benchmark-upworthy` CLI (#222).

The CLI itself drives the LIVE engine (it is GATED under pytest), so this smoke
test does NOT run the real engine: it monkeypatches `score_with_engine` with a
fake that records its inputs, then asserts the command WIRES the pieces together
— load CSV → adapt to cases → load the panel → call the scorer with those cases +
the panel — and emits the pre-registration + result sections. The eval math is
covered by `test_benchmark_engine.py`.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from sidira_simulator.cli import cli
from sidira_simulator.schemas.benchmark import BenchmarkCase
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.schemas.scoring import (
    BenchmarkCaseResult,
    BenchmarkRunResult,
    NullIntegrityCertificate,
)

# Two tests, each a baseline + one challenger headline (pure copy swaps so the
# adapter yields a case per challenger and skips nothing).
_CSV = """clickability_test_id,headline,clicks,impressions,eyecatcher_id
t1,Baseline one,100,10000,
t1,Challenger one,150,10000,
t2,Baseline two,80,10000,
t2,Challenger two,200,10000,
"""


def _fake_result(cases: list[BenchmarkCase]) -> BenchmarkRunResult:
    case_results = [
        BenchmarkCaseResult(
            case_id=c.case_id,
            source=c.source,
            observed_lift=c.ground_truth.observed_lift,
            prediction=0.01,
        )
        for c in cases
    ]
    cert = NullIntegrityCertificate(
        n_experiments=len(cases),
        passed=True,
        certifying=True,
        n_permutations=10,
        seed=0,
        integrity_hash="deadbeef",
    )
    return BenchmarkRunResult(
        rank_rho=0.5,
        direction_accuracy=1.0,
        certificate=cert,
        n_cases=len(cases),
        case_results=case_results,
        seed=0,
    )


def test_benchmark_upworthy_wires_load_adapt_call(tmp_path: Path, monkeypatch):
    csv_path = tmp_path / "archive.csv"
    csv_path.write_text(_CSV, encoding="utf-8")

    captured: dict = {}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        captured["cases"] = list(cases)
        captured["persona_pack"] = persona_pack
        captured["kwargs"] = kwargs
        return _fake_result(list(cases))

    # The CLI imports score_with_engine from the runner module at call time, so
    # patching the source attribute is what the local import resolves.
    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        [
            "benchmark-upworthy",
            "--csv-path",
            str(csv_path),
            "--population-size",
            "4",
            "--max-agents",
            "2",
            "--seed",
            "9",
            "--n-permutations",
            "10",
        ],
    )

    assert result.exit_code == 0, result.output
    # load → adapt: one case per challenger (2 tests × 1 challenger = 2 cases).
    assert len(captured["cases"]) == 2
    assert all(isinstance(c, BenchmarkCase) for c in captured["cases"])
    assert all(c.source == "upworthy" for c in captured["cases"])
    # load panel: the real pre-registered panel was passed through.
    assert isinstance(captured["persona_pack"], PersonaPack)
    # run params threaded through.
    assert captured["kwargs"]["population_size"] == 4
    assert captured["kwargs"]["max_agents"] == 2
    assert captured["kwargs"]["seed"] == 9
    assert captured["kwargs"]["n_permutations"] == 10
    # emitted sections.
    assert "Pre-registration / run config" in result.output
    assert "Blind-eval result" in result.output
    assert "Null-integrity certificate" in result.output
    assert "Stratified honesty table" in result.output


def test_benchmark_upworthy_errors_when_no_cases(tmp_path: Path, monkeypatch):
    # A CSV with only single-variant tests yields no adaptable cases.
    csv_path = tmp_path / "thin.csv"
    csv_path.write_text(
        "clickability_test_id,headline,clicks,impressions,eyecatcher_id\n"
        "solo,Only one,10,1000,\n",
        encoding="utf-8",
    )

    def fail(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("score_with_engine should not be called with zero cases")

    monkeypatch.setattr("sidira_simulator.services.benchmark_runner.score_with_engine", fail)

    result = CliRunner().invoke(cli, ["benchmark-upworthy", "--csv-path", str(csv_path)])
    assert result.exit_code != 0
    assert "No benchmark cases" in result.output
