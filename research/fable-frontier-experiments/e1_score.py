"""E1 scorer — unseals e1_answers.json AFTER all predictions are recorded.

Verifies the answers fingerprint, scores CALC and LLM-TABLES against the
pre-registered thresholds (PREREG_E1), writes e1_score.json.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent

sealed = (HERE / "e1_answers.json").read_bytes()
digest = hashlib.sha256(sealed).hexdigest()
recorded = (HERE / "e1_answers.sha256").read_text().split()[0]
assert digest == recorded, f"FINGERPRINT MISMATCH {digest} != {recorded}"

answers = {a["id"]: a for a in json.loads(sealed)["answers"]}
cases = {c["id"]: c for c in json.loads((HERE / "e1_cases.json").read_text())}
preds = json.loads((HERE / "e1_predictions.json").read_text())["predictions"]

SIGN = {"up": "+", "down": "-"}


def score(kind: str) -> dict:
    rows, res = [], {"flip": {"correct": 0, "wrong": 0, "abstain": 0},
                     "onesign": {"correct": 0, "wrong": 0, "abstain": 0}}
    for p in preds:
        cid = p["id"]
        truth = answers[cid]["true_sign"]
        d = p[kind]["direction"]
        bucket = "flip" if cases[cid]["flip"] else "onesign"
        if d == "abstain":
            res[bucket]["abstain"] += 1
            outcome = "abstain"
        elif SIGN[d] == truth:
            res[bucket]["correct"] += 1
            outcome = "correct"
        else:
            res[bucket]["wrong"] += 1
            outcome = "WRONG"
        rows.append({"id": cid, "bucket": bucket, "pred": d, "truth": truth,
                     "outcome": outcome})
    return {"summary": res, "rows": rows}


calc = score("CALC")
llm = score("LLM_TABLES")

cc = json.loads((HERE / "e1_cookiecats_predictions.json").read_text())
cc_truth = {"retention_7": "down", "retention_1": "down"}  # public sealed result
cc_calc_ok = all(cc["CALC"][m]["direction"] == cc_truth[m] for m in cc_truth)
cc_llm_ok = all(cc["LLM_TABLES"].get(m) == cc_truth[m] for m in cc_truth)

f = calc["summary"]["flip"]
o = calc["summary"]["onesign"]
verdict = "PASS" if (f["correct"] >= 9 and f["wrong"] == 0 and f["abstain"] <= 6
                     and o["wrong"] == 0 and cc_calc_ok) else (
    "KILL" if (f["wrong"] > 0 or f["correct"] < 6) else "FAIL-BY-ABSTENTION")

out = {
    "prereg": "PREREG_E1_ARITHMETIC_SUFFICIENCY.md",
    "answers_sha256_verified": digest,
    "CALC": calc, "LLM_TABLES": llm,
    "cookiecats": {"CALC_recovers_both_signs": cc_calc_ok,
                   "LLM_TABLES_recovers_both_signs": cc_llm_ok,
                   "CALC_deltas_pp": {m: cc["CALC"][m]["delta_pp"] for m in cc_truth}},
    "verdict": verdict,
}
(HERE / "e1_score.json").write_text(json.dumps(out, indent=1))
print(json.dumps({k: out[k] for k in ("verdict", "cookiecats")}, indent=1))
print("CALC  flip:", f, " onesign:", o)
print("LLM   flip:", llm["summary"]["flip"], " onesign:", llm["summary"]["onesign"])
wrongs = [r for r in llm["rows"] if r["outcome"] == "WRONG"]
print("LLM wrong cells:", [r["id"] for r in wrongs])
