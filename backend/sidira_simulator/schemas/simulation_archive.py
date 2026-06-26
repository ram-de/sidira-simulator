"""Synthetic-simulation archive schema (#31 fusion).

The experiment-memory chat grounds in two kinds of evidence:

- a REAL, already-concluded A/B experiment (``schemas.experiment_memory.Experiment``)
  — a MEASURED outcome, and
- a Sidira-engine SIMULATION of a hypothesis — a PREDICTED outcome.

This module is the PREDICTED side. It is a small read-only PROJECTION of the live
``schemas.simulation.Simulation`` / ``SimulationResult`` contract (which is
DB-backed and engine-produced, so it is NOT reachable from the offline/seed path).
We deliberately do NOT import or refactor the live simulation model — fusion is a
read over a flattened, demoable projection that carries exactly the predicted
fields a fused answer needs.

Firewall, mirroring ``Experiment``: the INPUT side (``change_description``,
``primary_metric``, ``category``) drives retrieval; the PREDICTED-outcome side
(``predicted_direction``, ``confidence_score``, ``predicted_metric_lift_pp``) is
attached after ranking, never used to rank. A prediction can never leak into the
features that match it to a real experiment.

Honesty law (DESIGN.md §8.3, mirrored here): a prediction is labeled UNCALIBRATED
— it is simulated-agent agreement, never a measured effect. The fusion answer
states "PREDICTED" beside every figure sourced here.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

# Reuse the experiment archive's change-category vocabulary so a simulated
# hypothesis and a real experiment can be matched on the same axis (#31 pairing).
from sidira_simulator.schemas.experiment_memory import ExperimentCategory


class PredictedDirection(str, Enum):
    """The DIRECTION a simulation predicted for the treatment.

    Mirrors the real ``ExperimentResult`` win/loss/flat trichotomy so a fused
    answer can say "we predicted UP, the real test measured DOWN" cleanly. This
    is a direction CALL (which way the simulated panel leaned), never a measured
    effect — magnitude is uncalibrated (DESIGN.md §8.3).
    """

    UP = "up"  # the simulated panel favored the treatment
    DOWN = "down"  # the simulated panel disfavored the treatment
    FLAT = "flat"  # the simulated panel was indistinguishable from control


class SimulatedHypothesis(BaseModel):
    """One Sidira-engine simulation of a hypothesis — a PREDICTED outcome.

    A flattened projection of a completed A/B-mode ``Simulation`` shaped for
    retrieval + citation. Field meanings track the live contract:

    INPUT side (drives retrieval): id, change_description, primary_metric, category.
    PREDICTED side (attached after ranking, never ranks): predicted_direction,
    confidence_score, predicted_metric_lift_pp, sim_date.
    """

    id: str = Field(description="Simulation designator, e.g. sim-0008.")
    change_description: str = Field(
        description="The hypothesis the engine simulated — input side. "
        "Mirrors Hypothesis.prose / the change under test."
    )
    primary_metric: str = Field(
        description="The OEC the prediction is expressed on (maps to Hypothesis.metric_name)."
    )
    category: ExperimentCategory
    # ── predicted-outcome side ────────────────────────────────────────────
    predicted_direction: PredictedDirection
    confidence_score: float = Field(
        ge=0.0,
        le=100.0,
        description=(
            "Raw simulated-agent AGREEMENT (0-100), UNCALIBRATED — the live "
            "SimulationResult.confidence_score. Never a measured probability."
        ),
    )
    predicted_metric_lift_pp: float | None = Field(
        default=None,
        description=(
            "Predicted paired treatment-control delta on the primary metric, in "
            "percentage points. The live SimulationResult.metric_lift_pp. "
            "Uncalibrated — read as rank/direction, not effect size (DESIGN.md §8.3). "
            "None when no metric delta was computed (e.g. a non-metric run): the "
            "citation then reports DIRECTION only and never fabricates a magnitude."
        ),
    )
    sim_date: str = Field(description="ISO date the simulation ran (YYYY-MM-DD).")
    # Optional explicit link to the real experiment this prediction is paired
    # with, when one exists in the experiment archive. Lets the fusion compose a
    # PREDICTED-vs-MEASURED story without re-deriving the pairing by similarity.
    paired_experiment_id: str | None = Field(
        default=None,
        description=(
            "Id of the real Experiment that later tested the same change, when "
            "known. None when the prediction has no measured counterpart yet."
        ),
    )
