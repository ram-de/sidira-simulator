#!/usr/bin/env python3
"""Gated accuracy + cost — product-change PORTFOLIO, LIVE engine run (#39).

REAL live-engine output (prod 208cd9e, benchmark-portfolio, population_size=10,
Groq llama-3.3-70b, panel upworthy-general-us-news-v2). Per-case predicted signal
comes from the run's checkpoint; the true winner sign comes from PORTFOLIO_CASES.json.

This is the SIGN-based moat test: each of the 8 cases is one real product A/B test
with a directional outcome (treatment vs control won). We ask the question the moat
hinges on: does the engine's CONFIDENCE (here, |predicted signal|) track its
accuracy — i.e. if we ABSTAIN on the low-confidence cases and only "call" the
high-confidence ones, is the called subset more accurate? If yes, the abstention
gate earns its keep. If no, raw signal is not a usable confidence and the gate needs
a TRAINED calibrator on real outcomes (client history, #18/#20).

n=8 is BELOW the gate's certification floor (G0 wants >=50), so this ILLUSTRATES the
mechanism on real data; it does not certify it. Reported honestly either way.
"""
from __future__ import annotations

import json
from pathlib import Path

from sidira_simulator.services.directional_gate import (
    ExperimentRecord,
    balanced_sign_match_rate,
    selective_risk,
    abstention_is_monotone,
    fit_calibration,
)
from bench_store import record_run

HERE = Path(__file__).resolve().parent
CASES = json.load(open(HERE.parents[0] / "portfolio-benchmark" / "PORTFOLIO_CASES.json"))

# Per-case predicted signal from the live run's checkpoint (/tmp/portfolio_ckpt.json).
PRED = {
    "cookiecats_gate_move": 0.0,
    "cxl_form_fields_9_to_6": 0.05,
    "duolingo_weekend_amulet": 0.01,
    "msn_homepage_extra_offers": -0.03,
    "msn_realestate_widget": 0.0,
    "multistep_form_3_vs_6": 0.17,
    "office_online_redesign": -0.02,
    "tinkoff_defer_passport": 0.13,
}

# True winner sign per case (+1 = treatment won, -1 = control won) + counter-intuitive flag.
TRUE, CI = {}, {}
for c in CASES["scored_cases"]:
    TRUE[c["id"]] = 1.0 if c["real_winner"] == "treatment" else -1.0
    CI[c["id"]] = bool(c.get("counter_intuitive"))


def sgn(x: float, dead: float = 0.005) -> int:
    return 0 if abs(x) < dead else (1 if x > 0 else -1)


def main() -> None:
    recs = [
        ExperimentRecord(case_id=cid, observed_lift=TRUE[cid], predicted_signal=PRED[cid])
        for cid in PRED
    ]

    print("case                          pred_signal  pred_dir  true_dir  hit  counter_intuitive")
    for cid in sorted(PRED, key=lambda k: -abs(PRED[k])):
        pd, td = sgn(PRED[cid]), int(TRUE[cid])
        hit = "—" if pd == 0 else ("✓" if pd == td else "✗")
        print(f"{cid:30}{PRED[cid]:+6.2f}      {pd:+d}        {td:+d}      {hit}    {CI[cid]}")

    called = [(cid, sgn(PRED[cid]), int(TRUE[cid])) for cid in PRED if sgn(PRED[cid]) != 0]
    n_called = len(called)
    n_called_right = sum(1 for _, p, t in called if p == t)
    print(f"\noverall sign-match (forced, n=8):  balanced={balanced_sign_match_rate(recs, 0.0):.3f}")
    print(f"on CALLED cases (non-zero signal): {n_called_right}/{n_called} = {n_called_right/n_called:.3f}")
    print(f"engine self-abstained (|signal|~0): {8 - n_called}/8 cases")

    # ── THE MOAT TEST: does confidence (|signal|) track accuracy? ──
    # risk-coverage: order by pred_conf (|signal|); accuracy on the top-k.
    print("\nrisk-coverage (callable = most-confident first):")
    print(" coverage  callable_n  callable_accuracy")
    ordered = sorted(PRED, key=lambda k: -abs(PRED[k]))
    for k in range(1, 9):
        sub = ordered[:k]
        acc = sum(1 for cid in sub if sgn(PRED[cid]) == int(TRUE[cid])) / k
        print(f"   {k}/8       {k:<2}         {acc:.2f}")
    # The moat needs accuracy to FALL as coverage rises (high-conf = more accurate).
    fit_calibration(recs, 0.0, seed=0)
    mono = abstention_is_monotone(recs, 0.0)
    print(f"\nabstention monotone (high-conf more accurate)? {mono}")

    # most-confident call:
    top = ordered[0]
    print(f"most-confident call: {top} (signal {PRED[top]:+.2f}) -> "
          f"{'CORRECT' if sgn(PRED[top])==int(TRUE[top]) else 'WRONG'}")

    # ── Cost framing ──
    # If confidence DOESN'T track accuracy, abstaining on low-confidence saves no
    # decision quality — you'd skip real tests on cases the engine is no better at.
    # Honest $: the gate only saves money if callable_accuracy >> chance AND > the
    # always-pick-balance baseline (0.625 here). It does not on this data.
    record_run(
        run_id="portfolio-live-pop10",
        run_date="2026-06-27",
        dataset="product-portfolio",
        domain_type="sign",
        n_cases=8,
        engine_ref="LIVE prod 208cd9e · benchmark-portfolio · pop=10 · groq llama-3.3-70b",
        gated="yes (|signal| confidence proxy)",
        primary_metric=f"called_acc={n_called_right}/{n_called}",
        tail_recall_at5="",
        top5_capture="",
        top5_random="",
        callable_accuracy=f"top1=WRONG; top4=0.50; not monotone",
        abstain_rate=f"{8-n_called}/8 self-abstained (|signal|~0)",
        cost_per_experiment="$30k",
        dollars_saved="~$0 — confidence does NOT track accuracy (gate gives no lift on raw signal)",
        verdict="HONEST NEGATIVE: raw-signal abstention fails (most-confident call is wrong); moat needs a TRAINED calibrator on real outcomes (#18/#20)",
        scope_caveat="n=8 below G0 floor (illustrative, not certified); counter-intuitive cases drive the misses (more-is-better bias)",
        source_files="checkpoint /tmp/portfolio_ckpt.json + PORTFOLIO_CASES.json",
    )
    print("\nrecorded run: portfolio-live-pop10")


if __name__ == "__main__":
    main()
