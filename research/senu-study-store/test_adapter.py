"""
test_adapter.py — smoke test the Sidira-side adapter end-to-end on the example fixtures.

Runs with plain python (no pytest needed): `python3.11 test_adapter.py`.
Verifies the MECHANICAL half (aggregate by arm, control/treatment via role, signed lift)
and the SEMANTIC half (capability/hypothesis from the arm dictionary), plus that dropped
(null-outcome) rows are surfaced, not silently folded in.
"""
from __future__ import annotations

import json
from pathlib import Path

import arm_dictionary as armdict
from senu_export_to_benchmarkcase import (
    aggregate_outcomes_by_arm,
    export_to_benchmarkcases,
)

HERE = Path(__file__).resolve().parent
ENV = json.loads((HERE / "examples/study_S123_envelope.json").read_text())
AD = armdict.load(HERE / "examples/study_S123_arm_dictionary.json")


def approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) <= tol


def test_aggregate_by_arm():
    by_arm = aggregate_outcomes_by_arm(ENV, AD["behavior_schema"])
    # cap_on: [T,T,F,T] -> 0.75 over n=4 ; cap_off: [F,T,F] valid + 1 null dropped -> 1/3, n=3
    assert by_arm["cap_on"]["n"] == 4 and approx(by_arm["cap_on"]["mean"], 0.75), by_arm
    assert by_arm["cap_off"]["n"] == 3 and approx(by_arm["cap_off"]["mean"], 1 / 3), by_arm
    assert by_arm["_dropped"]["n"] == 1, "the null-outcome row must be surfaced as dropped"
    print("  ✓ aggregate_by_arm: cap_on 0.75/n4, cap_off 0.333/n3, 1 dropped")


def test_ground_truth_uses_role():
    cases = export_to_benchmarkcases(ENV, AD, ["accept_rate"])
    gt = cases[0]["ground_truth"]
    # baseline=cap_on is control, manipulation=cap_off is treatment (from the arm ROLES)
    assert approx(gt["control_metric"], 0.75), gt
    assert approx(gt["treatment_metric"], 1 / 3), gt
    assert gt["observed_lift"] < 0 and gt["winner"] == "control", gt
    print(f"  ✓ ground_truth via role: control 0.75 vs treatment 0.333, "
          f"lift {gt['observed_lift']:+.3f}, winner={gt['winner']} (skip-cap removal LOSES)")


def test_case_id_and_semantics():
    cases = export_to_benchmarkcases(ENV, AD, ["accept_rate", "conversion"])
    assert [c["case_id"] for c in cases] == [
        "senu:S123:split_the_loot.v1:accept_rate",
        "senu:S123:split_the_loot.v1:conversion",
    ], [c["case_id"] for c in cases]
    hyp = cases[0]["hypothesis"]
    assert "cap" in hyp["summary"] and hyp["expected_direction"] == "control_higher", hyp
    assert cases[0]["capability"]["feature_pack_ref"].startswith("r2://"), cases[0]["capability"]
    print("  ✓ case_id convention + semantics from arm dictionary (capability+hypothesis)")


def test_missing_arm_raises():
    bad = {**ENV, "records": [r for r in ENV["records"] if r["blocks"][0]["arm"] != "cap_off"]}
    try:
        export_to_benchmarkcases(bad, AD, ["accept_rate"])
    except SystemExit as e:
        assert "treatment" in str(e), e
        print("  ✓ missing-treatment envelope raises (no control-less ground truth)")
        return
    raise AssertionError("expected SystemExit when the treatment arm has no rows")


if __name__ == "__main__":
    print("adapter smoke test:")
    test_aggregate_by_arm()
    test_ground_truth_uses_role()
    test_case_id_and_semantics()
    test_missing_arm_raises()
    print("ALL PASS")
