"""E3-P scorer. Verifies the truths seal, then scores e3p_predictions.json
against e3p_truths.json per the sealed prereg (sha256 80f5625d...).

Run ONLY after predictions are sealed (e3p_predictions.sha256 exists).

Metrics (prereg): PREVALENCE; COVERAGE-A/B; called-set directional accuracy,
confident-wrong (called up vs truth down or called down vs truth up),
false-ship (called up, truth down), false-kill (called down, truth up);
abstain-reason distribution by estimand; baselines (always-treatment-wins,
chance, never-call); curated stratum reported separately.

Verdict: PASS  = COVERAGE-B >= 15% AND zero confident-wrong (both arms)
                 AND called-set accuracy > always-treatment-wins on same cases
         MARGINAL = COVERAGE-B in [5%,15%) AND zero confident-wrong
         KILL  = COVERAGE-B < 5% OR any confident-wrong on a called case
"""
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent


def sealed_ok(path: Path, sidecar: Path) -> bool:
    want = sidecar.read_text().split()[0]
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    return want == got


def main() -> None:
    for f, s in (("e3p_truths.json", "e3p_truths.sha256"),
                 ("e3p_predictions.json", "e3p_predictions.sha256")):
        if not sealed_ok(HERE / f, HERE / s):
            print(f"SEAL MISMATCH on {f} — refusing to score", file=sys.stderr)
            sys.exit(1)
    print("seals verified: truths + predictions\n")

    truths = {r["id"]: r["direction_primary"]
              for r in json.loads((HERE / "e3p_truths.json").read_text())}
    preds = json.loads((HERE / "e3p_predictions.json").read_text())

    report = {}
    for stratum in ("realistic", "curated"):
        sp = [p for p in preds if p["stratum"] == stratum]
        ids = sorted({p["id"] for p in sp})
        n = len(ids)
        if n == 0:
            continue
        prevalence = sum(1 for i in ids
                         if next(p for p in sp if p["id"] == i)["prevalence_flag"]) / n
        strat = {"n_cases": n, "prevalence_in_principle": round(prevalence, 3)}
        for arm in ("A", "B"):
            ap = [p for p in sp if p["arm"] == arm]
            called = [p for p in ap if p["decision"] == "call"]
            cov = len(called) / n
            correct = conf_wrong = false_ship = false_kill = flat_miss = 0
            wrong_ids = []
            for p in called:
                t = truths[p["id"]]
                d = p["direction"]
                if d == t:
                    correct += 1
                elif {d, t} == {"up", "down"}:
                    conf_wrong += 1
                    wrong_ids.append(p["id"])
                    if d == "up":
                        false_ship += 1
                    else:
                        false_kill += 1
                else:
                    flat_miss += 1
            # baselines on the same called subset + full stratum
            atw_called = sum(1 for p in called if truths[p["id"]] == "up")
            atw_full = sum(1 for i in ids if truths[i] == "up")
            reasons = Counter()
            by_estimand = defaultdict(Counter)
            for p in ap:
                if p["decision"] == "abstain":
                    reasons[p["abstain_reason"]] += 1
                    by_estimand[p.get("estimand") or "?"][p["abstain_reason"]] += 1
            strat[f"arm_{arm}"] = {
                "coverage": round(cov, 3),
                "called": len(called),
                "called_correct": correct,
                "called_accuracy": round(correct / len(called), 3) if called else None,
                "confident_wrong": conf_wrong,
                "confident_wrong_ids": wrong_ids,
                "false_ship": false_ship,
                "false_kill": false_kill,
                "flat_mismatch": flat_miss,
                "baseline_always_treatment_wins_on_called":
                    round(atw_called / len(called), 3) if called else None,
                "baseline_always_treatment_wins_full":
                    round(atw_full / n, 3),
                "abstain_reasons": dict(reasons),
                "abstain_by_estimand": {k: dict(v) for k, v in by_estimand.items()},
            }
        report[stratum] = strat

    r = report.get("realistic", {})
    covB = r.get("arm_B", {}).get("coverage", 0)
    cw = (r.get("arm_A", {}).get("confident_wrong", 0)
          + r.get("arm_B", {}).get("confident_wrong", 0))
    accB = r.get("arm_B", {}).get("called_accuracy")
    atwB = r.get("arm_B", {}).get("baseline_always_treatment_wins_on_called")
    if cw > 0 or covB < 0.05:
        verdict = "KILL"
    elif covB >= 0.15 and (accB is not None and atwB is not None and accB > atwB):
        verdict = "PASS"
    elif covB >= 0.15:
        verdict = "MARGINAL (coverage met; called-set accuracy does not beat always-treatment-wins baseline)"
    else:
        verdict = "MARGINAL"
    report["verdict"] = verdict
    report["verdict_inputs"] = {"coverage_B": covB, "confident_wrong_total": cw,
                                "called_accuracy_B": accB,
                                "always_treatment_wins_on_called_B": atwB}
    out = json.dumps(report, indent=1)
    (HERE / "e3p_score.json").write_text(out)
    print(out)


if __name__ == "__main__":
    main()
