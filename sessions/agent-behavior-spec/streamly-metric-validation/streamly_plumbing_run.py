"""Streamly H-001 plumbing + face-validity run (NOT accuracy validation).

Runs the REAL engine (SimulationRunner) on the streamly_sample persona pack +
the crawled `continue_watching` capability + the H-001 Smart-Resume hypothesis,
bypassing the DB repos. Streamly is fictional → there is NO real outcome; this
confirms the full customer-pack path runs end-to-end (readiness) and lets us
compare per-persona reactions to the PM's AUTHORED expectations (face-validity).
"""
from __future__ import annotations
import argparse, asyncio, json

from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.simulation_runner import SimulationRunner
from sidira_simulator.adapters.llm import get_chat_client

CUST, VER = "streamly_sample", "2026-W21"
PROSE = ("Replace the Continue Watching rail with a single Smart Resume hero: the top of the "
         "home screen becomes one large card with the single most likely title to resume "
         "(next episode for series viewers; in-progress movie otherwise) and one big Resume "
         "button, with a small 'More options' expander that reveals the legacy multi-tile row. "
         "The horizontal Continue Watching rail is removed from the top of home when a Smart "
         "Resume target exists. Cold-start users still see the editorial hero.")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=12)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    args = ap.parse_args()
    pack = PersonaPackLoader().load_latest(CUST)
    cap = FeaturePackLoader().load_capability(CUST, VER, "continue_watching")
    hyp = Hypothesis.model_validate({
        "capability_name": "continue_watching",
        "prose": PROSE,
        "metric_name": "conversion",
        "conversion_action": "start playing a title from the home screen",
        "conversion_action_label": "Resume or play a title",
        "decision_point": "you've just opened the Streamly home screen",
    })
    runner = SimulationRunner(chat_client=get_chat_client(args.model))
    sim = asyncio.run(runner.run(
        customer_id=CUST, persona_pack=pack, capability=cap, feature_pack_version=VER,
        hypothesis=hyp, population_size=args.population, run_seed=42, treatment_fraction=0.5))
    res = sim.result
    print("=== ENGINE RAN OK ===")
    print("lift:", getattr(res, "lift", None), "| metric:", getattr(res, "metric_name", None))
    recs = getattr(runner, "_last_run_agent_records", [])
    print(f"agents materialized: {len(recs)}  (arms: {sorted(set(r.arm for r in recs))})")
    out = {"lift": getattr(res, "lift", None), "metric_name": getattr(res, "metric_name", None),
           "result": json.loads(res.model_dump_json()) if hasattr(res, "model_dump_json") else str(res)}
    open("/Users/ram/Projects/sidira-simulator/.claude/worktrees/benchmark-gate-validation/sessions/agent-behavior-spec/streamly-metric-validation/streamly_plumbing_result.json","w").write(json.dumps(out, indent=2, default=str))
    print("wrote streamly_plumbing_result.json")

if __name__ == "__main__":
    main()
