"""Streamly H-001 v1.1 blinded higher-fidelity run (NOT accuracy validation).

STEP A3. Copy of streamly_plumbing_run.py, upgraded:
  - loads the v1.1 streamly_sample pack (v_2, with the centroid_full/feature_scale/
    sample_rows/posterior_mean quad) via PersonaPackLoader.load_latest;
  - wires a RENDERED treatment (proposed_figma = the Smart Resume hero ReverseFigma
    in smart_resume_proposed_figma.json) + a proposed_prd onto the Hypothesis, so
    the treatment renderer has a faithful standalone (blinded) view and the metric
    pass does NOT fall back to the UNBLINDED prompt.

Streamly is FICTIONAL → no real outcome. This is readiness + face-validity only.
Captures lift / lift_ci / confidence_score / treatment+control scores / weaknesses
+ per-agent records (agent_id → persona_name → arm) for the STEP B face-validity join.
"""
from __future__ import annotations
import argparse, asyncio, json
from pathlib import Path

from sidira_simulator.adapters.persona_loader import PersonaPackLoader
from sidira_simulator.adapters.feature_pack_loader import FeaturePackLoader
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.schemas.feature_pack import ReverseFigma
from sidira_simulator.services.simulation_runner import SimulationRunner
from sidira_simulator.adapters.llm import get_chat_client

HERE = Path(__file__).resolve().parent
CUST, VER = "streamly_sample", "2026-W21"

PROSE = ("Replace the Continue Watching rail with a single Smart Resume hero: the top of the "
         "home screen becomes one large card with the single most likely title to resume "
         "(next episode for series viewers; in-progress movie otherwise) and one big Resume "
         "button, with a small 'More options' expander that reveals the legacy multi-tile row. "
         "The horizontal Continue Watching rail is removed from the top of home when a Smart "
         "Resume target exists. Cold-start users still see the editorial hero.")

PROPOSED_PRD = (
    "Smart Resume hero (H-001). Collapse the editorial hero + Continue Watching rail at the top "
    "of home into ONE large full-bleed Smart Resume card showing the single most-likely title to "
    "resume — next episode for series viewers, in-progress movie otherwise — with one big primary "
    "Resume button and a small 'More options' expander that reveals the legacy multi-tile Continue "
    "Watching row inline. The horizontal Continue Watching rail is REMOVED from the top of home "
    "when a Smart Resume target exists; the full list stays reachable via 'More options' or a "
    "'My Stuff' tab. Cold-start users (no in-progress titles) still see the existing editorial hero "
    "verbatim — no regression for new users."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=20)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--treatment-fraction", type=float, default=0.5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--pack-version", default=None,
                    help="Load a specific pack version (e.g. v_1) instead of latest.")
    ap.add_argument("--out-suffix", default="",
                    help="Suffix for output filename: streamly_v11_result{suffix}.json")
    args = ap.parse_args()

    loader = PersonaPackLoader()
    pack = (loader.load_at_version(CUST, args.pack_version)
            if args.pack_version else loader.load_latest(CUST))
    cap = FeaturePackLoader().load_capability(CUST, VER, "continue_watching")

    figma_doc = json.loads((HERE / "smart_resume_proposed_figma.json").read_text())
    figma_doc.pop("_comment", None)
    proposed_figma = ReverseFigma.model_validate(figma_doc)

    hyp = Hypothesis.model_validate({
        "capability_name": "continue_watching",
        "prose": PROSE,
        "proposed_prd": PROPOSED_PRD,
        "proposed_figma": proposed_figma.model_dump(),
        "metric_name": "conversion",
        "conversion_action": "start playing a title from the home screen",
        "conversion_action_label": "Resume or play a title",
        "decision_point": "you've just opened the Streamly home screen",
    })

    runner = SimulationRunner(chat_client=get_chat_client(args.model))
    sim = asyncio.run(runner.run(
        customer_id=CUST, persona_pack=pack, capability=cap, feature_pack_version=VER,
        hypothesis=hyp, population_size=args.population, run_seed=args.seed,
        treatment_fraction=args.treatment_fraction))
    res = sim.result

    recs = getattr(runner, "_last_run_agent_records", [])
    print("=== ENGINE RAN OK (v1.1 + rendered treatment) ===")
    print("pack version:", pack.version, "schema:", pack.schema_version, "personas:", len(pack.personas))
    print("lift:", getattr(res, "lift", None), "| lift_ci:", getattr(res, "lift_ci", None))
    print("confidence_score:", getattr(res, "confidence_score", None))
    print("treatment_score:", getattr(res, "treatment_score", None),
          "| control_score:", getattr(res, "control_score", None))
    print(f"agents materialized: {len(recs)}  arms: {sorted(set(r.arm for r in recs))}")

    # agent_id -> (persona_id, persona_name, arm) join table for STEP B
    rec_map = {r.agent_id: {"persona_id": r.persona_id, "persona_name": r.persona_name, "arm": r.arm}
               for r in recs}

    out = {
        "pack_version": pack.version,
        "pack_schema_version": pack.schema_version,
        "population": args.population,
        "treatment_fraction": args.treatment_fraction,
        "seed": args.seed,
        "model": args.model,
        "lift": getattr(res, "lift", None),
        "lift_ci": getattr(res, "lift_ci", None),
        "confidence_score": getattr(res, "confidence_score", None),
        "confidence_score_ci": getattr(res, "confidence_score_ci", None),
        "treatment_score": getattr(res, "treatment_score", None),
        "control_score": getattr(res, "control_score", None),
        "metric_name": getattr(res, "metric_name", None),
        "metric_lift": getattr(res, "metric_lift", None),
        "metric_lift_ci": getattr(res, "metric_lift_ci", None),
        "weaknesses": [w.model_dump() for w in getattr(res, "weaknesses", [])],
        "agent_records": rec_map,
        "per_agent_analyses": [a.model_dump() for a in getattr(res, "per_agent_analyses", [])],
        "result_full": json.loads(res.model_dump_json()),
    }
    fname = f"streamly_v11_result{args.out_suffix}.json"
    (HERE / fname).write_text(json.dumps(out, indent=2, default=str))
    print(f"wrote {fname}")


if __name__ == "__main__":
    main()
