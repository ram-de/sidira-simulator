"""iter2 -- M2 (few-shot analogy) robustness stress-test.

Implements PREREG_ITER2_M2_ROBUSTNESS.md EXACTLY. One run, score once, report
whatever it gives. NO tuning after seeing scores.

The M2 PROMPT and PARSE logic are IDENTICAL to iter1's run_m2 in alt_methods.py.
The ONLY change vs iter1: the in-context example block is reordered by a
deterministic permutation (5 orderings x 3 model seeds = 15 leave-one-out
passes). Also computes the base-rate-only floor (predict example-majority label).

Usage:
    export GROQ_API_KEY=...   # never printed
    /opt/homebrew/bin/python3.11 iter2_m2_robustness.py
"""
from __future__ import annotations

import json
import os
import sys
import statistics
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from openai import OpenAI

# Reuse the IDENTICAL prompt-building helpers and parse from iter1.
from alt_methods import (
    MODEL,
    CASES_PATH,
    get_client,
    chat,
    extract_json,
    blinded_stimulus,
)

HERE = Path(__file__).resolve().parent
OUT_PATH = HERE / "iter2_m2_robustness_result.json"

ORDER_SEEDS = [0, 1, 2, 3, 4]        # 5 random orderings of the in-context examples
MODEL_SEEDS = [8000, 8001, 8002]     # 3 model seeds passed to the API seed=


def m2_examples_block(examples) -> str:
    """IDENTICAL formatting to iter1 run_m2's example block, given an ordered
    list of example cases."""
    lines = []
    for j, ex in enumerate(examples, 1):
        lines.append(
            f"Example {j}:\n"
            f"  Domain: {ex['domain']}\n"
            f"  CONTROL: {ex['control']}\n"
            f"  TREATMENT: {ex['treatment']}\n"
            f"  Metric: {ex['metric']}\n"
            f"  Winner: {ex['real_winner']}")
    return "\n".join(lines)


