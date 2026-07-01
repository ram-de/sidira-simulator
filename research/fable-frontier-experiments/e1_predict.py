"""E1 predictors — CALC (translator -> deterministic arithmetic) and LLM-TABLES.

BLINDING: reads ONLY e1_cases.json prose + tier1_tables (id/family/flip metadata
stripped before any predictor sees a case). Never opens e1_answers.json.
Writes e1_predictions.json.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MODEL = "claude-opus-4-8"

for line in (HERE / "../../backend/.env").resolve().read_text().splitlines():
    if line.startswith("ANTHROPIC_API_KEY="):
        os.environ.setdefault("ANTHROPIC_API_KEY", line.split("=", 1)[1].strip())

from anthropic import Anthropic  # noqa: E402

client = Anthropic()


def chat_json(system: str, user: str) -> dict:
    # NOTE deviation from prereg: `temperature` is deprecated/rejected by
    # claude-opus-4-8 (400 error) — omitted; model default used instead of 0.
    resp = client.messages.create(
        model=MODEL, max_tokens=500,
        system=system, messages=[{"role": "user", "content": user}])
    text = resp.content[0].text
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {"error": text}


# ----------------------------------------------------------------- translator
TRANSLATOR_SYSTEM = (
    "You are a mechanism translator. You NEVER predict outcomes or signs. "
    "Given a product-change hypothesis and a tier-1 aggregate table, classify "
    "the composition mechanism and bind the table fields the arithmetic needs. "
    'Reply with ONLY strict JSON: {"family": "mix_shift" | "gross_vs_net" | '
    '"trade_down_cannibalization" | "other", "note": "<=15 words"}. '
    "mix_shift = traffic/mix moves between segments with different rates; "
    "gross_vs_net = a per-unit take moves against volume; "
    "trade_down_cannibalization = a new cheaper option draws from both "
    "non-buyers and an existing premium option."
)


def translate(prose: str, tables: dict) -> str:
    out = chat_json(TRANSLATOR_SYSTEM,
                    f"HYPOTHESIS: {prose}\n\nTIER-1 TABLE:\n{json.dumps(tables)}")
    return out.get("family", "other")


# ----------------------------------------------------------------- calculator
def calc_mix_shift(t: dict, scale: float) -> float:
    a, b = t["segments"][0], t["segments"][1]
    p = t["pilot_observed_shift"]["share_moved"] * scale
    base = a["users"] * a["baseline_conv_rate"] + b["users"] * b["baseline_conv_rate"]
    moved = a["users"] * p
    new = ((a["users"] - moved) * a["pilot_conv_rate"]
           + (b["users"] + moved) * b["pilot_conv_rate"])
    return new - base


def calc_gross_vs_net(t: dict, scale: float) -> float:
    s = t["segments"][0]
    shift = t["pilot_observed_shift"]
    unit_ratio = 1.0 + (shift["unit_ratio"] - 1.0) * scale
    take_ratio = 1.0 + (shift["take_ratio"] - 1.0) * scale
    base = s["baseline_units"] * s["baseline_take_per_unit"]
    new = s["baseline_units"] * unit_ratio * s["baseline_take_per_unit"] * take_ratio
    return new - base


def calc_trade_down(t: dict, scale: float) -> float:
    free = next(s for s in t["segments"] if s["price"] == 0.0)
    prem = next(s for s in t["segments"] if s["price"] > 0.0)
    low = t["new_option"]["price"]
    shift = t["pilot_observed_shift"]
    alpha = shift["share_of_free_users_adopting_lite"] * scale
    beta = shift["share_of_premium_switching_to_lite"] * scale
    return free["users"] * alpha * low - prem["users"] * beta * (prem["price"] - low)


CALCS = {"mix_shift": calc_mix_shift, "gross_vs_net": calc_gross_vs_net,
         "trade_down_cannibalization": calc_trade_down}


def calc_predict(family: str, tables: dict) -> dict:
    fn = CALCS.get(family)
    if fn is None:
        return {"direction": "abstain", "reason": f"unmapped family {family}"}
    try:
        center = fn(tables, 1.0)
        # prereg stability band: sign stable to +/-20% perturbation of shift inputs
        signs = {(fn(tables, s) > 0) for s in (0.8, 1.0, 1.2)}
        if len(signs) > 1:
            return {"direction": "abstain",
                    "reason": "sign unstable within +/-20% shift-share band",
                    "delta_center": center}
        return {"direction": "up" if center > 0 else "down", "delta_center": center}
    except (KeyError, StopIteration, TypeError) as e:
        return {"direction": "abstain", "reason": f"missing table fields: {e}"}


# ---------------------------------------------------------------- llm-tables
LLM_SYSTEM = (
    "You are a careful analyst. Given a product-change hypothesis and the "
    "tier-1 aggregate table from its pilot, decide the DIRECTION of the stated "
    "metric. Use the numbers in the table; do not rely on narrative tone. "
    'Reply with ONLY strict JSON: {"direction": "up" | "down" | "abstain", '
    '"reason": "<=25 words"}. Abstain only if the table truly cannot decide.'
)


def llm_predict(prose: str, tables: dict) -> dict:
    out = chat_json(LLM_SYSTEM,
                    f"HYPOTHESIS: {prose}\n\nTIER-1 TABLE:\n{json.dumps(tables)}")
    d = out.get("direction", "abstain")
    return {"direction": d if d in ("up", "down", "abstain") else "abstain",
            "reason": out.get("reason", "")}


def main() -> None:
    raw = json.loads((HERE / "e1_cases.json").read_text())
    preds = []
    for case in raw:
        blind = {"prose": case["prose"], "tier1_tables": case["tier1_tables"]}
        family = translate(blind["prose"], blind["tier1_tables"])
        calc = calc_predict(family, blind["tier1_tables"])
        llm = llm_predict(blind["prose"], blind["tier1_tables"])
        preds.append({"id": case["id"], "translator_family": family,
                      "CALC": calc, "LLM_TABLES": llm})
        print(f"{case['id']}: family={family} calc={calc['direction']} "
              f"llm={llm['direction']}", flush=True)
    (HERE / "e1_predictions.json").write_text(json.dumps(
        {"model": MODEL, "predictions": preds}, indent=1))
    print(f"wrote {len(preds)} predictions")


if __name__ == "__main__":
    sys.exit(main())
