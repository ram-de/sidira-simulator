"""Through-ENGINE smoke run (#342 path A, increment 2): does the SIDIRA_ELICITATION_MODE
flag flip the visit-lift sign in the REAL production elicitor pipeline?

NOT the full certified powered harness (that runs prod-box scale). This drives the
actual production seam — `prompt_composer.compose_metric_prompt` +
`visit_elicitor.elicit_visit_decision` — on a real Hillstrom email case, paired
control(no-email) vs treatment(email), under roleplay vs forecaster, with a real
Sonnet client. It confirms the wiring produces the predicted direction flip
(roleplay -> ad-aversion / negative-ish; forecaster -> positive, matching the RCT
where the email RAISES visits) end-to-end through the engine.

    PYTHONPATH=backend <venv>/bin/python <thisfile>
"""
from __future__ import annotations

import sys
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client
from sidira_simulator.services.hillstrom_archive import load_hillstrom_csv
from sidira_simulator.services.hillstrom_adapter import build_hillstrom_case
from sidira_simulator.adapters.hillstrom_panel_loader import load_hillstrom_panel
from sidira_simulator.services.prompt_composer import compose_metric_prompt
from sidira_simulator.services.visit_elicitor import elicit_visit_decision, VISIT_LABEL

CSV = "/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv"
CUSTOMER = "hillstrom"


def p_visit(client, persona, case, arm, mode, decision_point) -> float:
    sysp, _ = compose_metric_prompt(
        customer_id=CUSTOMER, persona=persona, capability=case.capability,
        hypothesis=case.hypothesis, arm=arm, elicitation_mode=mode,
    )
    dec = elicit_visit_decision(
        client, system_prompt=sysp, capability_name=case.capability.name,
        visit_label=VISIT_LABEL, decision_point=decision_point, temperature=0.0, seed=7,
    )
    return dec.p_metric


def main() -> int:
    rows, _summary = load_hillstrom_csv(CSV)
    case = build_hillstrom_case(rows, arm="Mens E-Mail", metric_name="visit")
    dp = getattr(case.hypothesis, "decision_point", None) or "the customer is looking at their inbox"
    personas = load_hillstrom_panel().personas[:3]
    client = get_chat_client("claude-sonnet-4-6")
    print(f"case={case.case_id}  capability={case.capability.name!r}  decision_point={dp!r}")
    print(f"real ground truth: Mens E-Mail RAISES visits (positive lift)\n")
    for mode in ("roleplay", "forecaster"):
        lifts = []
        for persona in personas:
            pt = p_visit(client, persona, case, "treatment", mode, dp)
            pc = p_visit(client, persona, case, "control", mode, dp)
            lifts.append(pt - pc)
            print(f"  [{mode:10s}] {persona.name}: p_visit treat {pt:.2f} - control {pc:.2f} = lift {pt-pc:+.3f}")
        mean = sum(lifts) / len(lifts)
        pos = sum(1 for x in lifts if x > 0)
        print(f"  => {mode}: mean visit lift {mean:+.3f}  ({pos}/{len(lifts)} personas positive)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
