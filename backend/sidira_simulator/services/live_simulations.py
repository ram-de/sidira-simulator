"""Adapt live, DB-backed simulation rows → the read-only ``SimulatedHypothesis``
projection the experiment-memory fusion consumes (#33).

The fusion pipeline (#31) was built against a SYNTHETIC offline seed
(``simulation_archive.seed_simulations``) because, as that module says verbatim,
"live simulation data is DB-backed and engine-produced — not reachable from the
offline/seed path." That is exactly why the ``/memory`` chat answered "no
experiments" for a hypothesis (e.g. a customer's "Continue Watching" change) that
plainly exists on the ``/simulations`` Hypotheses tab: the chat was reading the
demo seed, not the tenant's real simulations.

This adapter closes that gap. It converts the rows
``SimulationOrchestrator.list_recent`` returns — the SAME source the Hypotheses
tab lists — into ``SimulatedHypothesis`` objects, so the fused conversation
retrieves over the tenant's OWN completed simulations, scoped to their
``customer_id`` by the caller.

Firewall + honesty are unchanged from the seed path: every field maps to the live
``SimulationResult`` / ``Hypothesis`` contract; the predicted figures stay
UNCALIBRATED agreement, never a measured effect (DESIGN.md §8.3). Only COMPLETED
rows that carry a result are projected — a pending/failed/result-less row has no
prediction to cite.
"""

from __future__ import annotations

from sidira_simulator.schemas.experiment_memory import ExperimentCategory
from sidira_simulator.schemas.simulation_archive import (
    PredictedDirection,
    SimulatedHypothesis,
)

# Below this absolute pp a predicted metric delta reads as FLAT rather than a
# directional call: the engine's magnitude is uncalibrated, so a hair off zero is
# not a UP/DOWN claim (DESIGN.md §8.3 — read direction, not effect size).
_FLAT_EPSILON_PP = 0.05


def _predicted_direction(
    metric_lift_pp: float | None, lift: float | None
) -> PredictedDirection:
    """Direction of the prediction from its signed delta.

    Prefer the paired metric delta (``metric_lift_pp``); fall back to the headline
    ``lift``; FLAT when neither resolves or the signal sits inside the flat band.
    The agreement (``confidence_score``) is a magnitude in [0, 100], never a
    direction, so it is deliberately not consulted here.
    """
    signal = metric_lift_pp if metric_lift_pp is not None else lift
    if signal is None or abs(signal) < _FLAT_EPSILON_PP:
        return PredictedDirection.FLAT
    return PredictedDirection.UP if signal > 0 else PredictedDirection.DOWN


def _sim_date(row: dict) -> str:
    """Best-effort YYYY-MM-DD for the row; '' when neither timestamp is present.

    Rows carry either a ``datetime`` or an ISO string depending on the store, so we
    normalise both to the leading date.
    """
    raw = row.get("completed_at") or row.get("created_at")
    if raw is None:
        return ""
    text = raw.isoformat() if hasattr(raw, "isoformat") else str(raw)
    return text[:10]


def to_simulated_hypotheses(rows: list[dict]) -> list[SimulatedHypothesis]:
    """Project completed live-simulation rows into the fusion's PREDICTED side.

    ``rows`` are the dicts ``SimulationOrchestrator.list_recent`` returns. Rows that
    are not ``completed``, or that lack a hypothesis prose, a result, or an
    agreement score, are skipped — there is no citable prediction.
    """
    out: list[SimulatedHypothesis] = []
    for row in rows:
        if (row.get("status") or "") != "completed":
            continue
        hyp = row.get("hypothesis_json") or {}
        result = row.get("result_json") or {}
        prose = (hyp.get("prose") or "").strip()
        confidence = result.get("confidence_score")
        if not prose or not result or confidence is None:
            continue
        metric_lift_pp = result.get("metric_lift_pp")
        primary_metric = (
            hyp.get("metric_name")
            or hyp.get("capability_name")
            or "the primary metric"
        )
        out.append(
            SimulatedHypothesis(
                id=str(row.get("id") or ""),
                change_description=prose,
                primary_metric=str(primary_metric),
                # Live rows carry no firewall change-category; UI is the neutral
                # default. Category only drives PREDICTED↔MEASURED pairing, which
                # the conversation route does not exercise for a live tenant (it
                # passes no measured experiments), so this never biases retrieval.
                category=ExperimentCategory.UI,
                predicted_direction=_predicted_direction(
                    metric_lift_pp, result.get("lift")
                ),
                confidence_score=float(confidence),
                # Report ONLY a real metric delta; None (no metric computed) yields
                # a direction-only citation rather than a fabricated 0.0pp that
                # could contradict the direction (DESIGN.md §8.3).
                predicted_metric_lift_pp=(
                    float(metric_lift_pp) if metric_lift_pp is not None else None
                ),
                sim_date=_sim_date(row),
                paired_experiment_id=None,
            )
        )
    return out
