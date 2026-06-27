"""Tests for the submit-time advisory gate over PRIOR PREDICTIONS (#38).

The gate ranks the tenant's own predicted simulations (NOT measured experiments),
groups re-runs of the same hypothesis with their agreement spread, and never
renders a prediction through the measured-Experiment shape.
"""

from __future__ import annotations

from sidira_simulator.schemas.experiment_memory import ExperimentCategory, Verdict
from sidira_simulator.schemas.simulation_archive import (
    PredictedDirection,
    SimulatedHypothesis,
)
from sidira_simulator.services.experiment_gate import gate_similar
from sidira_simulator.services.live_simulations import short_sim_id


def _sim(
    *,
    sim_id: str,
    change: str,
    metric: str = "conversion",
    direction: PredictedDirection = PredictedDirection.UP,
    confidence: float = 70.0,
    pp: float | None = 1.5,
    date: str = "2026-06-20",
) -> SimulatedHypothesis:
    return SimulatedHypothesis(
        id=sim_id,
        change_description=change,
        primary_metric=metric,
        category=ExperimentCategory.UI,
        predicted_direction=direction,
        confidence_score=confidence,
        predicted_metric_lift_pp=pp,
        sim_date=date,
    )


# ── source-aware: predicted priors, never measured ────────────────────────────


def test_gate_match_is_predicted_not_measured() -> None:
    sims = [_sim(sim_id="sim-timer", change="Add an urgency countdown timer to checkout")]
    resp = gate_similar("add an urgency countdown timer to checkout", sims, top_k=5)
    assert resp.verdict is Verdict.ALREADY_TESTED
    m = resp.matches[0]
    assert m.id == "sim-timer"
    # Predicted-outcome side only — no measured winner / effect_size on the schema.
    assert m.predicted_direction == "up"
    assert m.agreements == [70.0]
    assert not hasattr(m, "winner")
    assert not hasattr(m, "effect_size_pct")
    # Honest headline: a prediction, not a measured result.
    assert "prediction" in resp.headline.lower()


def test_gate_empty_when_no_simulations() -> None:
    resp = gate_similar("anything at all", [], top_k=5)
    assert resp.verdict is Verdict.NOVEL
    assert resp.matches == []


def test_gate_novel_surfaces_no_weak_prior() -> None:
    sims = [_sim(sim_id="sim-a", change="Add an urgency countdown timer to checkout")]
    resp = gate_similar("Switch datacenter region to cut p99 latency", sims, top_k=5)
    assert resp.verdict is Verdict.NOVEL
    assert resp.matches == []
    assert resp.caveat is None


def test_gate_similar_carries_prediction_caveat() -> None:
    sims = [_sim(sim_id="sim-price", change="Try a different monthly price for the paid tier")]
    resp = gate_similar("Experiment with the subscription price of our pro plan", sims, top_k=5)
    assert resp.verdict is Verdict.SIMILAR
    assert resp.caveat is not None
    assert "prediction" in resp.caveat.lower()
    assert "measured" in resp.caveat.lower()


# ── grouping + agreement spread (#38c) ────────────────────────────────────────


def test_gate_groups_reruns_and_shows_spread() -> None:
    change = "Add a 'Continue Watching' rail to the home screen"
    sims = [
        _sim(sim_id="sim-a", change=change, confidence=65.0, date="2026-06-18"),
        _sim(sim_id="sim-b", change=change, confidence=78.0, date="2026-06-20"),
        _sim(sim_id="sim-c", change=change, confidence=82.0, date="2026-06-22"),
    ]
    resp = gate_similar("add a continue watching rail to the home screen", sims, top_k=5)
    assert len(resp.matches) == 1, "three re-runs collapse into one match"
    m = resp.matches[0]
    assert m.run_count == 3
    assert m.agreements == [65.0, 78.0, 82.0], "agreement spread, oldest→newest"
    assert m.id == "sim-c", "representative is the most-recent run"
    assert m.last_sim_date == "2026-06-22"
    # The headline names the multi-run spread.
    assert "3×" in resp.headline


def test_gate_distinct_changes_stay_separate() -> None:
    sims = [
        _sim(sim_id="sim-a", change="Add an urgency countdown timer to checkout"),
        _sim(sim_id="sim-b", change="Add an urgency countdown banner to the cart"),
    ]
    resp = gate_similar("add an urgency countdown timer to checkout", sims, top_k=5)
    # Two genuinely different changes do not merge.
    assert len({m.id for m in resp.matches}) == len(resp.matches)


def test_gate_metric_is_consistent_per_hypothesis() -> None:
    """#37.4: one hypothesis renders ONE metric (the representative run's), never
    a mix of differing primary_metric values across re-runs."""
    change = "Add a 'Continue Watching' rail to the home screen"
    sims = [
        _sim(sim_id="sim-a", change=change, metric="browse", date="2026-06-18"),
        _sim(sim_id="sim-b", change=change, metric="retention", date="2026-06-22"),
    ]
    resp = gate_similar("continue watching rail home screen", sims, top_k=5)
    assert len(resp.matches) == 1
    assert resp.matches[0].primary_metric == "retention", "representative (latest) metric"


# ── short-id helper (#37.1) ───────────────────────────────────────────────────


def test_short_sim_id_shortens_a_real_uuid() -> None:
    assert short_sim_id("sim-acebe2ba-9206-4d1f-8b3a-1c2d3e4f5a6b") == "sim-ACEBE2BA"
    assert short_sim_id("exp-12345678-aaaa-bbbb-cccc-0123456789ab") == "exp-12345678"


def test_short_sim_id_shortens_a_bare_uuid() -> None:
    # The live orchestrator mints BARE uuids (str(uuid.uuid4()), no prefix) — these
    # are the common live case and must NOT leak raw into prose/citations (#37).
    assert short_sim_id("acebe2ba-9206-4d1f-8b3a-1c2d3e4f5a6b") == "sim-ACEBE2BA"
    assert short_sim_id("12345678-AAAA-BBBB-CCCC-0123456789AB") == "sim-12345678"


def test_short_sim_id_leaves_short_ids_intact() -> None:
    # Seed ids and test fixtures are already short — never mangled.
    assert short_sim_id("sim-0008") == "sim-0008"
    assert short_sim_id("sim-cw-1") == "sim-cw-1"
    assert short_sim_id("exp-0001") == "exp-0001"
    assert short_sim_id("") == ""
