"""Alt-method accuracy battery (think-differently loop, iteration 1).

Implements M0/M1/M2/M3 EXACTLY as frozen in PREREG_ALT_METHODS.md. One run,
score once, report whatever it gives. NO tuning after seeing scores.

Cases: the 14-case mixed-winner confirmatory set the comparative forecaster
scored ~0.50 (7/14) on. The prereg names this set as "PORTFOLIO_CASES.json
(14, mixed winners) -- the same set the council/comparative scored ~0.50 on".
The literal `PORTFOLIO_CASES.json` in the repo holds only 8 scored_cases; the
14-case set the comparative actually ran (portfolio_comparative_result.json,
dir_acc 0.50) is PORTFOLIO_CASES_CONFIRM.json. We use that file, per the
disambiguating "14 / ~0.50" qualifier. Blinded stimulus = domain + control +
treatment + metric ONLY (never real_winner/effect/source/counter_intuitive),
except M2's in-context EXAMPLES which intentionally include other cases'
real_winner (per the prereg).

Usage:
    export GROQ_API_KEY=...   # never printed
    /opt/homebrew/bin/python3.11 alt_methods.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
CASES_PATH = REPO / "sessions/agent-behavior-spec/portfolio-benchmark/PORTFOLIO_CASES_CONFIRM.json"
OUT_PATH = HERE / "alt_methods_result.json"

MODEL = "llama-3.3-70b-versatile"
M0_SEEDS = [6000, 6001, 6002, 6003, 6004]  # temp 0.0 for the first, 0.4 for the rest
M1_SEED = 7000
M2_SEED_BASE = 8000

_call_count = 0


def get_client() -> OpenAI:
    key = os.environ.get("GROQ_API_KEY")
    if not key:
        print("FATAL: GROQ_API_KEY not in environment", file=sys.stderr)
        sys.exit(2)
    return OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")


def chat(client: OpenAI, messages, *, seed: int, temperature: float, max_tokens: int = 512) -> str:
    """One Groq call. Counts calls; returns assistant text (or '')."""
    global _call_count
    _call_count += 1
    r = client.chat.completions.create(
        model=MODEL, messages=messages,
        max_tokens=max_tokens, temperature=temperature, seed=seed,
    )
    return r.choices[0].message.content or ""


def extract_json(text: str):
    """Tolerant single-JSON-object extractor: strip code fences, scan for the
    first balanced {...} that parses. Returns dict or None."""
    if not text:
        return None
    t = text.strip()
    if "```" in t:
        # drop fence markers (``` and ```json)
        parts = []
        for chunk in t.split("```"):
            parts.append(chunk)
        t = "\n".join(parts)
    # scan for balanced brace spans
    starts = [i for i, ch in enumerate(t) if ch == "{"]
    for s in starts:
        depth = 0
        for e in range(s, len(t)):
            if t[e] == "{":
                depth += 1
            elif t[e] == "}":
                depth -= 1
                if depth == 0:
                    cand = t[s:e + 1]
                    try:
                        return json.loads(cand)
                    except Exception:
                        break
    return None


def blinded_stimulus(case) -> str:
    return (f"Domain: {case['domain']}\n"
            f"Version CONTROL: {case['control']}\n"
            f"Version TREATMENT: {case['treatment']}\n"
            f"Metric: {case['metric']}")


# ----------------------------------------------------------------------------
# M0 -- holistic baseline (anchor). k=5 votes, majority. ALSO feeds M3.
# ----------------------------------------------------------------------------
def m0_vote(client, case, seed, temperature):
    msgs = [
        {"role": "system", "content":
            "You are an expert forecaster of how real customers respond to product and policy "
            "changes. You compare two versions and predict which performs better on a stated metric, "
            "grounded in how real audiences actually behave -- including when the intuitive option "
            "backfires. Mind the metric's direction (e.g. lower churn is better)."},
        {"role": "user", "content":
            blinded_stimulus(case) + "\n\n"
            "Which version performs BETTER on that metric for real customers? Respond ONLY with one "
            'JSON object: {"winner": "control" or "treatment"}'},
    ]
    raw = chat(client, msgs, seed=seed, temperature=temperature, max_tokens=200)
    o = extract_json(raw)
    if o:
        w = str(o.get("winner", "")).strip().lower()
        if w in ("control", "treatment"):
            return w
    return None


def run_m0(client, cases):
    rows = []
    for c in cases:
        votes = []
        for i, seed in enumerate(M0_SEEDS):
            temp = 0.0 if i == 0 else 0.4
            w = m0_vote(client, c, seed, temp)
            if w:
                votes.append(w)
        if not votes:
            rows.append({"id": c["id"], "real_winner": c["real_winner"],
                         "predicted": None, "hit": None, "votes": [],
                         "vote_counts": {}, "agreement": None, "dropped": True})
            continue
        counts = Counter(votes)
        pred, top = counts.most_common(1)[0]
        agreement = top / len(votes)  # max vote share
        hit = (pred == c["real_winner"])
        rows.append({"id": c["id"], "real_winner": c["real_winner"],
                     "predicted": pred, "hit": hit, "votes": votes,
                     "vote_counts": dict(counts), "agreement": agreement,
                     "dropped": False})
        print(f"  M0 {c['id'][:34]:34s} real={c['real_winner']:9s} pred={pred:9s} "
              f"agree={top}/{len(votes)} {'OK' if hit else 'X'}")
    return rows


# ----------------------------------------------------------------------------
# M1 -- hypothesis decomposition (LLM as feature-extractor). FROZEN rule.
# ----------------------------------------------------------------------------
M1_MECHS = ["relevance_gain", "salience_gain", "friction_add",
            "reactance_add", "overload_add", "loss_salience_add"]


def run_m1(client, cases):
    rows = []
    for c in cases:
        msgs = [
            {"role": "system", "content":
                "You are a careful UX/behavioral-science analyst. You DO NOT predict which version "
                "wins. You only rate mechanisms and classify the metric's direction, factually."},
            {"role": "user", "content":
                blinded_stimulus(c) + "\n\n"
                "Compared to CONTROL, rate the TREATMENT on each mechanism below in [0,1] "
                "(0 = not at all, 1 = strongly), as it pertains to the stated metric:\n"
                "- relevance_gain: treatment better matches the user's actual need/intent\n"
                "- salience_gain: treatment makes the value/CTA more prominent\n"
                "- friction_add: treatment adds steps/effort/cost/latency\n"
                "- reactance_add: treatment feels pushy/intrusive/controlling/surveilling\n"
                "- overload_add: treatment adds options/decisions/cognitive load\n"
                "- loss_salience_add: treatment surfaces a price/loss/risk the user would rather not face\n\n"
                "Also classify metric_polarity: 'higher_better' if a higher value of the metric is the "
                "good outcome, 'lower_better' if a lower value is the good outcome (e.g. churn).\n\n"
                "Respond ONLY with one JSON object with keys: relevance_gain, salience_gain, "
                "friction_add, reactance_add, overload_add, loss_salience_add, metric_polarity."},
        ]
        raw = chat(client, msgs, seed=M1_SEED, temperature=0.0, max_tokens=400)
        o = extract_json(raw)
        if not o:
            rows.append({"id": c["id"], "real_winner": c["real_winner"],
                         "predicted": None, "hit": None, "dropped": True,
                         "ratings": None, "s": None, "metric_polarity": None})
            print(f"  M1 {c['id'][:34]:34s} PARSE-FAIL (dropped)")
            continue
        try:
            ratings = {m: float(o.get(m, 0.0)) for m in M1_MECHS}
        except Exception:
            rows.append({"id": c["id"], "real_winner": c["real_winner"],
                         "predicted": None, "hit": None, "dropped": True,
                         "ratings": o, "s": None, "metric_polarity": None})
            print(f"  M1 {c['id'][:34]:34s} BAD-RATINGS (dropped)")
            continue
        polarity = str(o.get("metric_polarity", "")).strip().lower()
        if polarity not in ("higher_better", "lower_better"):
            rows.append({"id": c["id"], "real_winner": c["real_winner"],
                         "predicted": None, "hit": None, "dropped": True,
                         "ratings": ratings, "s": None, "metric_polarity": polarity})
            print(f"  M1 {c['id'][:34]:34s} BAD-POLARITY '{polarity}' (dropped)")
            continue
        # FROZEN rule
        s = (ratings["relevance_gain"] + ratings["salience_gain"]
             - ratings["friction_add"] - ratings["reactance_add"]
             - ratings["overload_add"] - ratings["loss_salience_add"])
        if s == 0:
            pred = "control"  # tie -> status quo
        elif polarity == "higher_better":
            pred = "treatment" if s > 0 else "control"
        else:  # lower_better: treatment wins iff s < 0
            pred = "treatment" if s < 0 else "control"
        hit = (pred == c["real_winner"])
        rows.append({"id": c["id"], "real_winner": c["real_winner"],
                     "predicted": pred, "hit": hit, "dropped": False,
                     "ratings": ratings, "s": s, "metric_polarity": polarity})
        print(f"  M1 {c['id'][:34]:34s} real={c['real_winner']:9s} pred={pred:9s} "
              f"s={s:+.2f} pol={polarity[:6]} {'OK' if hit else 'X'}")
    return rows


# ----------------------------------------------------------------------------
# M2 -- leave-one-out few-shot analogy. Other 13 as labeled examples. k=1 t=0.
# ----------------------------------------------------------------------------
def run_m2(client, cases):
    rows = []
    for idx, held in enumerate(cases):
        examples = [c for c in cases if c["id"] != held["id"]]
        lines = []
        for j, ex in enumerate(examples, 1):
            lines.append(
                f"Example {j}:\n"
                f"  Domain: {ex['domain']}\n"
                f"  CONTROL: {ex['control']}\n"
                f"  TREATMENT: {ex['treatment']}\n"
                f"  Metric: {ex['metric']}\n"
                f"  Winner: {ex['real_winner']}")
        examples_block = "\n".join(lines)
        msgs = [
            {"role": "system", "content":
                "You predict the winner of a product A/B test by analogy to labeled examples. "
                "Reason from the patterns in the examples, not outside knowledge."},
            {"role": "user", "content":
                "Here are labeled examples of product changes and which version won:\n\n"
                + examples_block + "\n\n"
                "Now predict the winner for this NEW case, by analogy to the examples above:\n"
                + blinded_stimulus(held) + "\n\n"
                'Respond ONLY with one JSON object: {"winner": "control" or "treatment"}'},
        ]
        raw = chat(client, msgs, seed=M2_SEED_BASE + idx, temperature=0.0, max_tokens=200)
        o = extract_json(raw)
        pred = None
        if o:
            w = str(o.get("winner", "")).strip().lower()
            if w in ("control", "treatment"):
                pred = w
        if pred is None:
            rows.append({"id": held["id"], "real_winner": held["real_winner"],
                         "predicted": None, "hit": None, "dropped": True})
            print(f"  M2 {held['id'][:34]:34s} PARSE-FAIL (dropped)")
            continue
        hit = (pred == held["real_winner"])
        rows.append({"id": held["id"], "real_winner": held["real_winner"],
                     "predicted": pred, "hit": hit, "dropped": False})
        print(f"  M2 {held['id'][:34]:34s} real={held['real_winner']:9s} pred={pred:9s} "
              f"{'OK' if hit else 'X'}")
    return rows


# ----------------------------------------------------------------------------
# M3 -- selective prediction (meta-reliability). Reuse M0 votes. No new calls.
# ----------------------------------------------------------------------------
def run_m3(m0_rows):
    scored = [r for r in m0_rows if not r["dropped"]]
    n = len(scored)
    full_correct = sum(1 for r in scored if r["hit"])
    full_acc = full_correct / n if n else 0.0

    hi = [r for r in scored if r["agreement"] is not None and r["agreement"] >= 0.8]  # >= 4/5
    hi_correct = sum(1 for r in hi if r["hit"])
    hi_acc = hi_correct / len(hi) if hi else None

    # accuracy-coverage curve: sort by agreement desc (ties by id), cumulative
    ordered = sorted(scored, key=lambda r: (-r["agreement"], r["id"]))
    curve = []
    cum_correct = 0
    for k, r in enumerate(ordered, 1):
        cum_correct += int(r["hit"])
        curve.append({
            "top_n": k,
            "coverage_frac": round(k / n, 4),
            "accuracy": round(cum_correct / k, 4),
            "min_agreement_in_subset": round(r["agreement"], 4),
        })

    return {
        "full_set_n": n,
        "full_set_accuracy": round(full_acc, 4),
        "full_set_correct": full_correct,
        "high_agreement_subset_threshold": "agreement >= 4/5",
        "high_agreement_subset_n": len(hi),
        "high_agreement_subset_accuracy": round(hi_acc, 4) if hi_acc is not None else None,
        "high_agreement_subset_correct": hi_correct,
        "high_agreement_subset_ids": [r["id"] for r in hi],
        "accuracy_coverage_curve": curve,
    }


def acc_of(rows):
    scored = [r for r in rows if not r["dropped"]]
    correct = sum(1 for r in scored if r["hit"])
    return correct, len(scored)


def main() -> int:
    data = json.loads(CASES_PATH.read_text())
    if isinstance(data, list):
        cases = data
    elif isinstance(data, dict) and isinstance(data.get("scored_cases"), list):
        cases = data["scored_cases"]
    elif isinstance(data, dict) and isinstance(data.get("cases"), list):
        cases = data["cases"]
    else:
        print("FATAL: could not locate case list", file=sys.stderr)
        return 2
    print(f"Loaded {len(cases)} cases from {CASES_PATH.name}\n")

    client = get_client()
    started = datetime.now(timezone.utc).isoformat()

    print("== M0 holistic baseline (k=5 votes) ==")
    m0 = run_m0(client, cases)
    print("\n== M1 hypothesis decomposition (frozen rule) ==")
    m1 = run_m1(client, cases)
    print("\n== M2 leave-one-out few-shot analogy ==")
    m2 = run_m2(client, cases)
    print("\n== M3 selective prediction (reuse M0) ==")
    m3 = run_m3(m0)

    m0_correct, m0_n = acc_of(m0)
    m1_correct, m1_n = acc_of(m1)
    m2_correct, m2_n = acc_of(m2)

    dropped = {
        "M0": [r["id"] for r in m0 if r["dropped"]],
        "M1": [r["id"] for r in m1 if r["dropped"]],
        "M2": [r["id"] for r in m2 if r["dropped"]],
    }

    result = {
        "experiment": "alt-method battery (think-differently loop, iter 1)",
        "prereg": "research/alt-method-spikes/PREREG_ALT_METHODS.md",
        "model": MODEL,
        "provider": "groq",
        "cases_path": str(CASES_PATH),
        "n_cases": len(cases),
        "m0_seeds": M0_SEEDS,
        "m0_temps": "seed 6000 -> temp 0.0; seeds 6001-6004 -> temp 0.4",
        "m1_seed": M1_SEED,
        "m2_seed_base": M2_SEED_BASE,
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "total_api_calls": _call_count,
        "headline": {
            "M0_accuracy": f"{m0_correct}/{m0_n}",
            "M0_accuracy_frac": round(m0_correct / m0_n, 4) if m0_n else None,
            "M1_accuracy": f"{m1_correct}/{m1_n}",
            "M1_accuracy_frac": round(m1_correct / m1_n, 4) if m1_n else None,
            "M2_accuracy": f"{m2_correct}/{m2_n}",
            "M2_accuracy_frac": round(m2_correct / m2_n, 4) if m2_n else None,
            "M3": m3,
        },
        "per_case": {
            "M0": [{k: r[k] for k in ("id", "real_winner", "predicted", "hit",
                                      "vote_counts", "agreement")} for r in m0],
            "M1": [{k: r[k] for k in ("id", "real_winner", "predicted", "hit",
                                      "s", "metric_polarity", "ratings")} for r in m1],
            "M2": [{k: r[k] for k in ("id", "real_winner", "predicted", "hit")} for r in m2],
        },
        "dropped_parse_failures": dropped,
    }
    OUT_PATH.write_text(json.dumps(result, indent=2))

    print("\n" + "=" * 64)
    print(f"M0 holistic     : {m0_correct}/{m0_n}")
    print(f"M1 decomposition: {m1_correct}/{m1_n}")
    print(f"M2 analogy      : {m2_correct}/{m2_n}")
    print(f"M3 full-set     : {m3['full_set_correct']}/{m3['full_set_n']}  "
          f"(acc {m3['full_set_accuracy']})")
    print(f"M3 agree>=4/5   : "
          f"{m3['high_agreement_subset_correct']}/{m3['high_agreement_subset_n']} "
          f"(acc {m3['high_agreement_subset_accuracy']})")
    print(f"total API calls : {_call_count}")
    print(f"dropped         : {dropped}")
    print(f"\nwrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
