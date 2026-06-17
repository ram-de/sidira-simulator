"""Model-comparison probe (#342): does a stronger model break the Upworthy
rank-ceiling that Groq llama-3.3-70b hit?

A LIGHT, blinded, order-randomized clickability elicitation on the IDENTICAL 60
cases as the committed Groq confirming run, across model tiers, scored through
the G0-G11 directional gate. This is a controlled *light-elicitation* arm — NOT
the heavy 200-agent persona panel of the prod run — so it isolates the model
effect cheaply (~$1 on Sonnet) before anyone spends $275 on a heavy Sonnet pass.

Two arms per model:
  - panel       : k lightweight reader personas vote -> heterogeneity-bearing signal
  - no_persona  : a single neutral rating -> the mandatory baseline (gate G11)

Discipline (#342): pre-register the config hash + predicted rho BEFORE the full
run; run ONCE; checkpoint per call so it is resumable. Runs LOCALLY (the prod-box
cautions in #342 do not apply here).

Usage:
    PYTHONPATH=backend <venv>/bin/python <thisfile> --models groq,sonnet --k 8
    ... --cases 3 --smoke        # quick pipeline check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path

from pydantic import BaseModel

from sidira_simulator.adapters.llm import get_chat_client, model_is_available
from sidira_simulator.services.upworthy_archive import load_upworthy_archive
from sidira_simulator.services.benchmark_adapter import upworthy_test_to_cases
from sidira_simulator.services.directional_gate import (
    ExperimentRecord, GateConfig, certify,
)

HERE = Path(__file__).resolve().parent
ARCHIVE = Path("/Users/ram/Projects/sidira-simulator/local-artifacts/upw_bench/archive.csv")

MODEL_IDS = {"groq": "llama-3.3-70b-versatile", "sonnet": "claude-sonnet-4-6",
             "haiku": "claude-haiku-4-5"}

# Lightweight, deliberately diverse reader personas — heterogeneity scaffolding,
# not claims about real Upworthy demographics (the panel is the variance source).
PERSONAS = [
    "a 24-year-old who scrolls social feeds on a phone during commutes",
    "a 45-year-old parent who shares feel-good and outrage stories",
    "a 33-year-old skeptic who distrusts clickbait and rarely clicks",
    "a 19-year-old college student into memes and pop culture",
    "a 58-year-old who reads news and human-interest pieces",
    "a 29-year-old activist drawn to social-justice angles",
    "a 38-year-old casual reader who clicks on curiosity gaps",
    "a 50-year-old who clicks practical how-to and health stories",
]


class ClickRating(BaseModel):
    a: int  # 0-100 likelihood YOU click headline A
    b: int  # 0-100 likelihood YOU click headline B


def _sha(obj) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()


def load_cases() -> list[dict]:
    conf = json.loads((HERE / "confirm_result.json").read_text())
    tests, _ = load_upworthy_archive(str(ARCHIVE))
    by_id = {t.test_id: t for t in tests}
    cases = []
    for c in conf["case_results"]:
        if c.get("dropped"):
            continue
        tid, pair = c["case_id"].split(":")
        ci, ti = (int(x) for x in pair.split("v"))
        t = by_id[tid]
        ctl, trt = t.variants[ci], t.variants[ti]
        cases.append({
            "case_id": c["case_id"],
            "control_hl": ctl.headline,
            "treatment_hl": trt.headline,
            "observed_lift": trt.ctr - ctl.ctr,
        })
    cases.sort(key=lambda c: c["case_id"])  # deterministic order for the prereg hash
    return cases


def load_fresh_cases(n: int, exclude_test_ids: set[str]) -> list[dict]:
    """A fresh, disjoint slice of `n` representable cases, enumerated with the
    SAME canonical pairing (`upworthy_test_to_cases`, baseline=variant 0) as the
    original confirming run, excluding the tests used there."""
    tests, _ = load_upworthy_archive(str(ARCHIVE))
    cases: list[dict] = []
    for t in sorted(tests, key=lambda t: t.test_id):
        if t.test_id in exclude_test_ids:
            continue
        for c in upworthy_test_to_cases(t).cases:
            _, pair = c.case_id.split(":")
            ci, ti = (int(x) for x in pair.split("v"))
            ctl, trt = t.variants[ci], t.variants[ti]
            cases.append({"case_id": c.case_id, "control_hl": ctl.headline,
                          "treatment_hl": trt.headline,
                          "observed_lift": trt.ctr - ctl.ctr})
        if len(cases) >= n:
            break
    cases.sort(key=lambda c: c["case_id"])
    return cases[:n]


def original_test_ids() -> set[str]:
    conf = json.loads((HERE / "confirm_result.json").read_text())
    return {c["case_id"].split(":")[0] for c in conf["case_results"]}


def elicit(client, persona: str | None, hl_control: str, hl_treatment: str,
           rng: random.Random, seed: int | None) -> float:
    """One blinded, order-randomized rating. Returns score_treatment - score_control."""
    treat_is_a = rng.random() < 0.5
    hl_a, hl_b = (hl_treatment, hl_control) if treat_is_a else (hl_control, hl_treatment)
    sys_msg = (f"You are {persona}. You are scrolling a social media feed."
               if persona else
               "You are a typical reader scrolling a social media feed.")
    user = (
        "Two versions of the same story's headline card:\n"
        f"Headline A: {hl_a!r}\n"
        f"Headline B: {hl_b!r}\n\n"
        "For EACH, rate from 0 to 100 how likely YOU personally are to click it "
        "to open the story. Judge them independently. "
        'Respond ONLY as JSON: {"a": <int 0-100>, "b": <int 0-100>}.'
    )
    msgs = [{"role": "system", "content": sys_msg},
            {"role": "user", "content": user}]
    r = client.chat_json(msgs, ClickRating, max_tokens=200, temperature=0.7, seed=seed)
    sa, sb = max(0, min(100, r.a)), max(0, min(100, r.b))
    s_treat, s_ctrl = (sa, sb) if treat_is_a else (sb, sa)
    return (s_treat - s_ctrl) / 100.0


def run_model(model_key: str, cases: list[dict], k: int, ckpt: Path) -> dict:
    model_id = MODEL_IDS[model_key]
    if not model_is_available(model_id):
        raise SystemExit(f"model {model_id} not available (provider key missing)")
    client = get_chat_client(model_id)
    state = json.loads(ckpt.read_text()) if ckpt.exists() else {"panel": {}, "no_persona": {}}
    t0 = time.time()
    for n, case in enumerate(cases):
        cid = case["case_id"]
        rng = random.Random(int(hashlib.sha256(cid.encode()).hexdigest(), 16) % (2**31))
        if cid not in state["panel"]:
            votes = []
            for pi in range(k):
                seed = (int(hashlib.sha256(f"{cid}:{pi}".encode()).hexdigest(), 16) % (2**31))
                votes.append(elicit(client, PERSONAS[pi % len(PERSONAS)],
                                    case["control_hl"], case["treatment_hl"], rng, seed))
            state["panel"][cid] = sum(votes) / len(votes)
        if cid not in state["no_persona"]:
            seed = (int(hashlib.sha256(f"{cid}:np".encode()).hexdigest(), 16) % (2**31))
            state["no_persona"][cid] = elicit(client, None, case["control_hl"],
                                              case["treatment_hl"], rng, seed)
        ckpt.write_text(json.dumps(state))
        print(f"  [{model_key}] {n+1}/{len(cases)} {cid}  panel={state['panel'][cid]:+.3f} "
              f"np={state['no_persona'][cid]:+.3f}  ({time.time()-t0:.0f}s)", flush=True)
    return state


def score(cases: list[dict], signals: dict, label: str, seed: int) -> dict:
    recs = [ExperimentRecord(c["case_id"], c["observed_lift"], signals[c["case_id"]])
            for c in cases]
    cfg = GateConfig(delta=0.0, budget=max(1, len(recs) // 4), bootstrap_trials=2000,
                     seed=seed, conf=0.90)
    res = certify(recs, cfg, aa=None)
    m = res.metrics
    print(f"\n=== {label} ===")
    print(f"  balanced SMR {m['balanced_smr']:.3f} (LB {m['smr_wilson_lo']:.3f}) | "
          f"Kendall tau_b {m['kendall_tau_b']:+.3f} (LB {m['kendall_tau_b_lo']:+.3f}) | "
          f"Spearman {m['spearman_rho']:+.3f}")
    print(f"  MCC {m['mcc']:+.3f} | ECE {m['ece']:.3f} Brier-skill {m['brier_skill']:+.3f} | "
          f"dU {m['delta_u']:+.2f} (LB {m['delta_u_lo']:+.2f}) | tail {m['tail_winner_recall']:.2f}")
    print(f"  VERDICT: {res.verdict}")
    return {"verdict": res.verdict, "metrics": m, "gates": res.gates}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="groq,sonnet")
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--cases", type=int, default=0, help="limit N cases (0=all)")
    ap.add_argument("--fresh", type=int, default=0,
                    help="use a fresh disjoint slice of N cases (0=use confirm-60)")
    ap.add_argument("--tag", default="", help="suffix for checkpoint/output filenames")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    if args.fresh:
        cases = load_fresh_cases(args.fresh, original_test_ids())
    else:
        cases = load_cases()
    if args.cases:
        cases = cases[: args.cases]
    case_set_hash = _sha([c["case_id"] for c in cases])
    print(f"cases={len(cases)} case_set_hash={case_set_hash[:16]} k={args.k} "
          f"models={args.models}")

    out = {"case_set_hash": case_set_hash, "n_cases": len(cases), "k": args.k,
           "models": {}}
    for mk in args.models.split(","):
        mk = mk.strip()
        sfx = ('_smoke' if args.smoke else '') + (f'_{args.tag}' if args.tag else '')
        ckpt = HERE / f"mcmp_ckpt_{mk}{sfx}.json"
        print(f"\n### running {mk} (ckpt {ckpt.name}) ###")
        state = run_model(mk, cases, args.k, ckpt)
        out["models"][mk] = {
            "panel": score(cases, state["panel"], f"{mk} / PANEL (k={args.k})", args.seed),
            "no_persona": score(cases, state["no_persona"], f"{mk} / NO-PERSONA baseline", args.seed),
        }
    out_path = HERE / (f"model_comparison_smoke.json" if args.smoke
                       else f"model_comparison_result{'_'+args.tag if args.tag else ''}.json")
    out_path.write_text(json.dumps(out, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
