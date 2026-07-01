"""
senu_export_to_benchmarkcase.py — ADAPTER STUB (ticket #547, part B).

Turn a completed Senu study's `senu.export.v1` envelope into the SAME
`(Capability, Hypothesis, GroundTruth)` `BenchmarkCase` shape the Sidira engine
scores in production (`backend/sidira_simulator/schemas/benchmark.py`). Once this
exists, a Senu result joins the engine's benchmark harness with zero special-casing
and lands a real predicted-vs-actual pair in the #222 conversion_calibrator.

WHY A STUB, NOT FINISHED CODE
-----------------------------
A `BenchmarkCase` has two halves, and only one is mechanically derivable from a
Senu export today:

  1. GroundTruth  (metric_name, control_metric, treatment_metric, observed_lift,
                   winner)  ..............................  MECHANICAL — buildable NOW.
     The export carries per-arm outcome metrics; this is arithmetic + a sign.

  2. Capability + Hypothesis  (current-state PRD/Figma + the proposed state-diff)
                              ...........................  NEEDS THE ARM DICTIONARY.
     A Senu game emits ROLE-named arms (`calm`/`urgent`, `headline-A`/`headline-B`)
     with ZERO engine coupling (calibration contract §11). To render that as a
     production `(Capability, Hypothesis)` we need a per-study **arm dictionary**:
       - which role is CONTROL (current state) vs TREATMENT (proposed change),
       - what product change the treatment expresses, in state-diff terms.
     That dictionary lives on the Senu side and is GATED on the written
     Sidira–Senu data agreement (ticket #547 part C). Until it exists, we can
     produce the GroundTruth half and leave the case `capability/hypothesis` unset.

CONTRACT DOCS (authoritative, in the senu repo):
  - senu/docs/EXPORT_ENVELOPE.md            (senu.export.v1 shape)
  - senu/docs/SIDIRA_BENCHMARKCASE_ADAPTER.md (this adapter's spec, draft)

This file deliberately does NOT import from `backend/…` — the store stays infra-free
and runnable with plain python. When part C lands, either wire the real pydantic
models in here, or (cleaner) move the finished adapter into
`backend/sidira_simulator/services/benchmark_adapter.py` beside the Upworthy one and
keep this as the thin research-side caller.
"""
from __future__ import annotations

import json
from pathlib import Path


def ground_truth_from_export(envelope: dict, ground_truth_name: str) -> dict:
    """MECHANICAL half — buildable now.

    Pull the per-arm metric for `ground_truth_name` out of a senu.export.v1 envelope
    and return a GroundTruth-shaped dict (control_metric, treatment_metric,
    observed_lift = treatment - control, winner). Direction only downstream — the
    magnitude is recorded but the engine is scored on sign (README §Scoring).

    Requires the arm dictionary to know which role is control vs treatment; if the
    envelope has exactly two arms and one is flagged `is_control`, we use that.
    Otherwise we raise, rather than guess — a mislabeled control silently flips the
    sign of every downstream score.
    """
    arms = envelope.get("arms") or envelope.get("outcomes") or []
    if len(arms) != 2:
        raise NotImplementedError(
            f"ground_truth_from_export handles 2-arm studies only for now; "
            f"got {len(arms)} arms. Multi-arm needs the arm dictionary (part C)."
        )
    control = next((a for a in arms if a.get("is_control")), None)
    treatment = next((a for a in arms if not a.get("is_control")), None)
    if control is None or treatment is None:
        raise NotImplementedError(
            "cannot identify control vs treatment from the envelope alone — this is "
            "exactly what the per-study ARM DICTIONARY (ticket #547 part C) supplies. "
            "Refusing to guess: a mislabeled control flips the sign of the score."
        )
    c = float(control["metrics"][ground_truth_name])
    t = float(treatment["metrics"][ground_truth_name])
    lift = t - c
    winner = "treatment" if lift > 0 else "control" if lift < 0 else "tie"
    return {
        "metric_name": ground_truth_name,
        "control_metric": c,
        "treatment_metric": t,
        "observed_lift": lift,
        "winner": winner,
    }


def capability_hypothesis_from_export(envelope: dict, arm_dictionary: dict) -> dict:
    """GATED half — needs the arm dictionary (ticket #547 part C).

    Given the current-state grounding (reverse-engineered PRD/Figma, the crawled
    feature pack) and the arm dictionary's control/treatment mapping + change
    description, build the production `(Capability, Hypothesis)` pair so
    `render_state_diff(capability, hypothesis)` yields the exact string the engine
    reads. Left unimplemented until the data agreement defines the arm dictionary.
    """
    raise NotImplementedError(
        "capability/hypothesis synthesis is gated on the Sidira–Senu data agreement "
        "and the per-study arm dictionary (ticket #547 part C). See "
        "senu/docs/SIDIRA_BENCHMARKCASE_ADAPTER.md."
    )


def export_to_benchmarkcases(
    envelope: dict,
    study_id: str,
    behavior_schema: str,
    ground_truth_names: list[str],
    arm_dictionary: dict | None = None,
) -> list[dict]:
    """Emit one partial BenchmarkCase-shaped dict per named ground truth.

    Produces the GroundTruth half now and, when `arm_dictionary` is supplied,
    attempts the capability/hypothesis half too. Keyed by the store's `case_id`
    convention: `senu:<studyId>:<behaviorSchema>:<groundTruthName>`.
    """
    cases: list[dict] = []
    for gt_name in ground_truth_names:
        case_id = f"senu:{study_id}:{behavior_schema}:{gt_name}"
        case: dict = {
            "case_id": case_id,
            "source": f"senu:{study_id}",
            "ground_truth": ground_truth_from_export(envelope, gt_name),
            "capability": None,
            "hypothesis": None,
        }
        if arm_dictionary is not None:
            case.update(capability_hypothesis_from_export(envelope, arm_dictionary))
        cases.append(case)
    return cases


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="senu.export.v1 -> BenchmarkCase[] (stub)")
    ap.add_argument("--envelope", required=True, help="path to a senu.export.v1 json")
    ap.add_argument("--study-id", required=True)
    ap.add_argument("--behavior-schema", required=True)
    ap.add_argument("--ground-truths", required=True, help="comma-separated metric names")
    args = ap.parse_args()

    env = json.loads(Path(args.envelope).read_text())
    out = export_to_benchmarkcases(
        env, args.study_id, args.behavior_schema, args.ground_truths.split(",")
    )
    print(json.dumps(out, indent=2))
