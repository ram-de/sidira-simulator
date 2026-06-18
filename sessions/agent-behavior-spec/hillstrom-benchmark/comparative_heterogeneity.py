"""Powered HETEROGENEITY run through the COMPARATIVE ENGINE pass (#342).

The e2e proved DIRECTION (comparative pass, +10pp) but the GMM personas gave
clustered deltas → no who-responds-more signal. This tests whether the production
comparative pass (`compose_comparative_metric_prompt` + `elicit_visit_delta`)
recovers the certified heterogeneity (standalone forecaster: rank-ρ +0.42) when
given SEGMENT-RICH personas. Strata = gender × recency × channel (the certified
38-cell set), each a descriptive Persona; real per-cell visit uplift from the RCT.
Primary endpoint: Spearman(predicted delta, real uplift) + permutation p.

    PYTHONPATH=backend <venv>/bin/python <thisfile> [--k 4]
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import forecaster_heterogeneity as FH  # build_cases, GENDER, REC, perm_p

from sidira_simulator.adapters.llm import get_chat_client
from sidira_simulator.schemas.persona import Persona
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.hillstrom_archive import load_hillstrom_csv
from sidira_simulator.services.hillstrom_adapter import build_hillstrom_case
from sidira_simulator.services.prompt_composer import compose_comparative_metric_prompt
from sidira_simulator.services.visit_elicitor import elicit_visit_delta
from sidira_simulator.services.directional_gate import kendall_tau_b, _sign_dead
from sidira_simulator.services.statistics import spearman_rho

CSV = "/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv"
CHAN = {"Phone": "were acquired by phone", "Web": "were acquired on the web",
        "Multichannel": "were acquired across both phone and web"}
EMAILS = ["Mens E-Mail", "Womens E-Mail"]


def persona_for(gender: str, recency: str, channel: str) -> Persona:
    desc = (f"Customers who {FH.GENDER[gender]}, who {FH.REC[recency]}, and who "
            f"{CHAN.get(channel, 'were acquired via ' + channel)}.")
    return Persona(id=f"{gender}|{recency}|{channel}",
                   name=f"{gender} / {recency} / {channel}", description=desc)


def engine_case(rows, email):
    c = build_hillstrom_case(rows, arm=email, metric_name="visit")
    data = c.hypothesis.model_dump()
    data.update({"metric_name": "visit",
                 "decision_point": "the customer is looking at their inbox"})
    return c.capability, Hypothesis.model_validate(data)


def cell_delta(client, persona, cap, hyp, k):
    ds = []
    for i in range(k):
        sysp = compose_comparative_metric_prompt(
            customer_id="hillstrom", persona=persona, capability=cap,
            hypothesis=hyp, sample_index=i,
        )
        try:
            ds.append(elicit_visit_delta(
                client, system_prompt=sysp, capability_name=cap.name,
                decision_point=hyp.decision_point or "", temperature=0.5, seed=4000 + i))
        except ValueError:
            continue
    return statistics.mean(ds) if ds else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cells = FH.build_cases(CSV)
    if args.smoke:
        cells = cells[:2]
    rows, _ = load_hillstrom_csv(CSV)
    caps = {e: engine_case(rows, e) for e in EMAILS}
    client = get_chat_client("claude-sonnet-4-6")
    print(f"COMPARATIVE-ENGINE heterogeneity | {len(cells)} cells (gender x recency x "
          f"channel x email), k={args.k} | descriptive segment personas")
    preds, reals, dropped = [], [], 0
    for n, c in enumerate(cells):
        cap, hyp = caps[c["email"]]
        d = cell_delta(client, persona_for(c["gender"], c["recency"], c["channel"]), cap, hyp, args.k)
        if d is None:
            dropped += 1
            continue
        preds.append(d); reals.append(c["real_visit"])
        if (n + 1) % 10 == 0:
            print(f"  ...{n+1}/{len(cells)}", flush=True)
    rho = spearman_rho(preds, reals)
    tau = kendall_tau_b(preds, reals)
    p = FH.perm_p(preds, reals, rho)
    dir_acc = sum(_sign_dead(pr, 0) == _sign_dead(rl, 0) for pr, rl in zip(preds, reals)) / len(preds)
    print(f"\n=== COMPARATIVE-ENGINE HETEROGENEITY (n={len(preds)}, dropped={dropped}) ===")
    print(f"  Spearman rho = {rho:+.3f}  (perm p = {p:.4f})   Kendall tau_b = {tau:+.3f}")
    print(f"  direction accuracy = {dir_acc:.3f}")
    print(f"  pre-registered bar (rho>0.30 AND p<0.05): "
          f"{'CERTIFIED' if (rho > 0.30 and p < 0.05) else 'NOT certified'}")
    print(f"  baselines: standalone forecaster ρ +0.42 (certified) | GMM-persona e2e: clustered/no heterogeneity")
    if not args.smoke:
        HERE.joinpath("comparative_heterogeneity_result.json").write_text(json.dumps(
            {"n": len(preds), "dropped": dropped, "spearman": rho, "kendall": tau,
             "perm_p": p, "direction_accuracy": dir_acc, "k": args.k}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
