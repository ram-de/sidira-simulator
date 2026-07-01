"""
senu_export_to_benchmarkcase.py — Senu export -> BenchmarkCase adapter (ticket #547 part B).

Turn a completed Senu study's `senu.export.v1` envelope into the SAME
`(Capability, Hypothesis, GroundTruth)` `BenchmarkCase` shape the Sidira engine scores
in production (`backend/sidira_simulator/schemas/benchmark.py`). Once wired, a Senu
result joins the engine's benchmark harness with zero special-casing and lands a real
predicted-vs-actual pair in the #222 conversion_calibrator.

WHAT'S MECHANICAL (buildable NOW) vs SEMANTIC (Sidira-side arm dictionary)
--------------------------------------------------------------------------
A `BenchmarkCase` has two halves:

  1. GroundTruth  (control_metric, treatment_metric, observed_lift, winner)
     MECHANICAL — built here, NOW. The envelope's `ab_outcome` rows carry the assigned
     `arm` + the frozen primary `outcome`; we aggregate outcome BY arm, then use the arm
     ROLE (baseline=control, manipulation=treatment) to label the sides. The role is
     GENERIC Senu data — it comes from the StudySpec / our Sidira-side arm dictionary,
     NOT a guess. (Earlier this file "refused to guess" control vs treatment; that was
     over-cautious — the role already tells us.)

  2. Capability + Hypothesis  (current-state PRD/Figma + the proposed state-diff)
     SEMANTIC — needs the SIDIRA-SIDE arm dictionary (`arm_dictionary.py`), because
     "the manipulation arm = removed the skip-cap from THIS customer's product" is
     customer-specific and cannot live in multi-tenant Senu. Given the arm dictionary
     we assemble a capability/hypothesis dict here; final pydantic construction +
     `render_state_diff` happen in the backend when wired.

This module stays infra-free (plain python, no backend import) so the research store
runs anywhere. When promoted, move the finished pydantic construction into
`backend/sidira_simulator/services/benchmark_adapter.py` beside the Upworthy adapter
and keep this as the thin research-side caller.

CONTRACT DOCS (authoritative, senu repo):
  - senu/packages/core/src/exportEnvelope.ts  (AbOutcomeBlock — the real shape)
  - senu/packages/core/src/studySpec.ts        (arm roles: baseline/manipulation)
"""
from __future__ import annotations

import json
from pathlib import Path

import arm_dictionary as armdict


# --------------------------------------------------------------------------- #
# MECHANICAL half — aggregate the envelope's ab_outcome rows by arm.
# --------------------------------------------------------------------------- #
def _iter_ab_rows(envelope: dict, behavior_schema: str, primary_outcome: str | None):
    """Yield every `ab_outcome` block matching the schema (and primaryOutcome, if given).

    A senu.export.v1 envelope is a set of per-respondent records; each carries one or
    more blocks with `kind: "ab_outcome"`. We accept a few plausible container shapes so
    the adapter is robust to the exact top-level envelope framing (records[] / rows[] /
    a flat list), and filter to the requested behavior schema.
    """
    records = (
        envelope.get("records")
        or envelope.get("rows")
        or envelope.get("respondents")
        or (envelope if isinstance(envelope, list) else [])
    )
    for rec in records:
        blocks = rec.get("blocks", [rec]) if isinstance(rec, dict) else []
        for b in blocks:
            if not isinstance(b, dict) or b.get("kind") != "ab_outcome":
                continue
            if b.get("schema") not in (behavior_schema, None):
                continue
            if primary_outcome and b.get("primaryOutcome") not in (primary_outcome, None):
                continue
            yield b


def aggregate_outcomes_by_arm(
    envelope: dict, behavior_schema: str, primary_outcome: str | None = None
) -> dict[str, dict]:
    """Return {arm_name: {"mean": float, "n": int}} over the frozen primary outcome.

    Binary outcomes (bool) average to a rate; continuous outcomes (number) average to a
    mean. Rows with a null arm/outcome (sanitized away) are skipped and counted as
    dropped — never silently folded into an arm.
    """
    acc: dict[str, list[float]] = {}
    dropped = 0
    for b in _iter_ab_rows(envelope, behavior_schema, primary_outcome):
        arm, out = b.get("arm"), b.get("outcome")
        if arm is None or out is None:
            dropped += 1
            continue
        acc.setdefault(arm, []).append(float(out))
    result = {arm: {"mean": sum(v) / len(v), "n": len(v)} for arm, v in acc.items()}
    if dropped:
        result["_dropped"] = {"mean": float("nan"), "n": dropped}  # visible, not hidden
    return result


