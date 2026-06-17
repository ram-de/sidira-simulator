#!/usr/bin/env python3
"""Per-subset accuracy for the v3 portfolio, using a BLIND, pre-registered
stimulus-type classification (substantive-deliberative=A vs micro/aesthetic=B).

The classification is produced by an independent agent blind to the sim's
per-case correctness, then sealed with a canonical SHA-256 BEFORE this script
is run. This script only joins that frozen classification to the per-case
correctness already on record in portfolio_results_v3.txt — it introduces no
new researcher degrees of freedom.

Usage: python3 subset_score.py <classification.json>
"""
import json
import sys
import hashlib

# Per-case correctness as recorded in portfolio_results_v3.txt (deterministic,
# seed=42). True = sim predicted the real winner's direction correctly.
CORRECT = {
    "cookiecats_gate_move": True,
    "duolingo_weekend_amulet": True,
    "msn_realestate_widget": True,
    "msn_homepage_extra_offers": True,
    "tinkoff_defer_passport": True,
    "office_online_redesign": False,
    "cxl_form_fields_9_to_6": False,
    "multistep_form_3_vs_6": False,
    "amazon_credit_card_offer_relocation": True,
    "etsy_infinite_scroll_search": True,
    "linkedin_volunteer_section_value_copy": False,
    "msn_hotmail_link_new_tab": False,
    "msn_support_personalized_answers": False,
    "pinterest_signup_color_scheme": False,
    "price_com_hk_price_ranges": False,
}


def canonical_sha256(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(blob).hexdigest()


def main(path: str) -> None:
    with open(path) as fh:
        cls = json.load(fh)

    print(f"classification canonical SHA-256: {canonical_sha256(cls)}")
    print()

    by_class = {"A": [], "B": []}
    for row in cls["classifications"]:
        cid = row["id"]
        klass = row["class"]
        if cid not in CORRECT:
            raise SystemExit(f"unknown case id in classification: {cid}")
        by_class[klass].append((cid, CORRECT[cid]))

    missing = set(CORRECT) - {r["id"] for r in cls["classifications"]}
    if missing:
        raise SystemExit(f"classification missing cases: {sorted(missing)}")

    labels = {
        "A": "substantive_deliberative",
        "B": "subtle_micro_aesthetic",
    }
    for klass in ("A", "B"):
        rows = by_class[klass]
        n = len(rows)
        hits = sum(1 for _, ok in rows if ok)
        acc = hits / n if n else float("nan")
        print(f"== CLASS {klass} ({labels[klass]}): {hits}/{n} = {acc:.3f} ==")
        for cid, ok in sorted(rows):
            print(f"   {'✓' if ok else '✗'} {cid}")
        print()

    total_hits = sum(1 for _, ok in CORRECT.items() if ok)
    print(f"overall (sanity): {total_hits}/{len(CORRECT)} = {total_hits/len(CORRECT):.3f}  (must equal 7/15=0.467)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: python3 subset_score.py <classification.json>")
    main(sys.argv[1])
