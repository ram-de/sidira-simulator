"""Powered HETEROGENEITY certification (#342, Codex-recommended path B).

The sign-fix (email raises visits) is partly common-world knowledge. The
non-trivial product claim is WHO RESPONDS MORE. This certifies that at power:
finer stratification (gender x recency x channel x email), BOTH outcomes,
heterogeneity rank correlation as the PRIMARY endpoint with a label-permutation
p-value, plus the non-obvious GENDER-MATCH differential (does the model know
men's-buyers respond more to the men's email than the women's email?). Sonnet
(primary) + Groq (model-stability). Ground truth from the real Hillstrom RCT CSV.

Pre-registered pass/fail bar (see PREREG_HETEROGENEITY.json):
  CERTIFIED iff VISIT heterogeneity Spearman rho > 0.30 AND permutation p < 0.05.

    PYTHONPATH=backend <venv>/bin/python <thisfile>
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
REC = {"recent": "shopped within ~3 months", "lapsing": "last shopped ~4-6 months ago",
       "dormant": "have not shopped in 7+ months"}
EMAIL = {"Mens E-Mail": "a promotional email featuring MEN'S merchandise",
         "Womens E-Mail": "a promotional email featuring WOMEN'S merchandise"}
_OBJ = re.compile(r'\{[^{}]*\}')


def gender_of(r):
    m, w = int(r["mens"]), int(r["womens"])
    return "mens_buyer" if (m and not w) else "womens_buyer" if (w and not m) else "both_buyer" if (m and w) else None


def rec_of(r):
    v = float(r["recency"]); return "recent" if v <= 3 else "lapsing" if v <= 6 else "dormant"


def build_cases(csv_path, min_n=250):
    rows = list(csv.DictReader(open(csv_path)))
    cell = defaultdict(lambda: defaultdict(lambda: {"v": 0, "c": 0, "n": 0}))
    for r in rows:
        g = gender_of(r)
        if g is None:
            continue
        key = (g, rec_of(r), r["channel"])
        d = cell[key][r["segment"]]
        d["v"] += int(r["visit"]); d["c"] += int(r["conversion"]); d["n"] += 1
    cases = []
    for (g, rc, ch), arms in sorted(cell.items()):
        ctrl = arms.get("No E-Mail")
        if not ctrl or ctrl["n"] < min_n:
            continue
        bv, bc = ctrl["v"] / ctrl["n"], ctrl["c"] / ctrl["n"]
        for email in ("Mens E-Mail", "Womens E-Mail"):
            a = arms.get(email)
            if not a or a["n"] < min_n:
                continue
            cases.append({"gender": g, "recency": rc, "channel": ch, "email": email,
                          "real_visit": a["v"] / a["n"] - bv, "real_conv": a["c"] / a["n"] - bc})
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


def forecast(client, c, seed):
    msgs = [
        {"role": "system", "content": "You are an expert in email-marketing causal effects. You "
         "predict how a promotional email changes customer behavior vs no email, grounded in how "
         "real randomized campaigns move metrics. Different audiences respond by different amounts."},
        {"role": "user", "content":
            f"Audience: customers who {GENDER[c['gender']]}, who {REC[c['recency']]}, acquired via "
            f"the {c['channel']} channel.\nCampaign: send {EMAIL[c['email']]} to this audience; a "
            "randomized holdout gets NO email.\nPredict the change vs the holdout in (1) site VISIT "
            'rate and (2) CONVERSION rate, in percentage points. Respond ONLY JSON: '
            '{"visit_pp": <float>, "conv_pp": <float>}'}]
    for attempt in range(3):
        try:
            raw = client.chat(msgs, max_tokens=250, temperature=0.0 if attempt else 0.3, seed=seed)
        except Exception:
            continue
        o = _json(raw)
        if o and "visit_pp" in o and "conv_pp" in o:
            try:
                return float(o["visit_pp"]), float(o["conv_pp"])
            except (TypeError, ValueError):
                continue
    return None


def perm_p(pred, real, obs, trials=5000, seed=42):
    rng = random.Random(seed); r = list(real); hits = 0
    for _ in range(trials):
        rng.shuffle(r)
        if abs(spearman_rho(pred, r)) >= abs(obs):
            hits += 1
    return (hits + 1) / (trials + 1)


def gender_match_diff(cases, pred_v):
    """Non-obvious heterogeneity: per (gender,recency,channel), does predicted
    (mens_email - womens_email) visit-uplift differential correlate with real?"""
    by = defaultdict(dict)
    for i, c in enumerate(cases):
        by[(c["gender"], c["recency"], c["channel"])][c["email"]] = (pred_v[i], c["real_visit"])
    pd, rd = [], []
    for k, arms in by.items():
        if "Mens E-Mail" in arms and "Womens E-Mail" in arms:
            pd.append(arms["Mens E-Mail"][0] - arms["Womens E-Mail"][0])
            rd.append(arms["Mens E-Mail"][1] - arms["Womens E-Mail"][1])
    if len(pd) < 3:
        return None
    rho = spearman_rho(pd, rd)
    return {"n_triples": len(pd), "spearman": rho, "perm_p": perm_p(pd, rd, rho)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default="/Users/ram/Projects/sidira-simulator/local-artifacts/hillstrom/hillstrom.csv")
    ap.add_argument("--models", default="sonnet,groq")
    args = ap.parse_args()
    cases = build_cases(args.csv)
    print(f"cases={len(cases)} (gender x recency x channel x email); "
          f"visit signs {sum(c['real_visit']>0 for c in cases)}+/{sum(c['real_visit']<0 for c in cases)}-")
    out = {"n_cases": len(cases), "cases": cases, "models": {}}
    for mk in args.models.split(","):
        mid = MODEL_IDS[mk]
        if not model_is_available(mid):
            print(f"skip {mk}"); continue
        client = get_chat_client(mid)
        pv, pc, used = [], [], []
        for i, c in enumerate(cases):
            f = forecast(client, c, seed=3000 + i)
            if f is None:
                print(f"  DROP {c['gender']}/{c['recency']}/{c['channel']}/{c['email']}"); continue
            pv.append(f[0]); pc.append(f[1]); used.append(c)
        rv = [c["real_visit"] for c in used]; rc = [c["real_conv"] for c in used]
        res = {
            "n": len(used),
            "visit": {"dir_acc": sum(_sign_dead(p, 0) == _sign_dead(r, 0) for p, r in zip(pv, rv)) / len(pv),
                      "spearman": spearman_rho(pv, rv), "kendall": kendall_tau_b(pv, rv),
                      "perm_p": perm_p(pv, rv, spearman_rho(pv, rv))},
            "conversion": {"dir_acc": sum(_sign_dead(p, 0) == _sign_dead(r, 0) for p, r in zip(pc, rc)) / len(pc),
                           "spearman": spearman_rho(pc, rc), "kendall": kendall_tau_b(pc, rc),
                           "perm_p": perm_p(pc, rc, spearman_rho(pc, rc))},
            "gender_match_visit": gender_match_diff(used, pv),
        }
        v, cv, gm = res["visit"], res["conversion"], res["gender_match_visit"]
        certified = v["spearman"] > 0.30 and v["perm_p"] < 0.05
        res["heterogeneity_certified"] = certified
        print(f"\n### {mk} (n={res['n']}) ###")
        print(f"  VISIT      heterogeneity Spearman {v['spearman']:+.3f} (perm p {v['perm_p']:.4f}) "
              f"Kendall {v['kendall']:+.3f} | dir_acc {v['dir_acc']:.2f}")
        print(f"  CONVERSION heterogeneity Spearman {cv['spearman']:+.3f} (perm p {cv['perm_p']:.4f}) | "
              f"dir_acc {cv['dir_acc']:.2f}")
        if gm:
            print(f"  GENDER-MATCH differential Spearman {gm['spearman']:+.3f} (perm p {gm['perm_p']:.4f}, "
                  f"n_triples {gm['n_triples']})")
        print(f"  PRE-REGISTERED BAR (visit rho>0.30 AND p<0.05): "
              f"{'CERTIFIED' if certified else 'NOT certified'}")
        out["models"][mk] = res
    (HERE / "forecaster_heterogeneity_result.json").write_text(json.dumps(out, indent=2, default=float))
    print(f"\nwrote {HERE/'forecaster_heterogeneity_result.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