def m2_messages(held, examples):
    """IDENTICAL message structure / wording to iter1 run_m2."""
    examples_block = m2_examples_block(examples)
    return [
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


def parse_winner(raw):
    """IDENTICAL parse to iter1 run_m2."""
    o = extract_json(raw)
    if o:
        w = str(o.get("winner", "")).strip().lower()
        if w in ("control", "treatment"):
            return w
    return None


def run_m2_pass(client, cases, order_seed, model_seed):
    """One full leave-one-out pass with examples reordered by order_seed and the
    API seed fixed to model_seed."""
    correct = 0
    scored = 0
    dropped = []
    per_case = []
    for idx, held in enumerate(cases):
        examples = [c for c in cases if c["id"] != held["id"]]
        # Deterministic, reproducible permutation of the 13 examples for this
        # held-out case under this ordering. Distinct per (order_seed, idx).
        rng = np.random.default_rng(order_seed * 100003 + idx)
        perm = rng.permutation(len(examples))
        ordered = [examples[p] for p in perm]

        msgs = m2_messages(held, ordered)
        raw = chat(client, msgs, seed=model_seed, temperature=0.0, max_tokens=200)
        pred = parse_winner(raw)
        if pred is None:
            dropped.append(held["id"])
            per_case.append({"id": held["id"], "real_winner": held["real_winner"],
                             "predicted": None, "hit": None})
            continue
        hit = (pred == held["real_winner"])
        scored += 1
        correct += int(hit)
        per_case.append({"id": held["id"], "real_winner": held["real_winner"],
                         "predicted": pred, "hit": hit})
    # Accuracy over the 14 held-out cases (drops count against scored denom).
    acc = correct / scored if scored else 0.0
    return {
        "order_seed": order_seed,
        "model_seed": model_seed,
        "correct": correct,
        "scored": scored,
        "dropped_count": len(dropped),
        "dropped_ids": dropped,
        "accuracy": round(acc, 4),
        "per_case": per_case,
    }


def base_rate_only(cases):
    """For each held-out case, predict the majority real_winner label among the
    other 13. The floor."""
    correct = 0
    per_case = []
    for held in cases:
        others = [c["real_winner"] for c in cases if c["id"] != held["id"]]
        pred, _ = Counter(others).most_common(1)[0]
        hit = (pred == held["real_winner"])
        correct += int(hit)
        per_case.append({"id": held["id"], "real_winner": held["real_winner"],
                         "predicted": pred, "hit": hit})
    return correct / len(cases), correct, per_case


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

    # Seed global RNGs explicitly for reproducibility (per-pass uses its own
    # default_rng, but seed these too per the prereg's reproducibility ask).
    np.random.seed(12345)
    import random
    random.seed(12345)

    client = get_client()
    started = datetime.now(timezone.utc).isoformat()

    base_acc, base_correct, base_per_case = base_rate_only(cases)
    print(f"Base-rate-only floor: {base_correct}/{len(cases)} = {base_acc:.4f}\n")

    runs = []
    print("== M2 robustness grid: 5 orderings x 3 model seeds = 15 passes ==")
    for order_seed in ORDER_SEEDS:
        for model_seed in MODEL_SEEDS:
            r = run_m2_pass(client, cases, order_seed, model_seed)
            runs.append(r)
            print(f"  order_seed={order_seed} model_seed={model_seed} "
                  f"acc={r['accuracy']:.4f} ({r['correct']}/{r['scored']}) "
                  f"dropped={r['dropped_count']}")

    accs = [r["accuracy"] for r in runs]
    median = float(np.median(accs))
    p10 = float(np.percentile(accs, 10))
    amin = float(min(accs))
    amax = float(max(accs))

    pass_median = median >= 0.70
    pass_p10 = p10 >= 0.64
    verdict = "PASS" if (pass_median and pass_p10) else "FAIL"

    result = {
        "experiment": "iter2 -- M2 few-shot analogy robustness stress-test",
        "prereg": "research/alt-method-spikes/PREREG_ITER2_M2_ROBUSTNESS.md",
        "model": MODEL,
        "provider": "groq",
        "temperature": 0.0,
        "cases_path": str(CASES_PATH),
        "n_cases": len(cases),
        "order_seeds": ORDER_SEEDS,
        "model_seeds": MODEL_SEEDS,
        "n_runs": len(runs),
        "started_utc": started,
        "finished_utc": datetime.now(timezone.utc).isoformat(),
        "base_rate_only": {
            "accuracy": round(base_acc, 4),
            "correct": base_correct,
            "n": len(cases),
            "per_case": base_per_case,
        },
        "m2_runs": [
            {k: r[k] for k in ("order_seed", "model_seed", "accuracy",
                               "correct", "scored", "dropped_count", "dropped_ids")}
            for r in runs
        ],
        "m2_per_run_per_case": {
            f"order{r['order_seed']}_seed{r['model_seed']}": r["per_case"] for r in runs
        },
        "summary": {
            "accuracies": accs,
            "median": round(median, 4),
            "p10": round(p10, 4),
            "min": round(amin, 4),
            "max": round(amax, 4),
            "base_rate_only_accuracy": round(base_acc, 4),
            "total_dropped_parse": sum(r["dropped_count"] for r in runs),
            "pass_criteria": "median >= 0.70 AND p10 >= 0.64",
            "median_ge_0_70": pass_median,
            "p10_ge_0_64": pass_p10,
            "verdict": verdict,
        },
    }
    OUT_PATH.write_text(json.dumps(result, indent=2))

    print("\n" + "=" * 64)
    print(f"Base-rate floor : {base_acc:.4f} ({base_correct}/{len(cases)})")
    print(f"M2 accuracies   : {accs}")
    print(f"median          : {median:.4f}  (PASS needs >= 0.70 -> {pass_median})")
    print(f"p10             : {p10:.4f}  (PASS needs >= 0.64 -> {pass_p10})")
    print(f"min / max       : {amin:.4f} / {amax:.4f}")
    print(f"total dropped   : {sum(r['dropped_count'] for r in runs)}")
    print(f"\nVERDICT: {verdict}")
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
