"""Through-engine COMPARATIVE-delta forecaster run (#342 path A).

Same panel + cases as through_engine_powered, but uses the new comparative pass
(`compose_comparative_metric_prompt` + `visit_elicitor.elicit_visit_delta`): ONE
call per agent showing BOTH versions, asking for the directional visit-rate delta
directly — instead of two independent absolute passes subtracted. Tests whether the
comparative judgment recovers the standalone win (direction accuracy → 1.0) where
the per-arm forecaster pass stalled at 0.12.

    PYTHONPATH=backend <venv>/bin/python <thisfile> [--k 6] [--smoke]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client
from sidira_simulator.adapters.hillstrom_panel_loader import load_hillstrom_panel
from sidira_simulator.services.hillstrom_archive import load_hillstrom_csv
from sidira_simulator.services.hillstrom_adapter import build_hillstrom_case
from sidira_simulator.services.prompt_composer import compose_comparative_metric_prompt
from sidira_simulator.services.visit_elicitor import elicit_visit_delta

CSV = "/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv"
EMAILS = ["Mens E-Mail", "Womens E-Mail"]
HERE = Path(__file__).resolve().parent


def cell_lift(client, persona, case, dp, k) -> float:
    deltas = []
    for i in range(k):
        sysp = compose_comparative_metric_prompt(
            customer_id="hillstrom", persona=persona, capability=case.capability,
            hypothesis=case.hypothesis, sample_index=i,
        )
        try:
            deltas.append(elicit_visit_delta(
                client, system_prompt=sysp, capability_name=case.capability.name,
                decision_point=dp, temperature=0.0, seed=2000 + i))
        except ValueError:
            continue
    return statistics.mean(deltas) if deltas else 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    rows, _ = load_hillstrom_csv(CSV)
    personas = load_hillstrom_panel().personas
    if args.smoke:
        personas = personas[:1]
    cases = {e: build_hillstrom_case(rows, arm=e, metric_name="visit") for e in EMAILS}
    dps = {e: getattr(cases[e].hypothesis, "decision_point", None)
           or "the customer is looking at their inbox" for e in EMAILS}
    client = get_chat_client("claude-sonnet-4-6")
    emails = EMAILS[:1] if args.smoke else EMAILS
    k = 2 if args.smoke else args.k
    print(f"COMPARATIVE forecaster pass | {len(personas)} personas x {len(emails)} emails, k={k}; "
          f"RCT truth: every email RAISES visits (lift>0)\n")
    lifts = []
    for persona in personas:
        for email in emails:
            lf = cell_lift(client, persona, cases[email], dps[email], k)
            lifts.append(lf)
            print(f"  {persona.name} x {email:13s}: predicted visit lift {lf:+.3f}")
    mean = statistics.mean(lifts)
    pos = sum(1 for x in lifts if x > 0)
    dir_acc = pos / len(lifts)
    print(f"\n  COMPARATIVE forecaster: direction accuracy {dir_acc:.2f} ({pos}/{len(lifts)} positive) "
          f"| mean lift {mean:+.3f}")
    print(f"  (baselines: per-arm roleplay 0.00, per-arm forecaster 0.12)")
    if not args.smoke:
        HERE.joinpath("through_engine_comparative_result.json").write_text(
            json.dumps({"direction_accuracy": dir_acc, "mean_lift": mean,
                        "n_cells": len(lifts), "k": k}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
