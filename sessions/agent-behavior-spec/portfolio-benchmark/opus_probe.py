"""Opus capability probe (#342): does a stronger model fix product-change direction?

Re-runs the EXACT V4 expansion cases through the same comparative-forecaster prompt
as portfolio_comparative.py, but on claude-opus-4-7 (the strongest registered model).
Self-contained: calls Anthropic directly because opus-4-7 is a reasoning model that
rejects the `temperature` arg the shared AnthropicChat.chat path forces (so it's
~deterministic → k=1). Pre-registered prediction (PREREG_PORTFOLIO_V4_OPUS_PROBE.json):
NO meaningful trick-pile improvement, because the more-is-better failure is a bias, not
a capability gap (the Hillstrom ad-aversion model-comparison found Sonnet==Groq).

    ANTHROPIC_API_KEY=... <venv>/bin/python opus_probe.py
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import anthropic

HERE = Path(__file__).resolve().parent
CASES = HERE / "PORTFOLIO_CASES_EXPANSION_V4.json"
MODEL = "claude-opus-4-7"
_OBJ = re.compile(r"\{[^{}]*\}")

LESS_WON = ["apparel_hide_discount_surfacing", "gift_certificate_expiry_window",
            "time_scarcity_promo_framing", "product_image_hover_zoom"]
MORE_WON = ["homepage_carousel_item_count", "donation_banner_only_word",
            "upload_dropzone_border_button_weight", "vendor_listing_popularity_count"]
AMBIG = ["referral_reward_sender_certainty", "referral_reward_recipient_certainty"]

SYSTEM = ("You are an expert forecaster of how real customers respond to product and "
          "policy changes. You compare two versions and predict which performs better on a "
          "stated metric, grounded in how real audiences actually behave — including when "
          "the intuitive option backfires. Mind the metric's direction (e.g. lower churn is better).")


def predict(client, case) -> str | None:
    user = (f"Domain: {case['domain']}\n"
            f"Version CONTROL: {case['control']}\n"
            f"Version TREATMENT: {case['treatment']}\n"
            f"Metric: {case['metric']}\n\n"
            "Which version performs BETTER on that metric for real customers? Respond ONLY with one "
            'JSON object: {"winner": "control" or "treatment", "confidence": <0-1>, "reason": "<one sentence>"}')
    msg = client.messages.create(model=MODEL, max_tokens=2048, system=SYSTEM,
                                 messages=[{"role": "user", "content": user}])
    raw = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text")
    for cand in reversed(_OBJ.findall(raw)):
        try:
            w = str(json.loads(cand).get("winner", "")).strip().lower()
        except Exception:
            continue
        if w in ("control", "treatment"):
            return w
    m = re.search(r'"?winner"?\s*[:=]\s*"?(control|treatment)', raw, re.I)
    return m.group(1).lower() if m else None


def main() -> int:
    cases = json.loads(CASES.read_text())["scored_cases"]
    client = anthropic.Anthropic()
    rows, by = [], {}
    for c in cases:
        pred = predict(client, c)
        hit = pred == c["real_winner"]
        by[c["id"]] = hit
        rows.append({"id": c["id"], "real": c["real_winner"], "pred": pred, "hit": hit})
        print(f"  {c['id'][:38]:38s} real={c['real_winner']:9s} pred={str(pred):9s} {'OK' if hit else 'X'}")

    def sub(ids):
        h = [by[i] for i in ids if i in by]
        return sum(h), len(h)
    overall = (sum(r["hit"] for r in rows), len(rows))
    lw, mw, am = sub(LESS_WON), sub(MORE_WON), sub(AMBIG)
    print(f"\n=== OPUS-4-7 probe: overall {overall[0]}/{overall[1]} = {overall[0]/overall[1]:.3f} "
          f"(Sonnet was 5/10) ===")
    print(f"  less-won (trick pile): {lw[0]}/{lw[1]}  (Sonnet 1/4)   more-won: {mw[0]}/{mw[1]}   ambiguous: {am[0]}/{am[1]}")
    (HERE / "opus_probe_result.json").write_text(json.dumps(
        {"model": MODEL, "overall": f"{overall[0]}/{overall[1]}",
         "less_won": f"{lw[0]}/{lw[1]}", "more_won": f"{mw[0]}/{mw[1]}", "ambiguous": f"{am[0]}/{am[1]}",
         "sonnet_baseline": {"overall": "5/10", "less_won": "1/4", "more_won": "3/4"},
         "cases": rows}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
