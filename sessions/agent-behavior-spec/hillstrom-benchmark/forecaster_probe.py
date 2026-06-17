"""Hillstrom forecaster probe (#342 / Benchmark 2): does expert-forecaster
elicitation fix the certified "advertising-as-harm" sign inversion?

The certified reader-roleplay run predicted promotional emails LOWER visits &
conversions (direction accuracy 0.0) when the real RCT shows they RAISE both.
The report diagnoses this as intrinsic to introspective reader-roleplay. The
Upworthy work showed expert-forecaster framing recovers signal where roleplay is
null. This tests the same lever on the named accuracy bug.

Ground truth: real per-segment uplifts computed from the Hillstrom RCT CSV
(`real_segment_uplifts.json`, 3 gender segments x 2 emails, all positive).
Predictor: expert-forecaster elicitation (Sonnet + Groq control). Scored on
direction accuracy (the sign-fix headline) + Spearman/Kendall rank (heterogeneity,
n=6 = underpowered, reported honestly).

    PYTHONPATH=backend <venv>/bin/python <thisfile>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client, model_is_available
from sidira_simulator.services.directional_gate import kendall_tau_b, _sign_dead
from sidira_simulator.services.statistics import spearman_rho

HERE = Path(__file__).resolve().parent
MODEL_IDS = {"sonnet": "claude-sonnet-4-6", "groq": "llama-3.3-70b-versatile"}
SEG_DESC = {
    "mens_buyer": "customers who purchased MEN'S merchandise (but not women's) in the past year",
    "womens_buyer": "customers who purchased WOMEN'S merchandise (but not men's) in the past year",
    "both_buyer": "customers who purchased BOTH men's and women's merchandise in the past year",
}
EMAIL_DESC = {"Mens E-Mail": "a promotional email featuring MEN'S merchandise",
              "Womens E-Mail": "a promotional email featuring WOMEN'S merchandise"}
_OBJ = re.compile(r'\{[^{}]*\}')


def _json(raw):
    for c in reversed(_OBJ.findall(raw)):
        try:
            o = json.loads(c)
            if isinstance(o, dict):
                return o
        except Exception:
            continue
    return None


def forecast(client, seg, email, seed):
    msgs = [
        {"role": "system", "content": "You are an expert in email-marketing causal effects. "
         "You predict how a promotional email campaign changes customer behavior versus sending "
         "no email, grounded in how real randomized campaigns actually move metrics."},
        {"role": "user", "content":
            f"Audience: {SEG_DESC[seg]}.\nCampaign: the retailer sends {EMAIL_DESC[email]} to this "
            "audience. A randomized holdout gets NO email.\nOver the next two weeks, predict the "
            "change versus the no-email holdout in:\n(1) site VISIT rate, in percentage points\n"
            "(2) purchase CONVERSION rate, in percentage points\n"
            'Respond ONLY with one JSON object: {"visit_pp": <float>, "conv_pp": <float>}'}]
    for attempt in range(3):
        try:
            raw = client.chat(msgs, max_tokens=300, temperature=0.0 if attempt else 0.3, seed=seed)
        except Exception:
            continue
        o = _json(raw)
        if o and "visit_pp" in o and "conv_pp" in o:
            try:
                return float(o["visit_pp"]), float(o["conv_pp"])
            except (TypeError, ValueError):
                continue
    return None


def score(pred, real, label):
    # direction accuracy: predicted sign vs real sign (real all +)
    dir_acc = sum(1 for p, r in zip(pred, real) if _sign_dead(p, 0) == _sign_dead(r, 0)) / len(pred)
    rho = spearman_rho(pred, real)
    tau = kendall_tau_b(pred, real)
    print(f"  {label:28s} dir_acc={dir_acc:.2f}  spearman={rho:+.3f}  kendall={tau:+.3f}  "
          f"pred_signs={''.join('+' if p>0 else '-' if p<0 else '0' for p in pred)}")
    return {"dir_acc": dir_acc, "spearman": rho, "kendall": tau,
            "pred": pred, "real": real}


def main() -> int:
    gt = json.loads((HERE / "real_segment_uplifts.json").read_text())
    cases = [(g["segment"], g["email"], g["visit_uplift"], g["conv_uplift"]) for g in gt]
    out = {"n_cases": len(cases), "baseline_reader_roleplay": {
        "visit": {"dir_acc": 0.0, "rank_rho": -0.29}, "conversion": {"dir_acc": 0.0, "rank_rho": -0.36}},
        "models": {}}
    print(f"cases={len(cases)} (3 segments x 2 emails); real signs all POSITIVE")
    print("baseline (certified reader-roleplay): visit dir_acc 0.0 rho -0.29 | conv dir_acc 0.0 rho -0.36\n")
    for mk in ("sonnet", "groq"):
        mid = MODEL_IDS[mk]
        if not model_is_available(mid):
            print(f"skip {mk}: unavailable"); continue
        client = get_chat_client(mid)
        pv, pc, real_v, real_c = [], [], [], []
        for i, (seg, email, ruv, ruc) in enumerate(cases):
            f = forecast(client, seg, email, seed=1000 + i)
            if f is None:
                print(f"  DROP {seg}/{email}"); continue
            pv.append(f[0]); pc.append(f[1]); real_v.append(ruv); real_c.append(ruc)
        print(f"### {mk} (expert-forecaster) ###")
        out["models"][mk] = {
            "visit": score(pv, real_v, "VISIT (expert-forecaster)"),
            "conversion": score(pc, real_c, "CONVERSION (expert-forecaster)"),
        }
        print()
    (HERE / "forecaster_probe_result.json").write_text(json.dumps(out, indent=2, default=float))
    print(f"wrote {HERE/'forecaster_probe_result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
