"""Seed archive of past Sidira SIMULATIONS — predicted hypotheses (#31 fusion).

The companion to ``experiment_archive.py``. Where that archive holds REAL,
already-concluded A/B experiments (MEASURED outcomes), this one holds Sidira-engine
SIMULATIONS of hypotheses (PREDICTED outcomes). Live simulation data is DB-backed
and engine-produced — not reachable from the offline/seed path — so, exactly as
ticket #31 directs, this small synthetic-simulation seed is added parallel to the
experiment seed so the fusion is demoable offline.

The seed is DELIBERATELY PAIRED to the experiment archive: most simulations carry a
``paired_experiment_id`` pointing at the real experiment that later tested the same
change. That pairing is what lets a fused answer tell a STORY —
"we *predicted* X (Sidira sim), the real A/B *measured* Y, learning Z."

The pairings are honest about the engine, not flattering:

- Several predictions were DIRECTIONALLY RIGHT (sim-0002, sim-0008, sim-0021) — the
  engine called the winner.
- A few were DIRECTIONALLY WRONG (sim-0001 predicted the urgency timer UP; the real
  test measured a LOSS — sim-0006 likewise). Those are the most valuable rows: the
  fusion surfaces the miss instead of smoothing it over (DESIGN.md §8.3 honesty law).
- Two simulations (sim-0101, sim-0102) have NO paired experiment — a prediction with
  no measured counterpart yet, so the fusion shows the prediction standing alone,
  explicitly flagged uncalibrated.

Every number here is framed as a SIMULATED prediction (uncalibrated agreement),
never a measured effect. When this feature meets a real customer, ``_SEED`` is
replaced by their completed simulations loaded from storage; the fusion pipeline is
unchanged.
"""

from __future__ import annotations

from sidira_simulator.schemas.experiment_memory import ExperimentCategory
from sidira_simulator.schemas.simulation_archive import (
    PredictedDirection,
    SimulatedHypothesis,
)

CAT = ExperimentCategory
DIR = PredictedDirection


_SEED: tuple[SimulatedHypothesis, ...] = (
    # ── paired with experiments, prediction DIRECTIONALLY WRONG ───────────────
    SimulatedHypothesis(
        id="sim-0001",
        change_description="Add an urgency countdown timer ('offer ends in 2h') to the checkout page",
        primary_metric="checkout conversion rate",
        category=CAT.COPY,
        predicted_direction=DIR.UP,  # engine liked it; the real test did NOT
        confidence_score=71.0,
        predicted_metric_lift_pp=2.9,
        sim_date="2024-03-04",
        paired_experiment_id="exp-0001",
    ),
    SimulatedHypothesis(
        id="sim-0006",
        change_description="Use a fear-of-missing-out subject line ('You're about to lose your data') in the dunning email",
        primary_metric="email reactivation rate",
        category=CAT.COPY,
        predicted_direction=DIR.UP,  # engine liked FOMO; the real test measured a LOSS
        confidence_score=64.0,
        predicted_metric_lift_pp=1.8,
        sim_date="2024-07-23",
        paired_experiment_id="exp-0006",
    ),
    # ── paired with experiments, prediction DIRECTIONALLY RIGHT ───────────────
    SimulatedHypothesis(
        id="sim-0002",
        change_description="Reframe the headline from feature-led ('Automated reporting') to outcome-led ('Close your books 3 days faster')",
        primary_metric="landing page signup rate",
        category=CAT.COPY,
        predicted_direction=DIR.UP,
        confidence_score=78.0,
        predicted_metric_lift_pp=4.1,
        sim_date="2024-04-25",
        paired_experiment_id="exp-0002",
    ),
    SimulatedHypothesis(
        id="sim-0008",
        change_description="Raise the Pro plan price from $29 to $39 per month",
        primary_metric="revenue per visitor",
        category=CAT.PRICING,
        predicted_direction=DIR.UP,
        confidence_score=69.0,
        predicted_metric_lift_pp=5.5,
        sim_date="2024-03-21",
        paired_experiment_id="exp-0008",
    ),
    SimulatedHypothesis(
        id="sim-0021",
        change_description="Reduce the signup form from 5 fields to 2 (email + password only)",
        primary_metric="signup completion rate",
        category=CAT.FLOW,
        predicted_direction=DIR.UP,
        confidence_score=83.0,
        predicted_metric_lift_pp=7.2,
        sim_date="2024-02-19",
        paired_experiment_id="exp-0021",
    ),
    SimulatedHypothesis(
        id="sim-0024",
        change_description="Move the checkout to a single page instead of a 3-step wizard",
        primary_metric="checkout completion rate",
        category=CAT.FLOW,
        predicted_direction=DIR.UP,
        confidence_score=74.0,
        predicted_metric_lift_pp=3.6,
        sim_date="2024-03-14",
        paired_experiment_id="exp-0024",
    ),
    # ── paired, prediction MAGNITUDE OFF but direction right (price discount) ──
    SimulatedHypothesis(
        id="sim-0014",
        change_description="Run a 20%-off limited-time discount banner sitewide for new visitors",
        primary_metric="revenue per visitor",
        category=CAT.PRICING,
        predicted_direction=DIR.DOWN,  # engine correctly feared the discount eroded RPV
        confidence_score=58.0,
        predicted_metric_lift_pp=-2.1,
        sim_date="2024-07-25",
        paired_experiment_id="exp-0014",
    ),
    SimulatedHypothesis(
        id="sim-0018",
        change_description="Switch the dashboard to a dark theme by default",
        primary_metric="day-7 retention",
        category=CAT.UI,
        predicted_direction=DIR.FLAT,  # engine saw no signal; real test measured a small loss
        confidence_score=52.0,
        predicted_metric_lift_pp=0.3,
        sim_date="2024-06-23",
        paired_experiment_id="exp-0018",
    ),
    # ── UNPAIRED predictions — no measured counterpart yet ─────────────────────
    SimulatedHypothesis(
        id="sim-0101",
        change_description="Add an AI-written summary card to the top of every report",
        primary_metric="day-7 retention",
        category=CAT.UI,
        predicted_direction=DIR.UP,
        confidence_score=66.0,
        predicted_metric_lift_pp=2.4,
        sim_date="2024-08-12",
        paired_experiment_id=None,
    ),
    SimulatedHypothesis(
        id="sim-0102",
        change_description="Switch onboarding to a usage-based pricing explainer instead of a feature tour",
        primary_metric="trial-to-paid conversion",
        category=CAT.PRICING,
        predicted_direction=DIR.UP,
        confidence_score=61.0,
        predicted_metric_lift_pp=3.0,
        sim_date="2024-08-20",
        paired_experiment_id=None,
    ),
)


def seed_simulations() -> list[SimulatedHypothesis]:
    """Return a copy of the synthetic-simulation seed as a fresh list.

    Returns deep copies (``model_copy``) so a caller mutating a returned record
    can never corrupt the module-level seed shared across requests — mirrors
    ``experiment_archive.seed_experiments``.
    """
    return [s.model_copy(deep=True) for s in _SEED]
