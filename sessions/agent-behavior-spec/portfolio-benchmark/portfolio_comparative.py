"""Re-run the product-change portfolio through the COMPARATIVE-forecaster path (#342).

The prior result (0.286, 4/14) used the per-arm reader-roleplay engine and was
killed by a "more-is-better" bias on counter-intuitive changes. This re-runs the
14 confirmatory cases with the validated comparative-forecaster framing: show the
expert BOTH versions + the metric in one pass, ask which wins, score direction
accuracy vs the real winner. BLIND — `effect` / `real_winner` are never shown.

    PYTHONPATH=backend <venv>/bin/python <thisfile> [--k 4]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client

HERE = Path(__file__).resolve().parent
CASES = HERE / "PORTFOLIO_CASES_CONFIRM.json"
_OBJ = re.compile(r"\{[^{}]*\}")


def predict_winner(client, case, seed) -> str | None:
    msgs = [
        {"role": "system", "content": "You are an expert forecaster of how real customers respond "
         "to product and policy changes. You compare two versions and predict which performs better "
         "on a stated metric, grounded in how real audiences actually behave — including when the "
         "intuitive option backfires. Mind the metric's direction (e.g. lower churn is better)."},
        {"role": "user", "content":
            f"Domain: {case['domain']}\n"
            f"Version CONTROL: {case['control']}\n"
            f"Version TREATMENT: {case['treatment']}\n"
            f"Metric: {case['metric']}\n\n"
            "Which version performs BETTER on that metric for real customers? Respond ONLY with one "
            'JSON object: {"winner": "control" or "treatment", "confidence": <0-1>, "reason": "<one sentence>"}'}]
    for attempt in range(3):
        raw = client.chat(msgs, max_tokens=300, temperature=0.0 if attempt else 0.4, seed=seed)
        for cand in reversed(_OBJ.findall(raw)):
            try:
                o = json.loads(cand)
            except Exception:
                continue
            w = str(o.get("winner", "")).strip().lower()
            if w in ("control", "treatment"):
                return w
        m = re.search(r'"?winner"?\s*[:=]\s*"?(control|treatment)', raw, re.I)
        if m:
            return m.group(1).lower()
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cases = json.loads(CASES.read_text())["scored_cases"]
    if args.smoke:
        cases = cases[:1]
    client = get_chat_client("claude-sonnet-4-6")
    correct = scored = dropped = 0
    rows = []
    for c in cases:
        votes = [w for w in (predict_winner(client, c, 6000 + i) for i in range(args.k)) if w]
        if not votes:
            dropped += 1; continue
        pred = Counter(votes).most_common(1)[0][0]
        hit = pred == c["real_winner"]
        scored += 1; correct += int(hit)
        rows.append({"id": c["id"], "real": c["real_winner"], "pred": pred,
                     "counter_intuitive": c.get("counter_intuitive"), "hit": hit})
        print(f"  {c['id'][:38]:38s} real={c['real_winner']:9s} pred={pred:9s} {'OK' if hit else 'X'}")
    acc = correct / scored if scored else 0.0
    print(f"\n=== PORTFOLIO comparative-forecaster: direction accuracy {acc:.3f} ({correct}/{scored}, dropped {dropped}) ===")
    print(f"  prior (per-arm reader-roleplay): 0.286 (4/14) | chance ~0.5")
    if not args.smoke:
        (HERE / "portfolio_comparative_result.json").write_text(json.dumps(
            {"direction_accuracy": acc, "correct": correct, "scored": scored,
             "dropped": dropped, "k": args.k, "prior_accuracy": 0.286, "cases": rows}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
