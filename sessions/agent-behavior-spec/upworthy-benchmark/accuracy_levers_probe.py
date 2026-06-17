"""Accuracy-levers probe (#342 follow-on): does a different ELICITATION change
the Upworthy rank result? All prior runs used reader-roleplay ("would YOU
click?"). This tests expert-forecaster framings on the IDENTICAL fresh 150-case
slice, scored through the same G0-G11 gate.

Avenues:
  comparative  — forced choice + brief reasoning: which headline gets higher CTR,
                 with a confidence -> signal = P(treatment wins) - 0.5
  popshare     — "of 100 feed users, how many click A vs B?" -> signal = clicks_T - clicks_C

Single call per case (these are direct CTR forecasters, not persona panels).
Blinded + order-randomized. Pre-register before the full run; resumable.

Usage:
    PYTHONPATH=backend <venv>/bin/python <thisfile> --modes comparative,popshare \
        --models sonnet,groq [--cases N] [--smoke]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client, model_is_available
from sidira_simulator.services.directional_gate import ExperimentRecord, GateConfig, certify

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import model_comparison_probe as MCP  # reuse load_fresh_cases / original_test_ids

MODEL_IDS = MCP.MODEL_IDS
_OBJ = re.compile(r'\{[^{}]*\}')


def _extract_json(raw: str) -> dict | None:
    for cand in reversed(_OBJ.findall(raw)):
        try:
            o = json.loads(cand)
            if isinstance(o, dict):
                return o
        except Exception:
            continue
    return None


def _robust(client, msgs, seed, want) -> dict | None:
    for attempt in range(3):
        temp = 0.4 if attempt == 0 else 0.0
        try:
            raw = client.chat(msgs, max_tokens=400, temperature=temp, seed=seed)
        except Exception:
            continue
        o = _extract_json(raw)
        if o is not None and all(k in o for k in want):
            return o
    return None


def elicit_comparative(client, ctl: str, trt: str, rng: random.Random, seed):
    treat_is_a = rng.random() < 0.5
    a, b = (trt, ctl) if treat_is_a else (ctl, trt)
    msgs = [
        {"role": "system", "content": "You are an expert at predicting which social-media "
         "headline earns a higher click-through rate in a feed."},
        {"role": "user", "content":
            f"Two headlines for the SAME story:\nA: {a!r}\nB: {b!r}\n\n"
            "Which gets the higher click-through rate? Weigh curiosity gap, specificity, "
            "emotional pull, novelty, and clarity. Then answer ONLY with one JSON object: "
            '{"winner": "A" or "B", "p_winner": <number 0.5-1.0>}'}]
    o = _robust(client, msgs, seed, ("winner", "p_winner"))
    if o is None:
        return None
    try:
        p = float(o["p_winner"])
    except (TypeError, ValueError):
        return None
    p = max(0.5, min(1.0, p))
    winner_is_a = str(o["winner"]).strip().upper().startswith("A")
    p_treat = p if (winner_is_a == treat_is_a) else (1.0 - p)
    return p_treat - 0.5  # [-0.5, 0.5]


def elicit_popshare(client, ctl: str, trt: str, rng: random.Random, seed):
    treat_is_a = rng.random() < 0.5
    a, b = (trt, ctl) if treat_is_a else (ctl, trt)
    msgs = [
        {"role": "system", "content": "You estimate click-through behavior for social-media "
         "headlines based on how typical feed audiences actually behave."},
        {"role": "user", "content":
            f"Two headlines for the SAME story:\nA: {a!r}\nB: {b!r}\n\n"
            "Of 100 typical people who see this story card in their feed, how many click A, "
            'and how many click B? Answer ONLY with one JSON object: {"a": <int 0-100>, "b": <int 0-100>}'}]
    o = _robust(client, msgs, seed, ("a", "b"))
    if o is None:
        return None
    try:
        sa, sb = int(o["a"]), int(o["b"])
    except (TypeError, ValueError):
        return None
    s_treat, s_ctrl = (sa, sb) if treat_is_a else (sb, sa)
    return (s_treat - s_ctrl) / 100.0


ELICITORS = {"comparative": elicit_comparative, "popshare": elicit_popshare}


def run(mode: str, model_key: str, cases, ckpt: Path) -> dict:
    model_id = MODEL_IDS[model_key]
    if not model_is_available(model_id):
        raise SystemExit(f"{model_id} unavailable")
    client = get_chat_client(model_id)
    fn = ELICITORS[mode]
    state = json.loads(ckpt.read_text()) if ckpt.exists() else {"sig": {}, "dropped": {}}
    state.setdefault("dropped", {})
    t0 = time.time()
    for n, c in enumerate(cases):
        cid = c["case_id"]
        if cid in state["sig"]:
            continue
        rng = random.Random(int(hashlib.sha256(f"{mode}:{cid}".encode()).hexdigest(), 16) % (2**31))
        seed = int(hashlib.sha256(f"{mode}:{cid}:s".encode()).hexdigest(), 16) % (2**31)
        v = fn(client, c["control_hl"], c["treatment_hl"], rng, seed)
        if v is None:
            state["dropped"][cid] = "unparseable after retries"
        else:
            state["sig"][cid] = v
        ckpt.write_text(json.dumps(state))
        if (n + 1) % 25 == 0 or n + 1 == len(cases):
            print(f"  [{mode}/{model_key}] {n+1}/{len(cases)} ({time.time()-t0:.0f}s, "
                  f"{len(state['dropped'])} dropped)", flush=True)
    return state


def score(cases, signals, label, seed):
    recs = [ExperimentRecord(c["case_id"], c["observed_lift"], signals[c["case_id"]])
            for c in cases if c["case_id"] in signals]
    nd = len(cases) - len(recs)
    cfg = GateConfig(delta=0.0, budget=max(1, len(recs) // 4), bootstrap_trials=2000,
                     seed=seed, conf=0.90)
    res = certify(recs, cfg)
    m = res.metrics
    print(f"\n=== {label} === (n={len(recs)}, dropped={nd})")
    print(f"  SMR {m['balanced_smr']:.3f} (LB {m['smr_wilson_lo']:.3f}) | "
          f"Spearman {m['spearman_rho']:+.3f} | Kendall tau_b {m['kendall_tau_b']:+.3f} "
          f"(LB {m['kendall_tau_b_lo']:+.3f}) | MCC {m['mcc']:+.3f} (LB {m['mcc_lo']:+.3f}) | "
          f"Brier-skill {m['brier_skill']:+.3f} | tail {m['tail_winner_recall']:.2f}")
    print(f"  VERDICT: {res.verdict}")
    return {"verdict": res.verdict, "metrics": m, "gates": res.gates,
            "n_scored": len(recs), "n_dropped": nd}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--modes", default="comparative,popshare")
    ap.add_argument("--models", default="sonnet,groq")
    ap.add_argument("--cases", type=int, default=150)
    ap.add_argument("--confirm", action="store_true",
                    help="use a SECOND disjoint slice (excludes the first 150 + original 60)")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    orig = MCP.original_test_ids()
    if args.confirm:
        first = MCP.load_fresh_cases(150, orig)
        first_tids = {c["case_id"].split(":")[0] for c in first}
        cases = MCP.load_fresh_cases(args.cases, orig | first_tids)
    else:
        cases = MCP.load_fresh_cases(args.cases, orig)
    if args.smoke:
        cases = cases[:3]
    csh = hashlib.sha256(json.dumps(sorted(c["case_id"] for c in cases), sort_keys=True).encode()).hexdigest()
    print(f"cases={len(cases)} case_set_hash={csh[:16]} modes={args.modes} models={args.models}")

    out = {"case_set_hash": csh, "n_cases": len(cases), "results": {}}
    for mode in args.modes.split(","):
        for mk in args.models.split(","):
            tag = f"{mode}_{mk}{'_confirm' if args.confirm else ''}{'_smoke' if args.smoke else ''}"
            ckpt = HERE / f"levers_ckpt_{tag}.json"
            print(f"\n### {mode} / {mk} ###")
            st = run(mode.strip(), mk.strip(), cases, ckpt)
            out["results"][f"{mode}/{mk}"] = score(cases, st["sig"], f"{mode} / {mk}", args.seed)
    out_path = HERE / ("accuracy_levers_smoke.json" if args.smoke else
                       ("accuracy_levers_confirm_result.json" if args.confirm
                        else "accuracy_levers_result.json"))
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
