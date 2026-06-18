"""Method-change experiment (#342): can we beat the more-is-better prior-echo on
counter-intuitive product changes WITHOUT re-collapsing the easy-case signal?

Four arms over the V4 counter-intuitive cases, model + cases held fixed:
  1. comparative_baseline  — current method: show both, ask which wins.
  2. comparative_ledger    — show both, force a SIGNED mechanism ledger (positive AND
                             negative/backfire pathways) + an explicit "when does the
                             richer option backfire?" step BEFORE the verdict. (conservative
                             fix: targets prior-echo without removing the comparison that
                             preserves signal.)
  3. per_arm_behavioral    — score EACH version in ISOLATION (never shown together), as an
                             audience behavioral-responsiveness estimate; winner = higher
                             mean. (the aggressive arm — directly tests the founder's concern
                             that isolation re-collapses the signal, à la the old two-pass.)
  4. placebo_leaner        — crude pro-simpler thumb. ARTIFACT CONTROL: a real fix must beat
                             this on less-won WITHOUT sacrificing more-won the way a thumb does.

Discriminator = less-won subset accuracy. Guard = more-won accuracy must not regress.
Pre-registered (PREREG_METHOD_EXPERIMENT.json). Small n (10) → detects only LARGE effects;
this is a FILTER, not a confirmation.

    PYTHONPATH=backend <venv>/bin/python method_experiment.py [--k 4] [--model claude-sonnet-4-6]
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from sidira_simulator.adapters.llm import get_chat_client

HERE = Path(__file__).resolve().parent
CASES = HERE.parent / "portfolio-benchmark" / "PORTFOLIO_CASES_EXPANSION_V4.json"
_OBJ = re.compile(r"\{(?:[^{}]|\{[^{}]*\})*\}")

LESS_WON = ["apparel_hide_discount_surfacing", "gift_certificate_expiry_window",
            "time_scarcity_promo_framing", "product_image_hover_zoom"]
MORE_WON = ["homepage_carousel_item_count", "donation_banner_only_word",
            "upload_dropzone_border_button_weight", "vendor_listing_popularity_count"]
AMBIG = ["referral_reward_sender_certainty", "referral_reward_recipient_certainty"]

FORECASTER_SYS = ("You are an expert forecaster of how real customers respond to product and "
                  "policy changes, grounded in how real audiences actually behave — including "
                  "when the intuitive option backfires. Mind the metric's direction.")


def _parse(raw, keys):
    for cand in reversed(_OBJ.findall(raw)):
        try:
            o = json.loads(cand)
        except Exception:
            continue
        if any(k in o for k in keys):
            return o
    return None


def _winner_from(o):
    if not o:
        return None
    w = str(o.get("winner", "")).strip().lower()
    return w if w in ("control", "treatment") else None


def arm_comparative_baseline(client, case, seed):
    msgs = [{"role": "system", "content": FORECASTER_SYS},
            {"role": "user", "content":
             f"Domain: {case['domain']}\nVersion CONTROL: {case['control']}\n"
             f"Version TREATMENT: {case['treatment']}\nMetric: {case['metric']}\n\n"
             "Which version performs BETTER on that metric for real customers? Respond ONLY with "
             'JSON: {"winner": "control" or "treatment", "confidence": <0-1>}'}]
    return _winner_from(_parse(client.chat(msgs, max_tokens=300, temperature=0.0 if seed % 2 else 0.4, seed=seed), ["winner"]))


def arm_comparative_ledger(client, case, seed):
    msgs = [{"role": "system", "content": FORECASTER_SYS},
            {"role": "user", "content":
             f"Domain: {case['domain']}\nVersion CONTROL: {case['control']}\n"
             f"Version TREATMENT: {case['treatment']}\nMetric: {case['metric']}\n\n"
             "Do NOT answer which wins yet. First reason about the CHANGE from CONTROL to TREATMENT:\n"
             "1. positive_pathways: concrete ways the change could IMPROVE the metric, and for which part of the audience.\n"
             "2. negative_pathways: concrete ways the change could HURT the metric — added friction, distrust/"
             "reactance, choice overload, reduced urgency, quality-signal loss, attention cost — and for whom.\n"
             "3. backfire_check: the more-featured / more-obvious / 'richer' option is often ASSUMED to win. State the "
             "specific conditions under which it backfires HERE, for this audience.\n"
             "Only AFTER weighing both sides, pick the winner. Respond ONLY with JSON: "
             '{"positive_pathways": ["..."], "negative_pathways": ["..."], "backfire_check": "...", '
             '"winner": "control" or "treatment", "confidence": <0-1>}'}]
    return _winner_from(_parse(client.chat(msgs, max_tokens=900, temperature=0.0 if seed % 2 else 0.4, seed=seed), ["winner"]))


def _responsiveness(client, case, which, seed):
    # Show ONE version in isolation — no hint a variant exists.
    design = case[which]
    msgs = [{"role": "system", "content":
             "You are an expert forecaster estimating how a target audience responds to a single "
             "product/marketing design, grounded in real behavior."},
            {"role": "user", "content":
             f"Domain: {case['domain']}\nDesign: {design}\nMetric: {case['metric']}\n\n"
             "Imagine the target audience encountering this design. On a 0-100 scale, estimate the "
             "RESPONSIVENESS (higher = more of the audience takes the desired action on the metric), "
             "and name the main reason some of the audience do NOT take the action. Respond ONLY with "
             'JSON: {"responsiveness": <0-100>, "main_friction": "..."}'}]
    o = _parse(client.chat(msgs, max_tokens=300, temperature=0.0 if seed % 2 else 0.4, seed=seed), ["responsiveness"])
    try:
        return float(o["responsiveness"])
    except Exception:
        return None


def arm_per_arm_behavioral(client, case, seed):
    c = _responsiveness(client, case, "control", seed)
    t = _responsiveness(client, case, "treatment", seed + 1)
    if c is None or t is None:
        return None
    return ("control", "treatment", c, t)  # caller aggregates


def arm_placebo_leaner(client, case, seed):
    msgs = [{"role": "system", "content":
             FORECASTER_SYS + " Note: the simpler, lower-friction, less-featured option is frequently "
             "underrated and wins more often than people expect."},
            {"role": "user", "content":
             f"Domain: {case['domain']}\nVersion CONTROL: {case['control']}\n"
             f"Version TREATMENT: {case['treatment']}\nMetric: {case['metric']}\n\n"
             'Which version wins? Respond ONLY with JSON: {"winner": "control" or "treatment"}'}]
    return _winner_from(_parse(client.chat(msgs, max_tokens=300, temperature=0.0 if seed % 2 else 0.4, seed=seed), ["winner"]))


def vote_winner(fn, client, case, k, base_seed):
    votes = [w for w in (fn(client, case, base_seed + i) for i in range(k)) if w]
    return Counter(votes).most_common(1)[0][0] if votes else None


def per_arm_winner(client, case, k, base_seed):
    cs, ts = [], []
    for i in range(k):
        r = arm_per_arm_behavioral(client, case, base_seed + 2 * i)
        if r:
            cs.append(r[2]); ts.append(r[3])
    if not cs:
        return None, None
    mc, mt = sum(cs) / len(cs), sum(ts) / len(ts)
    if abs(mt - mc) < 1.0:  # collapse: isolated scores ~equal → no signal (the founder's concern)
        return "tie", round(mt - mc, 2)
    return ("treatment" if mt > mc else "control"), round(mt - mc, 2)


def score(cases, preds):
    """preds: {id: winner_or_tie_or_None}. Returns acc dicts + 2x2 + more-is-better rate."""
    by = {c["id"]: c for c in cases}
    def acc(ids):
        hits = [int(preds.get(i) == by[i]["real_winner"]) for i in ids if preds.get(i) in ("control", "treatment")]
        scored = [i for i in ids if preds.get(i) in ("control", "treatment")]
        return (sum(hits), len(scored), len(ids) - len(scored))  # correct, scored, unscored(tie/None)
    # more-is-better pick rate: how often it picked the "more/richer" arm.
    # In V4, the "more/richer" arm is TREATMENT for more_won cases and CONTROL for less_won
    # cases (less-won = the simpler arm won, so the richer arm is the loser). Encode per case:
    richer = {**{i: "treatment" for i in MORE_WON}, **{i: "control" for i in LESS_WON}}
    mib = [int(preds.get(i) == richer[i]) for i in richer if preds.get(i) in ("control", "treatment")]
    return {"overall": acc([c["id"] for c in cases]), "less_won": acc(LESS_WON),
            "more_won": acc(MORE_WON), "ambiguous": acc(AMBIG),
            "more_is_better_pick_rate": (sum(mib), len(mib))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cases = json.loads(CASES.read_text())["scored_cases"]
    if args.smoke:
        cases = [c for c in cases if c["id"] in (LESS_WON[0], MORE_WON[0])]
    client = get_chat_client(args.model)

    arms = {"comparative_baseline": arm_comparative_baseline,
            "comparative_ledger": arm_comparative_ledger,
            "placebo_leaner": arm_placebo_leaner}
    results = {}
    for name, fn in arms.items():
        preds = {c["id"]: vote_winner(fn, client, c, args.k, 7000) for c in cases}
        results[name] = {"preds": preds, "score": score(cases, preds)}
        print(f"[{name}] {results[name]['score']}")
    # per-arm behavioral (special aggregation + tie tracking)
    pa_preds, pa_diffs = {}, {}
    for c in cases:
        w, d = per_arm_winner(client, c, args.k, 7000)
        pa_preds[c["id"]] = w
        pa_diffs[c["id"]] = d
    results["per_arm_behavioral"] = {"preds": pa_preds, "diffs": pa_diffs,
                                     "tie_rate": sum(1 for v in pa_preds.values() if v == "tie") / len(pa_preds),
                                     "score": score(cases, pa_preds)}
    print(f"[per_arm_behavioral] tie_rate={results['per_arm_behavioral']['tie_rate']:.2f} {results['per_arm_behavioral']['score']}")

    if not args.smoke:
        (HERE / "method_experiment_result.json").write_text(json.dumps(
            {"model": args.model, "k": args.k, "n_cases": len(cases),
             "less_won": LESS_WON, "more_won": MORE_WON, "results": results}, indent=2))
    # readable summary
    print("\n=== SUMMARY (correct/scored, unscored) ===")
    for name, r in results.items():
        s = r["score"]
        print(f"  {name:24s} less-won {s['less_won'][0]}/{s['less_won'][1]}  "
              f"more-won {s['more_won'][0]}/{s['more_won'][1]}  overall {s['overall'][0]}/{s['overall'][1]}"
              + (f"  tie_rate={r['tie_rate']:.2f}" if "tie_rate" in r else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
