"""
test_calibrator.py — pytest for the study-store → calibrator wiring (#222 slice).

Constructs engine_blind + GroundTruth dict fixtures directly (both artifact shapes) and
verifies the WIN rule (engine_blind vs measured only), abstain/tie handling, the
guard×correctness table, null-integrity, malformed-never-raises, and the power caveat.

Run: /opt/homebrew/bin/python3.11 -m pytest research/senu-study-store/test_calibrator.py -q
"""
from __future__ import annotations

from calibrator import (
    ABSTAIN,
    HIT,
    MISS,
    TIE_EXCLUDED,
    UNSCORABLE,
    CalibrationReport,
    calibrate,
    render_markdown,
    score_case,
)


def _blind(sign, guard="CONFIRMS", conf=0.6, case_id="senu:S1:sch.v1:m", **extra):
    return {"case_id": case_id, "prediction": {"sign": sign, "guard": guard, "confidence": conf},
            **extra}


def _gt(winner=None, **extra):
    d = {"metric_name": "m"}
    if winner is not None:
        d["winner"] = winner
    d.update(extra)
    return d


# --- single-case scoring ---------------------------------------------------- #
def test_correct_sign_is_hit():
    s = score_case(_blind("+"), _gt(winner="treatment"))
    assert s.outcome == HIT
    assert s.engine_sign == "+" and s.measured_sign == "+"


def test_control_winner_is_minus():
    s = score_case(_blind("-"), _gt(winner="control"))
    assert s.outcome == HIT and s.measured_sign == "-"


def test_wrong_sign_is_miss():
    s = score_case(_blind("+"), _gt(winner="control"))
    assert s.outcome == MISS
    assert s.engine_sign == "+" and s.measured_sign == "-"


def test_engine_abstain_excluded():
    s = score_case(_blind("abstain", guard="CANT-VALIDATE"), _gt(winner="treatment"))
    assert s.outcome == ABSTAIN
    assert s.engine_sign == "abstain"


def test_measured_tie_excluded():
    s = score_case(_blind("+"), _gt(winner="tie"))
    assert s.outcome == TIE_EXCLUDED
    assert s.measured_sign == "0"


def test_reads_flat_engine_blind_shape():
    # studystore `engine_blind` block is flat (no `prediction` wrapper)
    flat = {"case_id": "senu:S1:sch.v1:m", "sign": "-", "guard": "CONTRADICTS", "confidence": 0.7}
    s = score_case(flat, _gt(winner="control"))
    assert s.outcome == HIT and s.guard == "CONTRADICTS" and s.confidence == 0.7


def test_reads_measured_block_sign_shape():
    # studystore `measured` block carries a `sign`, not a `winner`
    s = score_case(_blind("-"), {"sign": "-", "effect": -0.03, "metric": "accept_rate"})
    assert s.outcome == HIT and s.measured_sign == "-"


def test_measured_sign_tilde_zero_is_tie():
    s = score_case(_blind("+"), {"sign": "~0", "metric": "m"})
    assert s.outcome == TIE_EXCLUDED and s.measured_sign == "0"


# --- malformed never raises ------------------------------------------------- #
def test_malformed_is_unscorable_never_raises():
    assert score_case({"prediction": {"sign": "???"}}, {"winner": "banana"}).outcome == UNSCORABLE
    assert score_case(None, None).outcome == UNSCORABLE
    assert score_case({}, {}).outcome == UNSCORABLE
    # missing only one side is still unscorable, not a crash
    assert score_case(_blind("+"), {"metric_name": "m"}).outcome == UNSCORABLE


# --- null-integrity --------------------------------------------------------- #
def test_null_marker_directional_prediction_is_violation():
    s = score_case(_blind("+", null_case=True, case_id="senu:S1:sch.v1:m"), _gt(winner="control"))
    assert s.is_null and s.null_violation


def test_null_aa_name_directional_prediction_is_violation():
    s = score_case(_blind("+", case_id="senu:S1:sch.v1:aa_placebo"),
                   _gt(winner="control", metric_name="aa_placebo"))
    assert s.is_null and s.null_violation


def test_null_case_with_abstain_is_no_violation():
    s = score_case(_blind("abstain", null_case=True, case_id="senu:S1:sch.v1:a_a"),
                   _gt(winner="tie"))
    assert s.is_null and not s.null_violation


def test_non_null_regular_metric_not_flagged():
    s = score_case(_blind("+", case_id="senu:S1:sch.v1:accept_rate"), _gt(winner="treatment"))
    assert not s.is_null and not s.null_violation


