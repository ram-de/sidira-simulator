"""Powered through-ENGINE re-benchmark (#342 path A, increment 2 — at panel scale).

Drives the PRODUCTION metric-elicitation seam — `prompt_composer.compose_metric_prompt`
(now flag-aware) + `visit_elicitor.elicit_visit_decision` — over the real Hillstrom
panel, paired control(no-email) vs treatment(email), K agents/arm, under roleplay
vs forecaster. Confirms the deployed default (forecaster) carries the certified
SIGN fix through the engine at panel scale (vs the 3-persona smoke). RCT truth:
every email RAISES visits → direction accuracy is the headline.

Scope note: heterogeneity (who-responds-more) was certified STANDALONE
(forecaster_heterogeneity: visit rank-ρ +0.42 p=0.01, gender-match +0.75
p=0.0004); the full-panel heterogeneity run is the prod harness's job. This is the
engine-wiring confirmation of the direction fix, run locally (not on the prod box).

    PYTHONPATH=backend <venv>/bin/python <thisfile> [--k 6]
"""
from __future__ import annotations

import argparse
import statistics
import sys

from sidira_simulator.adapters.llm import get_chat_client
from sidira_simulator.adapters.hillstrom_panel_loader import load_hillstrom_panel
from sidira_simulator.services.hillstrom_archive import load_hillstrom_csv
from sidira_simulator.services.hillstrom_adapter import build_hillstrom_case
from sidira_simulator.services.prompt_composer import compose_metric_prompt
from sidira_simulator.services.visit_elicitor import elicit_visit_decision, VISIT_LABEL

CSV = "/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv"
EMAILS = ["Mens E-Mail", "Womens E-Mail"]


def mean_p_visit(client, persona, case, arm, mode, dp, k) -> float:
    ps = []
    for i in range(k):
        sysp, _ = compose_metric_prompt(
            customer_id="hillstrom", persona=persona, capability=case.capability,
            hypothesis=case.hypothesis, arm=arm, elicitation_mode=mode, sample_index=i,
        )
        dec = elicit_visit_decision(
            client, system_prompt=sysp, capability_name=case.capability.name,
            visit_label=VISIT_LABEL, decision_point=dp, temperature=0.0, seed=1000 + i,
        )
        ps.append(dec.p_metric)
    return statistics.mean(ps)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=6, help="agents per arm per cell")
    args = ap.parse_args()
    rows, _ = load_hillstrom_csv(CSV)
    personas = load_hillstrom_panel().personas
    cases = {e: build_hillstrom_case(rows, arm=e, metric_name="visit") for e in EMAILS}
    dps = {e: getattr(cases[e].hypothesis, "decision_point", None)
           or "the customer is looking at their inbox" for e in EMAILS}
    client = get_chat_client("claude-sonnet-4-6")
    print(f"panel={len(personas)} personas x {len(EMAILS)} emails, k={args.k} agents/arm; "
          f"RCT truth: every email RAISES visits (lift>0)\n")

    summary = {}
    for mode in ("roleplay", "forecaster"):
        lifts = []
        print(f"### mode={mode} ###")
        for persona in personas:
            for email in EMAILS:
                c = cases[email]
                pt = mean_p_visit(client, persona, c, "treatment", mode, dps[email], args.k)
                pc = mean_p_visit(client, persona, c, "control", mode, dps[email], args.k)
                lifts.append(pt - pc)
                print(f"  {persona.name} x {email:13s}: treat {pt:.3f} - ctrl {pc:.3f} = lift {pt-pc:+.3f}")
        mean = statistics.mean(lifts)
        pos = sum(1 for x in lifts if x > 0)
        dir_acc = pos / len(lifts)
        summary[mode] = {"mean_lift": mean, "direction_accuracy": dir_acc, "n_cells": len(lifts)}
        print(f"  => {mode}: mean visit lift {mean:+.3f} | direction accuracy {dir_acc:.2f} "
              f"({pos}/{len(lifts)} cells positive)\n")

    print("=" * 64)
    print("THROUGH-ENGINE RESULT (panel scale, production elicitor):")
    for mode, s in summary.items():
        print(f"  {mode:10s}: direction_accuracy {s['direction_accuracy']:.2f}  "
              f"mean_lift {s['mean_lift']:+.3f}")
    r, f = summary["roleplay"], summary["forecaster"]
    print(f"\n  Sign fix carried through the engine: "
          f"{'YES' if f['direction_accuracy'] > r['direction_accuracy'] else 'NO'} "
          f"(forecaster {f['direction_accuracy']:.2f} vs roleplay {r['direction_accuracy']:.2f}); "
          f"RCT direction is positive.")
    import json
    from pathlib import Path
    Path(__file__).resolve().parent.joinpath("through_engine_powered_result.json").write_text(
        json.dumps(summary, indent=2, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
