"""Powered confirmation: expert-forecaster vs the certified advertising-as-harm
sign inversion, on a finer stratification (gender x recency-tier x email) with a
permutation test (#342 / Benchmark 2).

The 6-case exploratory probe showed the sign-fix (Sonnet visit dir_acc 0.0->1.0,
Spearman -0.29->+0.65). This re-runs at power (>= the >=8-case floor) on real RCT
ground truth, pre-registered, with a label-permutation p-value on the rank
correlation. Direction accuracy is the headline (the sign-fix); rank rho tests
whether visit heterogeneity is recovered above chance.

    PYTHONPATH=backend <venv>/bin/python <thisfile> --csv <path>
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client, model_is_available
from sidira_simulator.services.directional_gate import kendall_tau_b, _sign_dead
from sidira_simulator.services.statistics import spearman_rho

HERE = Path(__file__).resolve().parent
MODEL_IDS = {"sonnet": "claude-sonnet-4-6", "groq": "llama-3.3-70b-versatile"}
GENDER = {"mens_buyer": "purchased MEN'S merchandise (not women's) in the past year",
          "womens_buyer": "purchased WOMEN'S merchandise (not men's) in the past year",
          "both_buyer": "purchased BOTH men's and women's merchandise in the past year"}
REC = {"recent": "and shopped recently (within ~3 months)",
       "lapsing": "and last shopped ~4-6 months ago",
       "dormant": "and have not shopped in 7+ months"}
EMAIL = {"Mens E-Mail": "a promotional email featuring MEN'S merchandise",
         "Womens E-Mail": "a promotional email featuring WOMEN'S merchandise"}
_OBJ = re.compile(r'\{[^{}]*\}')


def gender_of(r):
    m, w = int(r["mens"]), int(r["womens"])
    return "mens_buyer" if (m and not w) else "womens_buyer" if (w and not m) else "both_buyer" if (m and w) else None


def rec_of(r):
    v = float(r["recency"])
    return "recent" if v <= 3 else "lapsing" if v <= 6 else "dormant"


def build_cases(csv_path, min_n=300):
    rows = list(csv.DictReader(open(csv_path)))
    cell = defaultdict(lambda: defaultdict(lambda: {"v": 0, "n": 0}))
    for r in rows:
        g = gender_of(r)
        if g is None:
            continue
        key = (g, rec_of(r))
        d = cell[key][r["segment"]]
        d["v"] += int(r["visit"]); d["n"] += 1
    cases = []
    for (g, rc), arms in sorted(cell.items()):
        ctrl = arms.get("No E-Mail")
        if not ctrl or ctrl["n"] < min_n:
            continue
        base = ctrl["v"] / ctrl["n"]
        for email in ("Mens E-Mail", "Womens E-Mail"):
            a = arms.get(email)
            if not a or a["n"] < min_n:
                continue
            cases.append({"gender": g, "recency": rc, "email": email,
                          "real_visit_uplift": a["v"] / a["n"] - base, "n": a["n"]})
    return cases


def _json(raw):
    for c in reversed(_OBJ.findall(raw)):
        try:
            o = json.loads(c)
            if isinstance(o, dict):
                return o
        except Exception:
            continue
    return None


def forecast(client, case, seed):
    msgs = [
        {"role": "system", "content": "You are an expert in email-marketing causal effects. You "
         "predict how a promotional email changes customer behavior vs sending no email, grounded "
         "in how real randomized campaigns move metrics."},
        {"role": "user", "content":
            f"Audience: customers who {GENDER[case['gender']]} {REC[case['recency']]}.\n"
            f"Campaign: the retailer sends {EMAIL[case['email']]} to this audience; a randomized "
            "holdout gets NO email.\nPredict the change versus the no-email holdout in site VISIT "
            'rate over two weeks, in percentage points. Respond ONLY JSON: {"visit_pp": <float>}'}]
    for attempt in range(3):
        try:
            raw = client.chat(msgs, max_tokens=200, temperature=0.0 if attempt else 0.3, seed=seed)
        except Exception:
            continue
        o = _json(raw)
        if o and "visit_pp" in o:
            try:
                return float(o["visit_pp"])
            except (TypeError, ValueError):
                continue
    return None


def perm_p(pred, real, obs_rho, trials=5000, seed=42):
    rng = random.Random(seed)
    r = list(real)
    hits = 0
    for _ in range(trials):
        rng.shuffle(r)
        if abs(spearman_rho(pred, r)) >= abs(obs_rho):
            hits += 1
    return (hits + 1) / (trials + 1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv")
    ap.add_argument("--models", default="sonnet,groq")
    args = ap.parse_args()
    cases = build_cases(args.csv)
    real = [c["real_visit_uplift"] for c in cases]
    print(f"cases={len(cases)} (gender x recency x email); real visit signs: "
          f"{sum(r>0 for r in real)} pos / {sum(r<0 for r in real)} neg")
    out = {"n_cases": len(cases), "cases": cases,
           "baseline_reader_roleplay_visit": {"dir_acc": 0.0, "rank_rho": -0.29}, "models": {}}
    for mk in args.models.split(","):
        mid = MODEL_IDS[mk]
        if not model_is_available(mid):
            print(f"skip {mk}"); continue
        client = get_chat_client(mid)
        pred, rl = [], []
        for i, c in enumerate(cases):
            f = forecast(client, c, seed=2000 + i)
            if f is None:
                print(f"  DROP {c['gender']}/{c['recency']}/{c['email']}"); continue
            pred.append(f); rl.append(c["real_visit_uplift"])
        dir_acc = sum(1 for p, r in zip(pred, rl) if _sign_dead(p, 0) == _sign_dead(r, 0)) / len(pred)
        rho = spearman_rho(pred, rl); tau = kendall_tau_b(pred, rl)
        p = perm_p(pred, rl, rho)
        print(f"\n### {mk} expert-forecaster (VISIT, n={len(pred)}) ###")
        print(f"  direction_accuracy = {dir_acc:.3f}   (reader-roleplay certified: 0.0)")
        print(f"  Spearman rho = {rho:+.3f}  (perm p = {p:.4f})   Kendall tau_b = {tau:+.3f}")
        out["models"][mk] = {"n": len(pred), "dir_acc": dir_acc, "spearman": rho,
                             "kendall": tau, "perm_p": p}
    (HERE / "forecaster_powered_result.json").write_text(json.dumps(out, indent=2, default=float))
    print(f"\nwrote {HERE/'forecaster_powered_result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
