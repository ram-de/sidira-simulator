"""Persona-panel behavioral simulation (#342) — the final untested council lever.

Instead of asking a forecaster "which version is better?" (verdict → prior-echo) or
estimating a population responsiveness in isolation (the arm that failed 0/4), this drops
a panel of HETEROGENEOUS personas into each version SEPARATELY (between-subjects, never
told a variant exists) and has each ENACT a decision — narrate what they notice/feel/do,
then a terminal ACTION (convert / defer / abandon). Direction = arithmetic on the
aggregated conversion rate, never an opinion.

The bet: counter-intuitive A/B winners come from a behavioral mechanism in the TAIL
(procrastinators defer under a long deadline; skeptics bounce off a countdown; the
easily-overwhelmed abandon under added load). A trait-diverse panel that ENACTS can surface
that; a single judgment cannot. Discipline: personas carry only WHO THEY ARE — no mechanism
direction is hand-fed (that would be a disguised pro-simpler thumb).

    PYTHONPATH=backend <venv>/bin/python persona_panel_sim.py [--model claude-sonnet-4-6]
"""
from __future__ import annotations

import argparse
import json
import re
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

# Trait-diverse consumer panel. Each profile emphasizes BEHAVIORAL tendencies (patience,
# skepticism, attention budget, deal/quality orientation) — NOT which way any feature cuts.
# Held identical across every case and arm.
PANEL = [
    "an impulsive, deal-hunting mobile shopper with little patience who decides fast and loves a bargain",
    "a deliberate, skeptical researcher who reads everything carefully on desktop and distrusts marketing",
    "a busy parent who is chronically short on time, means to do things 'later', and rarely gets back to them",
    "a bargain-distrusting quality-seeker who reads discounts as a red flag about quality",
    "a loyal, trusting habitual buyer who doesn't overthink and just completes familiar tasks",
    "an anxious comparison-shopper who is easily overwhelmed by options and second-guesses decisions",
    "a leisurely, time-rich browser with lots of patience and no urgency",
    "a price-insensitive premium buyer who cares about quality, not savings, and ignores promotions",
    "a heavily distracted multitasker with a tiny attention span who abandons anything that takes effort",
    "a pressure-averse, autonomy-valuing person who reacts badly to urgency tactics and feeling pushed",
    "a novelty-seeking early adopter who enjoys rich, feature-packed experiences",
    "a minimalist who is put off by clutter and prefers the simplest, cleanest option",
]

ENACT_SYS = ("You roleplay a specific consumer reacting to a single real product/marketing "
             "experience, as that person genuinely would — not as a marketer or critic. Be honest "
             "about hesitation, friction, distraction, distrust, and procrastination.")


def enact(client, persona, case, design, seed):
    user = (f"You are {persona}.\n\n"
            f"Context: {case['domain']}.\n"
            f"You encounter this:\n{design}\n\n"
            f"The action in question (the metric) is: {case['metric']}.\n\n"
            "In first person, briefly narrate what you notice, think, and feel — then decide what you "
            "actually do RIGHT NOW. Be realistic for who you are. End with exactly one line:\n"
            'JSON: {"action": "convert" | "defer" | "abandon", "reason": "<short>"}\n'
            "convert = you take the action now; defer = you put it off for later; abandon = you leave without acting.")
    raw = client.chat([{"role": "system", "content": ENACT_SYS}, {"role": "user", "content": user}],
                      max_tokens=500, temperature=0.0, seed=seed)
    for cand in reversed(_OBJ.findall(raw)):
        try:
            a = str(json.loads(cand).get("action", "")).strip().lower()
        except Exception:
            continue
        if a in ("convert", "defer", "abandon"):
            return a
    m = re.search(r'"?action"?\s*[:=]\s*"?(convert|defer|abandon)', raw, re.I)
    return m.group(1).lower() if m else None


def arm_rate(client, case, which, seed0):
    """Conversion rate over the panel for one version in isolation. convert=1, else 0."""
    acts = []
    for i, p in enumerate(PANEL):
        a = enact(client, p, case, case[which], seed0 + i)
        if a:
            acts.append(1 if a == "convert" else 0)
    if not acts:
        return None, {}
    rate = sum(acts) / len(acts)
    return rate, {"n": len(acts), "convert": sum(acts)}


def score(preds, cases):
    by = {c["id"]: c for c in cases}
    def acc(ids):
        sc = [i for i in ids if preds.get(i) in ("control", "treatment")]
        return sum(int(preds[i] == by[i]["real_winner"]) for i in sc), len(sc), len(ids) - len(sc)
    richer = {**{i: "treatment" for i in MORE_WON}, **{i: "control" for i in LESS_WON}}
    mib = [int(preds.get(i) == richer[i]) for i in richer if preds.get(i) in ("control", "treatment")]
    return {"overall": acc([c["id"] for c in cases]), "less_won": acc(LESS_WON),
            "more_won": acc(MORE_WON), "ambiguous": acc(AMBIG),
            "more_is_better_pick_rate": (sum(mib), len(mib))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--smoke", action="store_true")
    args = ap.parse_args()
    cases = json.loads(CASES.read_text())["scored_cases"]
    if args.smoke:
        cases = [c for c in cases if c["id"] in (LESS_WON[0], MORE_WON[0])]
    client = get_chat_client(args.model)
    preds, detail = {}, {}
    for c in cases:
        rc, dc = arm_rate(client, c, "control", 8000)
        rt, dt = arm_rate(client, c, "treatment", 8500)
        if rc is None or rt is None:
            preds[c["id"]] = None
        elif abs(rt - rc) < 1e-9:
            preds[c["id"]] = "tie"
        else:
            preds[c["id"]] = "treatment" if rt > rc else "control"
        detail[c["id"]] = {"control_rate": rc, "treatment_rate": rt, "pred": preds[c["id"]],
                           "real": c["real_winner"], "ctrl": dc, "treat": dt}
        print(f"  {c['id'][:34]:34s} ctrl={rc} treat={rt} pred={preds[c['id']]} real={c['real_winner']}")
    s = score(preds, cases)
    print(f"\n=== PERSONA-PANEL SIM ({len(PANEL)} personas) ===")
    print(f"  less-won {s['less_won'][0]}/{s['less_won'][1]}  more-won {s['more_won'][0]}/{s['more_won'][1]}  "
          f"overall {s['overall'][0]}/{s['overall'][1]}  MIB {s['more_is_better_pick_rate'][0]}/{s['more_is_better_pick_rate'][1]}")
    print("  baseline (comparative forecaster): less 2/4, more 2/4, overall 5/10")
    if not args.smoke:
        (HERE / "persona_panel_sim_result.json").write_text(json.dumps(
            {"model": args.model, "panel_size": len(PANEL), "score": s, "detail": detail}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
