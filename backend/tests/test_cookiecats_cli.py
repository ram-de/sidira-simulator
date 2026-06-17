"""Smoke test for the `benchmark-cookiecats` CLI.

The CLI drives the LIVE engine (GATED under pytest), so this test does NOT run the
real engine: it monkeypatches `score_with_engine` with a fake that records its
inputs, then asserts the command WIRES the pieces together — load CSV → adapt to
cases → load the real panel → call the scorer with those cases + panel + the
retention metric builder — emits the pre-registration + result + honesty sections,
that --by-segment conditions each octile on a sub-panel, and that the resumable
checkpoint round-trips. The eval math + stratifiers are covered by their own tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from sidira_simulator.adapters.cookiecats_panel_loader import load_cookiecats_panel
from sidira_simulator.cli import cli
from sidira_simulator.schemas.benchmark import BenchmarkCase
from sidira_simulator.schemas.persona import PersonaPack
from sidira_simulator.schemas.scoring import (
    BenchmarkCaseResult,
    BenchmarkRunResult,
    NullIntegrityCertificate,
)

_FIXTURE = Path(__file__).parent / "data" / "cookiecats_sample.csv"


def _fake_result(cases: list[BenchmarkCase]) -> BenchmarkRunResult:
    case_results = [
        BenchmarkCaseResult(
            case_id=c.case_id,
            source=c.source,
            observed_lift=c.ground_truth.observed_lift,
            prediction=-0.01,
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
        rank_rho=0.3,
        direction_accuracy=0.6,
        certificate=cert,
        n_cases=len(cases),
        case_results=case_results,
        seed=0,
    )


def test_benchmark_cookiecats_wires_load_adapt_call(monkeypatch):
    captured: dict = {}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        captured["cases"] = list(cases)
        captured["persona_pack"] = persona_pack
        captured["kwargs"] = kwargs
        return _fake_result(list(cases))

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        [
            "benchmark-cookiecats",
            "--csv-path",
            str(_FIXTURE),
            "--metric",
            "retention_7",
            "--population-size",
            "4",
            "--max-agents",
            "2",
            "--seed",
            "7",
        ],
    )
    assert result.exit_code == 0, result.output
    # load → adapt: one population-level A/B case.
    cases = captured["cases"]
    assert len(cases) == 1
    assert cases[0].case_id == "cookiecats:gate40_vs_gate30:retention_7"
    assert isinstance(captured["persona_pack"], PersonaPack)
    # The engine metric is `retention` (the data outcome retention_7 maps to it).
    assert captured["kwargs"]["metric_name"] == "retention"
    assert captured["kwargs"]["population_size"] == 4
    assert captured["kwargs"]["max_agents"] == 2
    assert captured["kwargs"]["seed"] == 7
    assert callable(captured["kwargs"]["hypothesis_builder"])
    assert "Pre-registration / run config" in result.output
    assert "Blind-eval result" in result.output
    assert "Null-integrity certificate" in result.output


def test_benchmark_cookiecats_by_segment_conditions_subpanels(monkeypatch):
    captured: dict = {"calls": []}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        cs = list(cases)
        captured["calls"].append({"cases": cs, "panel": persona_pack})
        captured["cases"] = cs
        cache = kwargs.get("prediction_cache")
        if cache is not None:
            for c in cs:
                cache.setdefault(c.case_id, -0.01)
        return _fake_result(cs)

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-cookiecats", "--csv-path", str(_FIXTURE), "--by-segment"],
    )
    assert result.exit_code == 0, result.output
    full_n = len(load_cookiecats_panel().personas)
    warm_panels = [c["panel"] for c in captured["calls"][:-1]]  # all but the final full-set run
    assert warm_panels, "expected per-segment warm-up runs"
    for p in warm_panels:
        assert len(p.personas) < full_n, "segment warm-up must use a conditioned sub-panel"
        assert p.version != load_cookiecats_panel().version  # stratum-suffixed version
    # >=2 distinct cohorts conditioned (low vs heavy engagement).
    cohorts = {tuple(sorted(pp.id for pp in c["panel"].personas)) for c in captured["calls"][:-1]}
    assert len(cohorts) >= 2
    assert all(len(c.case_id.split(":")) == 4 for c in captured["cases"])
    assert "by engagement" in result.output


def test_benchmark_cookiecats_segment_warmup_miss_fails_loud(monkeypatch):
    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        cache = kwargs.get("prediction_cache")
        if cache is not None:
            for c in list(cases)[1:]:  # leave one case OUT (simulate an engine drop)
                cache[c.case_id] = -0.01
        return _fake_result(list(cases))

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-cookiecats", "--csv-path", str(_FIXTURE), "--by-segment"],
    )
    assert result.exit_code != 0
    assert "segment warm-up failed to score" in result.output


def test_benchmark_cookiecats_checkpoint_resumes(tmp_path: Path, monkeypatch):
    ckpt = tmp_path / "sub" / "ckpt.json"
    ckpt.parent.mkdir()
    panel_version = load_cookiecats_panel().version
    ckpt.write_text(
        json.dumps(
            {
                "run_config": {
                    "metric": "retention_7",
                    "seed": 0,
                    "model_id": None,
                    "population_size": 10,
                    "max_agents": None,
                    "use_segments": False,
                    "panel_version": panel_version,
                },
                "predictions": {"cookiecats:gate40_vs_gate30:retention_7": -0.02},
            }
        )
    )

    captured: dict = {}

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        captured["prediction_cache"] = kwargs.get("prediction_cache")
        return _fake_result(list(cases))

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-cookiecats", "--csv-path", str(_FIXTURE), "--checkpoint-path", str(ckpt)],
    )
    assert result.exit_code == 0, result.output
    assert captured["prediction_cache"]["cookiecats:gate40_vs_gate30:retention_7"] == -0.02
    assert "resumed 1 cached prediction" in result.output
    persisted = json.loads(ckpt.read_text())
    assert persisted["predictions"]["cookiecats:gate40_vs_gate30:retention_7"] == -0.02
    assert persisted["run_config"]["seed"] == 0


def test_benchmark_cookiecats_refuses_checkpoint_config_drift(tmp_path: Path, monkeypatch):
    ckpt = tmp_path / "ckpt.json"
    ckpt.write_text(
        json.dumps(
            {
                "run_config": {
                    "metric": "retention_7",
                    "seed": 999,  # different seed than the run below (seed=0 default)
                    "model_id": None,
                    "population_size": 10,
                    "max_agents": None,
                    "use_segments": False,
                },
                "predictions": {"cookiecats:gate40_vs_gate30:retention_7": -0.02},
            }
        )
    )

    def must_not_run(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("score_with_engine must not run on a config-drift checkpoint")

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine", must_not_run
    )

    result = CliRunner().invoke(
        cli,
        ["benchmark-cookiecats", "--csv-path", str(_FIXTURE), "--checkpoint-path", str(ckpt)],
    )
    assert result.exit_code != 0
    assert "DIFFERENT run config" in result.output
