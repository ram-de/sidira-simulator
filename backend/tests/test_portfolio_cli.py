"""Smoke test for the `benchmark-portfolio` CLI.

The CLI drives the LIVE engine (GATED under pytest), so this test does NOT run the
real engine: it monkeypatches `score_with_engine` with a fake that records its
inputs, then asserts the command WIRES the pieces together — load PORTFOLIO_CASES
→ adapt the 8 scored cases → load a generic consumer panel → call the scorer with
those cases + panel + the generic `conversion` metric builder — emits the
pre-registration, the direction_accuracy headline, the null-cert, the human-
baseline anchors, the per-experiment honesty table, and (with --include-heldout)
the SEPARATE non-scored probe section. The eval math + stratifiers are covered by
their own tests.
"""

from __future__ import annotations

import json
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


def _fake_result(cases: list[BenchmarkCase]) -> BenchmarkRunResult:
    case_results = [
        BenchmarkCaseResult(
            case_id=c.case_id,
            source=c.source,
            observed_lift=c.ground_truth.observed_lift,
            # Predict the real sign so direction_accuracy is non-trivial in output.
            prediction=c.ground_truth.observed_lift * 0.5,
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
        rank_rho=0.4,
        direction_accuracy=1.0,
        certificate=cert,
        n_cases=len(cases),
        case_results=case_results,
        seed=0,
    )


def _patch_engine(monkeypatch, captured: dict):
    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        cs = list(cases)
        captured.setdefault("calls", []).append(
            {"cases": cs, "panel": persona_pack, "kwargs": kwargs}
        )
        captured["cases"] = cs
        captured["persona_pack"] = persona_pack
        captured["kwargs"] = kwargs
        cache = kwargs.get("prediction_cache")
        if cache is not None:
            for c in cs:
                cache.setdefault(c.case_id, c.ground_truth.observed_lift * 0.5)
        return _fake_result(cs)

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )


def test_benchmark_portfolio_wires_load_adapt_call(monkeypatch):
    captured: dict = {}
    _patch_engine(monkeypatch, captured)

    result = CliRunner().invoke(
        cli,
        ["benchmark-portfolio", "--population-size", "4", "--max-agents", "2", "--seed", "7"],
    )
    assert result.exit_code == 0, result.output
    cases = captured["cases"]
    # The committed curated set has 8 scored cases.
    assert len(cases) == 8
    assert all(c.case_id.startswith("portfolio:") for c in cases)
    assert isinstance(captured["persona_pack"], PersonaPack)
    # The generic engine metric is `conversion`.
    assert captured["kwargs"]["metric_name"] == "conversion"
    assert captured["kwargs"]["population_size"] == 4
    assert captured["kwargs"]["max_agents"] == 2
    assert captured["kwargs"]["seed"] == 7
    assert callable(captured["kwargs"]["hypothesis_builder"])
    # The headline output sections.
    assert "Pre-registration / run config" in result.output
    assert "direction_accuracy (HEADLINE)" in result.output
    assert "Null-integrity certificate" in result.output
    # Human-baseline anchors printed next to the sim score.
    assert "Human-baseline anchors" in result.output
    assert "kohavi_expert_survey" in result.output
    assert "3 / 21 experts" in result.output
    # Direction-only / magnitude-out-of-scope note.
    assert "DIRECTION-ONLY" in result.output
    # Per-experiment honesty table.
    assert "by portfolio case" in result.output


def test_benchmark_portfolio_omits_heldout_by_default(monkeypatch):
    captured: dict = {}
    _patch_engine(monkeypatch, captured)
    result = CliRunner().invoke(cli, ["benchmark-portfolio"])
    assert result.exit_code == 0, result.output
    assert "HELD-OUT MEMORIZATION PROBE" not in result.output
    # Default off: only the 8 scored cases run (warm-up + final = same case set).
    assert len(captured["cases"]) == 8


def test_benchmark_portfolio_include_heldout_runs_separate_nonscored(monkeypatch):
    captured: dict = {}
    _patch_engine(monkeypatch, captured)
    result = CliRunner().invoke(cli, ["benchmark-portfolio", "--include-heldout"])
    assert result.exit_code == 0, result.output
    assert "HELD-OUT MEMORIZATION PROBE (NON-SCORED" in result.output
    assert "RECITING, not reasoning" in result.output
    # The probe section runs probe cases (held_out_probe ids) SEPARATELY.
    probe_ids = {
        c.case_id
        for call in captured["calls"]
        for c in call["cases"]
        if c.case_id.split(":", 1)[1]
        in {"netflix_browse_before_signup", "highrise_simple_person_page"}
    }
    assert probe_ids == {
        "portfolio:netflix_browse_before_signup",
        "portfolio:highrise_simple_person_page",
    }


def test_benchmark_portfolio_checkpoint_resumes(tmp_path: Path, monkeypatch):
    from sidira_simulator.adapters.upworthy_panel_loader import upworthy_panel_registration
    from sidira_simulator.services.portfolio_archive import load_portfolio_cases

    panel_version = upworthy_panel_registration().version
    portfolio_id = load_portfolio_cases()[0].portfolio_id
    ckpt = tmp_path / "sub" / "ckpt.json"
    ckpt.parent.mkdir()
    ckpt.write_text(
        json.dumps(
            {
                "run_config": {
                    "seed": 0,
                    "model_id": None,
                    "population_size": 10,
                    "max_agents": None,
                    "panel_version": panel_version,
                    "portfolio_id": portfolio_id,
                },
                "predictions": {"portfolio:cookiecats_gate_move": -0.02},
            }
        )
    )

    captured: dict = {}
    _patch_engine(monkeypatch, captured)

    result = CliRunner().invoke(cli, ["benchmark-portfolio", "--checkpoint-path", str(ckpt)])
    assert result.exit_code == 0, result.output
    assert "resumed 1 cached prediction" in result.output
    assert captured["kwargs"]["prediction_cache"]["portfolio:cookiecats_gate_move"] == -0.02
    persisted = json.loads(ckpt.read_text())
    assert persisted["predictions"]["portfolio:cookiecats_gate_move"] == -0.02
    assert persisted["run_config"]["seed"] == 0


def test_benchmark_portfolio_refuses_checkpoint_config_drift(tmp_path: Path, monkeypatch):
    ckpt = tmp_path / "ckpt.json"
    ckpt.write_text(
        json.dumps(
            {
                "run_config": {"seed": 999, "model_id": None, "population_size": 10},
                "predictions": {"portfolio:cookiecats_gate_move": -0.02},
            }
        )
    )

    def must_not_run(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("score_with_engine must not run on a config-drift checkpoint")

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine", must_not_run
    )

    result = CliRunner().invoke(cli, ["benchmark-portfolio", "--checkpoint-path", str(ckpt)])
    assert result.exit_code != 0
    assert "DIFFERENT run config" in result.output
