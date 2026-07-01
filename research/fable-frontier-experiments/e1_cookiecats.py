"""E1 Leg B — Cookie Cats collapsed to the tier-1 schema (PREREG_E1).

Collapse the real 90k-row A/B table to tier-1 aggregates per arm
(segment = engagement bin over sum_gamerounds; outcome rates per bin), then:
  CALC: recover the aggregate direction for gate_40 vs gate_30 from the
        collapsed table alone (bin-share-weighted rates; no row access).
  LLM-TABLES (informational): claude-opus-4-8 given the same collapsed table.
Known sealed truth (public result, PREREG_REALDATA campaign): gate_40 LOSES on
retention_7 and retention_1. Scored in e1_score.py, not here.
Writes e1_cookiecats_tables.json + e1_cookiecats_predictions.json.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
BINS = [0, 1, 11, 51, 201, 10**9]
LABELS = ["0", "1-10", "11-50", "51-200", "200+"]

for line in (HERE / "../../backend/.env").resolve().read_text().splitlines():
    if line.startswith("ANTHROPIC_API_KEY="):
        os.environ.setdefault("ANTHROPIC_API_KEY", line.split("=", 1)[1].strip())


def collapse() -> dict:
    df = pd.read_csv(HERE / ".data" / "cookie_cats.csv")
    df["bin"] = pd.cut(df["sum_gamerounds"], bins=BINS, labels=LABELS,
                       right=False, include_lowest=True)
    arms = {}
    for arm, g in df.groupby("version"):
        rows = []
        for b, gb in g.groupby("bin", observed=True):
            rows.append({"gamerounds_bin": str(b), "users": int(len(gb)),
                         "retention_7_rate": round(float(gb["retention_7"].mean()), 6),
                         "retention_1_rate": round(float(gb["retention_1"].mean()), 6)})
        arms[arm] = {"total_users": int(len(g)), "bins": rows}
    return {"schema": "tier1.segment_mediator_outcome.v1",
            "description": "Cookie Cats A/B collapsed to engagement-bin cross-tabs "
                           "per arm; no row-level data.",
            "arms": arms}


def calc_direction(tables: dict, metric: str) -> dict:
    rates = {}
    for arm, spec in tables["arms"].items():
        num = sum(b["users"] * b[f"{metric}_rate"] for b in spec["bins"])
        rates[arm] = num / spec["total_users"]
    delta = rates["gate_40"] - rates["gate_30"]
    return {"direction": "up" if delta > 0 else "down",
            "gate_30_rate": round(rates["gate_30"], 6),
            "gate_40_rate": round(rates["gate_40"], 6),
            "delta_pp": round(delta * 100, 4)}


def llm_tables(tables: dict) -> dict:
    from anthropic import Anthropic
    client = Anthropic()
    system = (
        "You are a careful analyst. Given a tier-1 aggregate cross-tab from a "
        "mobile-game A/B test, decide the DIRECTION of each stated metric for "
        "the treatment (gate_40: first progress gate moved from level 30 to "
        "level 40) versus control (gate_30). Use the numbers. Reply ONLY strict "
        'JSON: {"retention_7": "up"|"down"|"abstain", '
        '"retention_1": "up"|"down"|"abstain", "reason": "<=25 words"}.'
    )
    prose = ("Hypothesis: moving the first forced progress gate from level 30 "
             "to level 40 lets players build more momentum before the first "
             "interruption, which should improve retention.")
    resp = client.messages.create(  # temperature omitted: rejected by opus-4-8
        model="claude-opus-4-8", max_tokens=1500, system=system,
        messages=[{"role": "user",
                   "content": f"{prose}\n\nTIER-1 TABLE:\n{json.dumps(tables)}"}])
    m = re.search(r"\{.*\}", resp.content[0].text, re.S)
    return json.loads(m.group(0)) if m else {"error": resp.content[0].text}


def main() -> None:
    tables = collapse()
    (HERE / "e1_cookiecats_tables.json").write_text(json.dumps(tables, indent=1))
    preds = {"CALC": {m: calc_direction(tables, m)
                      for m in ("retention_7", "retention_1")},
             "LLM_TABLES": llm_tables(tables)}
    (HERE / "e1_cookiecats_predictions.json").write_text(json.dumps(preds, indent=1))
    print(json.dumps(preds, indent=1))


if __name__ == "__main__":
    main()
