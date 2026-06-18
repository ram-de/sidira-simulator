"""End-to-end flag-ON validation (#342): drive the REAL SimulationRunner.run with
SIDIRA_METRIC_COMPARATIVE=1 on the Hillstrom Mens-email visit case (A/B mode, real
Sonnet), then confirm the comparative path fired through the FULL runner:
  (a) treatment agent-records carry metric_comparative_delta (the run loop elicited it);
  (b) the PRODUCTION aggregate_metric_lift on those records delegates to the
      comparative aggregator and yields a lift (RCT truth: the email RAISES visits).

    PYTHONPATH=backend <venv>/bin/python <thisfile>
"""
from __future__ import annotations

import asyncio
import os
import tempfile

os.environ["SIDIRA_ELICITATION_MODE"] = "forecaster"
os.environ["SIDIRA_METRIC_COMPARATIVE"] = "1"

from sidira_simulator.adapters.r2 import LocalArtifactStore  # noqa: E402
from sidira_simulator.adapters.hillstrom_panel_loader import load_hillstrom_panel  # noqa: E402
from sidira_simulator.adapters.llm import get_chat_client  # noqa: E402
from sidira_simulator.services.hillstrom_archive import load_hillstrom_csv  # noqa: E402
from sidira_simulator.services.hillstrom_adapter import build_hillstrom_case  # noqa: E402
from sidira_simulator.services.simulation_runner import SimulationRunner  # noqa: E402
from sidira_simulator.services import scoring  # noqa: E402
from sidira_simulator.schemas.simulation import Hypothesis  # noqa: E402

CSV = "/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv"


def _to_reaction(r) -> scoring.AgentReaction:
    return scoring.AgentReaction(
        agent_id=r.agent_id, persona_id=r.persona_id, persona_name=r.persona_name,
        reaction_text=getattr(r, "reaction_text", ""), sample_index=r.sample_index,
        arm=r.arm, metric_p=r.metric_p,
        metric_comparative_delta=r.metric_comparative_delta,
    )


async def main() -> int:
    store = LocalArtifactStore(tempfile.mkdtemp(prefix="e2e_comp_"))
    client = get_chat_client("claude-sonnet-4-6")
    runner = SimulationRunner(store=store, chat_client=client, max_concurrent_agents=4)
    panel = load_hillstrom_panel()
    rows, _ = load_hillstrom_csv(CSV)
    case = build_hillstrom_case(rows, arm="Mens E-Mail", metric_name="visit")
    # The case's hypothesis leaves metric_name/decision_point None (that arg sets the
    # GROUND-TRUTH metric, not the engine task). Build the engine hypothesis the way
    # the benchmark harness does — set the visit metric + arm-neutral decision_point,
    # re-validated — so the runner actually elicits the metric.
    data = case.hypothesis.model_dump()
    data.update({"metric_name": "visit",
                 "decision_point": "the customer is looking at their inbox"})
    engine_hyp = Hypothesis.model_validate(data)
    print(f"flag SIDIRA_METRIC_COMPARATIVE=1, elicitation=forecaster | "
          f"metric={engine_hyp.metric_name} | A/B pop=8")
    sim = await runner.run(
        customer_id="hillstrom", persona_pack=panel, capability=case.capability,
        feature_pack_version="hillstrom-rct-v1", hypothesis=engine_hyp,
        population_size=8, treatment_fraction=0.5, model_id="claude-sonnet-4-6",
        run_seed=42,
    )
    recs = runner._last_run_agent_records
    treat = [r for r in recs if r.arm == "treatment"]
    ctrl = [r for r in recs if r.arm == "control"]
    deltas = [r.metric_comparative_delta for r in treat if r.metric_comparative_delta is not None]
    print(f"\nagents: {len(treat)} treatment / {len(ctrl)} control")
    print(f"(a) treatment records with comparative_delta SET: {len(deltas)}/{len(treat)}")
    print(f"    deltas: {[round(d, 3) for d in deltas]}")

    tr = [_to_reaction(r) for r in treat]
    cr = [_to_reaction(r) for r in ctrl]
    lift = scoring.aggregate_metric_lift(tr, cr, metric_name="visit", run_seed=42)
    used_comparative = any(r.metric_comparative_delta is not None for r in tr)
    print(f"\n(b) PRODUCTION aggregate_metric_lift  ->  lift_pp={lift.lift_pp}  "
          f"ci={lift.lift_ci_pp}  paired_n={lift.paired_n}")
    print(f"    delegated to comparative aggregator: {used_comparative}")
    print(f"\nRCT truth: Mens E-Mail RAISES visits (positive lift). "
          f"End-to-end comparative wiring fired: {used_comparative and len(deltas) > 0}")
    print(f"sim id: {sim.id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