def ground_truth_from_export(
    envelope: dict, arm_dict: dict, ground_truth_name: str
) -> dict:
    """MECHANICAL half — buildable now. Uses arm ROLE to label control vs treatment.

    `ground_truth_name` is the metric label we file this case under (e.g. "accept_rate").
    The measured value is the frozen primary outcome from the envelope; control = the
    baseline arm, treatment = the manipulation arm, both read from the arm dictionary's
    roles (which mirror Senu's generic StudySpec roles).
    """
    armdict.validate(arm_dict)
    by_arm = aggregate_outcomes_by_arm(envelope, arm_dict["behavior_schema"])
    ctrl_name = armdict.baseline_name(arm_dict)
    trt_name = armdict.manipulation_name(arm_dict)
    if ctrl_name not in by_arm or trt_name not in by_arm:
        raise SystemExit(
            f"ground_truth_from_export: envelope has no rows for "
            f"{'control ' + ctrl_name if ctrl_name not in by_arm else ''}"
            f"{'treatment ' + trt_name if trt_name not in by_arm else ''}; "
            f"saw arms {sorted(k for k in by_arm if not k.startswith('_'))}"
        )
    c = by_arm[ctrl_name]["mean"]
    t = by_arm[trt_name]["mean"]
    lift = t - c
    winner = "treatment" if lift > 0 else "control" if lift < 0 else "tie"
    return {
        "metric_name": ground_truth_name,
        "control_metric": c,
        "treatment_metric": t,
        "observed_lift": lift,        # magnitude recorded; engine scored on SIGN downstream
        "winner": winner,
        "n_control": by_arm[ctrl_name]["n"],
        "n_treatment": by_arm[trt_name]["n"],
    }


# --------------------------------------------------------------------------- #
# SEMANTIC half — assemble capability/hypothesis from the Sidira-side arm dictionary.
# --------------------------------------------------------------------------- #
def capability_hypothesis_from_arm_dictionary(arm_dict: dict) -> dict:
    """Build the (capability, hypothesis) product-change halves from the arm dictionary.

    This is the customer-specific semantics Senu can't hold. We emit plain dicts shaped
    for the backend `Capability`/`Hypothesis` builders; the current-state grounding is
    the crawled feature pack (`feature_pack_ref`). Final pydantic construction + the
    exact `render_state_diff` string are a backend concern (the production renderer),
    kept out of this infra-free research module on purpose.
    """
    armdict.validate(arm_dict)
    ch = arm_dict["product_change"]
    return {
        "capability": {
            "feature_pack_ref": arm_dict.get("feature_pack_ref"),
            "current_state": ch["current_state"],
        },
        "hypothesis": {
            "summary": ch["summary"],
            "proposed_state": ch["proposed_state"],
            "not_changing": ch.get("not_changing", []),
            "expected_direction": arm_dict.get("expected_direction"),
        },
    }


def export_to_benchmarkcases(
    envelope: dict,
    arm_dict: dict,
    ground_truth_names: list[str],
) -> list[dict]:
    """Emit one BenchmarkCase-shaped dict per named ground truth.

    Keyed by the store convention `senu:<studyId>:<behaviorSchema>:<groundTruthName>`.
    The GroundTruth half is always populated (mechanical); the capability/hypothesis
    half is populated from the arm dictionary (the Sidira-side semantics).
    """
    armdict.validate(arm_dict)
    study_id = arm_dict["study_id"]
    behavior_schema = arm_dict["behavior_schema"]
    semantics = capability_hypothesis_from_arm_dictionary(arm_dict)
    cases: list[dict] = []
    for gt_name in ground_truth_names:
        cases.append({
            "case_id": f"senu:{study_id}:{behavior_schema}:{gt_name}",
            "source": f"senu:{study_id}",
            "capability": semantics["capability"],
            "hypothesis": semantics["hypothesis"],
            "ground_truth": ground_truth_from_export(envelope, arm_dict, gt_name),
        })
    return cases


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="senu.export.v1 -> BenchmarkCase[]")
    ap.add_argument("--envelope", required=True, help="path to a senu.export.v1 json")
    ap.add_argument("--arm-dictionary", required=True, help="path to the Sidira-side arm dictionary")
    ap.add_argument("--ground-truths", required=True, help="comma-separated metric names")
    args = ap.parse_args()

    env = json.loads(Path(args.envelope).read_text())
    ad = armdict.load(args.arm_dictionary)
    out = export_to_benchmarkcases(env, ad, args.ground_truths.split(","))
    print(json.dumps(out, indent=2))
