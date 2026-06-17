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
    """A first run WRITES a checkpoint (incl. the content digest); a second run with
    the same config RESUMES from it. Running the CLI to seed the checkpoint avoids
    hand-computing the cases_digest and exercises the real round-trip."""
    ckpt = tmp_path / "sub" / "ckpt.json"
    ckpt.parent.mkdir()

    captured: dict = {}
    _patch_engine(monkeypatch, captured)

    # First run: populates + persists the checkpoint (the fake engine fills cache).
    first = CliRunner().invoke(cli, ["benchmark-portfolio", "--checkpoint-path", str(ckpt)])
    assert first.exit_code == 0, first.output
    persisted = json.loads(ckpt.read_text())
    assert "cases_digest" in persisted["run_config"]
    assert len(persisted["predictions"]) == 8

    # Second run: same config → resumes all 8 cached predictions.
    second = CliRunner().invoke(cli, ["benchmark-portfolio", "--checkpoint-path", str(ckpt)])
    assert second.exit_code == 0, second.output
    assert "resumed 8 cached prediction" in second.output


def test_benchmark_portfolio_checkpoint_invalidated_by_edited_cases(tmp_path: Path, monkeypatch):
    """Editing the cases file (same portfolio_id) changes the content digest, so a
    stale checkpoint is REFUSED rather than silently reusing predictions made from
    different control/treatment narratives (codex)."""
    ckpt = tmp_path / "ckpt.json"
    captured: dict = {}
    _patch_engine(monkeypatch, captured)
    # Seed the checkpoint from the committed cases.
    first = CliRunner().invoke(cli, ["benchmark-portfolio", "--checkpoint-path", str(ckpt)])
    assert first.exit_code == 0, first.output

    # Now write an EDITED cases file with the SAME portfolio_id but changed copy.
    from sidira_simulator.services.portfolio_archive import load_portfolio_cases

    arc = load_portfolio_cases()[0]
    edited = tmp_path / "edited_cases.json"
    edited.write_text(
        json.dumps(
            {
                "portfolio_id": arc.portfolio_id,  # SAME id — only content differs
                "scored_cases": [
                    {
                        "id": c.id,
                        "domain": c.domain,
                        "control": c.control + " (EDITED)",
                        "treatment": c.treatment,
                        "metric": c.metric,
                        "real_winner": c.real_winner,
                        "effect": c.effect,
                        "raw_data": c.raw_data,
                    }
                    for c in arc.scored_cases
                ],
                "held_out_memorization_probe": [],
                "human_baseline_anchors": arc.human_baseline_anchors,
            }
        )
    )
    result = CliRunner().invoke(
        cli,
        ["benchmark-portfolio", "--cases-path", str(edited), "--checkpoint-path", str(ckpt)],
    )
    assert result.exit_code != 0
    assert "DIFFERENT run config" in result.output


def test_benchmark_portfolio_all_dropped_reports_void_not_crash(monkeypatch):
    """If the engine drops EVERY case, direction_accuracy is None (n_cases=0) — the
    CLI must report a VOID run, not crash on None * 0 (codex P2)."""

    def fake_score_with_engine(cases, *, persona_pack, **kwargs):
        cs = list(cases)
        case_results = [
            BenchmarkCaseResult(
                case_id=c.case_id,
                source=c.source,
                observed_lift=c.ground_truth.observed_lift,
                dropped=True,
            )
            for c in cs
        ]
        return BenchmarkRunResult(
            n_cases=0,
            n_dropped=len(cs),
            dropped_case_ids=[c.case_id for c in cs],
            void=True,
            void_reason="No case produced a prediction (every case dropped).",
            case_results=case_results,
            seed=0,
        )

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine",
        fake_score_with_engine,
    )

    result = CliRunner().invoke(cli, ["benchmark-portfolio"])
    assert result.exit_code == 0, result.output
    assert "VOID:                   True" in result.output
    # The sim line renders "—/0" rather than crashing on None * 0.
    assert "—/0 correct" in result.output


def test_benchmark_portfolio_missing_cases_path_fails_loud(monkeypatch, tmp_path: Path):
    """A non-existent --cases-path fails with an actionable message, not a bare
    FileNotFoundError (codex P2: the default ships only in the source tree)."""

    def must_not_run(*a, **k):  # pragma: no cover - must not be reached
        raise AssertionError("score_with_engine must not run when the cases file is missing")

    monkeypatch.setattr(
        "sidira_simulator.services.benchmark_runner.score_with_engine", must_not_run
    )
    # The CLI imports DEFAULT_CASES_PATH from portfolio_archive at call time, so
    # patch it at the source module to simulate a packaged install where the
    # source-tree cases file is absent.
    monkeypatch.setattr(
        "sidira_simulator.services.portfolio_archive.DEFAULT_CASES_PATH",
        tmp_path / "nope" / "PORTFOLIO_CASES.json",
    )
    result = CliRunner().invoke(cli, ["benchmark-portfolio"])
    assert result.exit_code != 0
    assert "portfolio cases file not found" in result.output
    assert "--cases-path" in result.output


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