# --- aggregate calibrate ---------------------------------------------------- #
def _mixed_report() -> CalibrationReport:
    pairs = [
        (_blind("+", guard="CONFIRMS"), _gt(winner="treatment")),          # HIT / CONFIRMS
        (_blind("+", guard="CONFIRMS"), _gt(winner="treatment")),          # HIT / CONFIRMS
        (_blind("+", guard="CONFIRMS"), _gt(winner="control")),            # MISS / CONFIRMS
        (_blind("-", guard="CONTRADICTS"), _gt(winner="control")),         # HIT / CONTRADICTS
        (_blind("abstain", guard="CANT-VALIDATE"), _gt(winner="treatment")),  # ABSTAIN / CANT-VALIDATE
        (_blind("+", guard="CONFIRMS"), _gt(winner="tie")),                # TIE_EXCLUDED / CONFIRMS
    ]
    return calibrate(pairs)


def test_directional_accuracy_and_abstain_rate():
    r = _mixed_report()
    assert r.hits == 3 and r.misses == 1 and r.abstains == 1 and r.tie_excluded == 1
    # directional accuracy = 3 / (3+1) = 0.75
    assert abs(r.directional_accuracy - 0.75) < 1e-9
    # abstain rate = 1 / (3+1+1) = 0.2
    assert abs(r.abstain_rate - 0.2) < 1e-9


def test_guard_table_tallies():
    t = _mixed_report().guard_table
    assert t["CONFIRMS"][HIT] == 2 and t["CONFIRMS"][MISS] == 1 and t["CONFIRMS"][TIE_EXCLUDED] == 1
    assert t["CONTRADICTS"][HIT] == 1
    assert t["CANT-VALIDATE"][ABSTAIN] == 1


def test_directional_accuracy_none_when_no_directional_cases():
    r = calibrate([(_blind("abstain"), _gt(winner="treatment"))])
    assert r.directional_accuracy is None


# --- power honesty ---------------------------------------------------------- #
def test_power_caveat_present_and_loud_for_tiny_n():
    r = _mixed_report()
    assert r.underpowered
    md = render_markdown(r, "test")
    assert "POWER CAVEAT" in md and "track-record" in md
    assert "150" in md  # the floor is named


def test_report_json_states_scaffold_and_win_rule():
    d = _mixed_report().to_dict()
    assert d["scaffold"] is True
    assert "human_truth" in d["win_definition"] and "engine_blind" in d["win_definition"]
    assert "222" in d["note"]


def test_null_violation_counted_in_report():
    pairs = [
        (_blind("+", case_id="senu:S1:sch.v1:aa"), _gt(winner="control", metric_name="aa")),  # violation
        (_blind("abstain", case_id="senu:S1:sch.v1:a_a"), _gt(winner="tie", metric_name="a_a")),  # ok
    ]
    r = calibrate(pairs)
    assert r.null_cases == 2 and r.null_violations == 1


# --- store loading skips unpaired / non-final rows -------------------------- #
def test_load_store_pairs_skips_unpaired_and_nonfinal(tmp_path):
    import json as _json

    from calibrator import load_store_pairs

    recs = [
        # SCORED + paired → included
        {"case_id": "senu:S1:sch.v1:m", "status": "SCORED",
         "engine_blind": {"sign": "+", "guard": "CONFIRMS"}, "measured": {"sign": "+"}},
        # PENDING (empty measured) → skipped
        {"case_id": "senu:S2:sch.v1:m", "status": "PENDING",
         "engine_blind": {}, "measured": {}},
        # RUNNING → skipped
        {"case_id": "senu:S3:sch.v1:m", "status": "RUNNING",
         "engine_blind": {"sign": "+"}, "measured": {}},
        # VOID (even if it has both blocks) → skipped
        {"case_id": "senu:S4:sch.v1:m", "status": "VOID",
         "engine_blind": {"sign": "+"}, "measured": {"sign": "+"}},
        # ABSTAINED + paired → included
        {"case_id": "senu:S5:sch.v1:m", "status": "ABSTAINED",
         "engine_blind": {"sign": "abstain", "guard": "CANT-VALIDATE"}, "measured": {"sign": "-"}},
    ]
    store = tmp_path / "studies.jsonl"
    store.write_text("\n".join(_json.dumps(r) for r in recs) + "\n")

    pairs, skipped = load_store_pairs(store)
    assert skipped == 3  # PENDING, RUNNING, VOID
    ids = {cid for _, _, cid in pairs}
    assert ids == {"senu:S1:sch.v1:m", "senu:S5:sch.v1:m"}


if __name__ == "__main__":
    import sys

    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
