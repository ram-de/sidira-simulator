"""
score_streamly_v2.py — unseal + score the negative-control guard (iter1).

Verifies sha256, then evaluates the sealed predictions of PREREG_ITER1_NEGCONTROL.md:
 P1 guard trips on unobserved-confounder regimes; P2 guard does NOT trip on clean/observed;
 P3 (honest limit) guard need not catch true_null. Writes synthetic_streamly_v2_scorecard.md.
"""
from __future__ import annotations
import hashlib, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEALED = Path.home() / "streamly_challenge_v2_SEALED.json"
SHA = HERE / "SYNTHETIC_STREAMLY_V2_ANSWERS.sha256"
PRED = HERE / "synthetic_streamly_v2_predictions.json"
CARD = HERE / "synthetic_streamly_v2_scorecard.md"
UNOBS = {"unobserved_no_proxy", "unobserved_with_proxy"}
CLEAN_OBS = {"clean_rct_moderate", "clean_rct_small", "confounded_observed_moderate",
             "confounded_sign_flip", "confounded_strong_poor_overlap",
             "confounded_nonlinear", "heterogeneous_net_positive"}
W = {"positive": "treatment", "negative": "control", "null": "null/uncertain"}


def main():
    payload = SEALED.read_text()
    digest = hashlib.sha256(payload.encode()).hexdigest()
    integ = "OK" if digest == SHA.read_text().split()[0] else "FAIL — HASH MISMATCH"
    ans = {d["filename"]: d for d in json.loads(payload)["datasets"]}
    preds = {p["filename"]: p for p in json.loads(PRED.read_text())["predictions"]}

    rows = []
    unobs_caught = unobs_tot = clean_falsealarm = clean_tot = 0
    err_no_guard = err_with_guard = 0
    for fn in sorted(ans):
        a, p = ans[fn], preds[fn]
        reg, tsign = a["regime"], a["true_sign"]
        right = p["predicted_winner"] == W[tsign]
        trip = p["neg_control_tripped"]
        # error accounting: without guard we'd act on every prediction; with guard we abstain on trips
        if not right:
            err_no_guard += 1
            if not trip:
                err_with_guard += 1          # guard FAILED to catch this error
        if reg in UNOBS:
            unobs_tot += 1; unobs_caught += int(trip)
        if reg in CLEAN_OBS:
            clean_tot += 1; clean_falsealarm += int(trip and right)  # tripped a case it got RIGHT
        rows.append((fn, reg, tsign, p["predicted_winner"], right, p["neg_control_ate"], trip,
                     p["confidence"]))

    p1 = unobs_caught == unobs_tot
    p2 = clean_falsealarm == 0
    verdict = ("LEAD — negative-control guard catches the unobserved-confounder errors overlap "
               "missed, with no false alarms on clean/observed cases."
               if (p1 and p2) else
               "NULL — guard did not cleanly separate (see P1/P2 below).")

    md = [f"# Negative-control guard — Scorecard (iter1)", "",
          f"**Integrity:** sha256 `{digest[:16]}…` — {integ}", "",
          "> Self-generated seed-blind => MECH-ONLY. Real-data replication still required.", "",
          f"**P1 (guard trips on unobserved-confounder regimes):** {unobs_caught}/{unobs_tot} "
          f"-> {'PASS' if p1 else 'FAIL'}",
          f"**P2 (no false alarm on clean/observed cases it got right):** "
          f"{clean_tot - clean_falsealarm}/{clean_tot} clean -> {'PASS' if p2 else 'FAIL'}",
          f"**Error reduction:** without guard {err_no_guard} wrong actions; with guard "
          f"(abstain on trips) {err_with_guard} wrong actions remain.", "",
          "| File | Regime | True | Causal | ✓ | neg_control ATE | Tripped | Conf |",
          "|---|---|---|---|---|---|---|---|"]
    for fn, reg, ts, cw, ok, nca, trip, cf in rows:
        md.append(f"| {fn} | {reg} | {ts} | {cw} | {'Y' if ok else 'N'} | {nca:+.4f} | "
                  f"{'TRIP' if trip else '·'} | {cf} |")
    md += ["", "## Verdict", "", verdict,
           "", "Honest limit (P3, predicted): the guard keys on a negative-control outcome that "
           "shares the confounding; it catches HIDDEN confounding but not pure estimator residual "
           "on a true null unless that residual also shows on the control. Negative controls are a "
           "necessary guard, not a complete certificate — and in the router they require knowing "
           "WHICH metric is a valid negative control (LLM/domain judgment)."]
    CARD.write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nSUMMARY p1={p1} p2={p2} err {err_no_guard}->{err_with_guard} integ={integ!r}")


if __name__ == "__main__":
    main()
