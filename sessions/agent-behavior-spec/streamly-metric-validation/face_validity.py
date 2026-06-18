"""STEP B — per-persona face-validity vs the PM's authored expectations.

Joins per_agent_analyses (agent_id -> sentiment) to agent_records (agent_id ->
persona_name + arm), aggregates a per-persona TREATMENT-arm sentiment direction,
and compares to the PM's authored predicted-reaction table in h_001_smart_resume.md.

Face-validity ONLY: matching the PM means the sim shares a human's prior, NOT
evidence of correctness. Streamly is fictional — there is no real A/B outcome.

The v_2 (rebuilt) pack carries 7 GMM-DISCOVERED clusters (P01..P07) whose names
differ from the PM's 6 hand-authored archetypes, so a documented best-effort
cluster->archetype mapping is applied (grounded in the cluster descriptions and
the gen_streamly_feature_store.py segment design). Clusters with no clean
archetype counterpart are reported separately.
"""
from __future__ import annotations
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
RES = json.loads((HERE / "streamly_v11_result.json").read_text())

# PM's authored predicted reactions (h_001_smart_resume.md table).
PM = {
    "alex_binge_marathoner": "STRONG POSITIVE",
    "marco_background_player": "POSITIVE",
    "tess_new_trialer": "SLIGHTLY NEGATIVE",
    "rivka_weekend_movie_night": "NEGATIVE",
    "noor_niche_genre_loyalist": "NEUTRAL",
    "ken_price_sensitive_lapser": "NEUTRAL",
}

# Best-effort v_2 cluster -> PM archetype mapping. Grounded in each cluster's
# description + the gen_streamly_feature_store.py segment that seeded it.
# P02/P04 have no clean PM counterpart (the gen script had no separate reality-
# graze archetype; tess_new_trialer is the closest trial/graze analogue, claimed
# by P04 on tenure+browse; P02 is an extra binge cluster GMM split off).
CLUSTER_TO_ARCHETYPE = {
    "Solo Binge-Laugher On-the-Go": "alex_binge_marathoner",   # heavy mobile binger, autoplay
    "Binge-Focused Serial Devotees": "marco_background_player", # daily-return deep serial / comfort (closest survivor)
    "Mobile Casual Reality Browsers": "tess_new_trialer",       # recently-joined, browse-heavy, not committed
    "Family Movie Night Planners": "rivka_weekend_movie_night", # household, TV, movies, long browse ritual
    "Family Couch Comedy Night": "noor_niche_genre_loyalist",   # WEAK: only remaining 'engaged loyal' cluster; NOT a real niche/subtitle match
    "Lapsed Casual News Grazers": "ken_price_sensitive_lapser", # price-sensitive, cancel-intent, low engagement
    # "Binge-Hooked Solo Streamer" (P02): no clean PM counterpart -> reported separately
}

# 3-band collapse of the PM's 4 labels for direction-matching.
def pm_band(label: str) -> str:
    if "POSITIVE" in label:
        return "positive"
    if "NEGATIVE" in label:
        return "negative"
    return "neutral"


def main():
    recs = RES["agent_records"]            # agent_id -> {persona_id, persona_name, arm}
    analyses = RES["per_agent_analyses"]   # list of {agent_id, sentiment, ...}
    sent_by_agent = {a["agent_id"]: a["sentiment"] for a in analyses}

    # TREATMENT-arm per-persona sentiment tallies (the arm reacting to the change).
    by_persona = defaultdict(lambda: {"positive": 0, "neutral": 0, "negative": 0, "n": 0})
    for aid, meta in recs.items():
        if meta["arm"] != "treatment":
            continue
        s = sent_by_agent.get(aid)
        if s is None:
            continue
        by_persona[meta["persona_name"]]["n"] += 1
        by_persona[meta["persona_name"]][s] += 1

    def direction(tally) -> str:
        pos, neu, neg = tally["positive"], tally["neutral"], tally["negative"]
        if pos == neu == neg == 0:
            return "no-data"
        if pos > neg and pos >= neu:
            return "positive"
        if neg > pos and neg >= neu:
            return "negative"
        return "neutral"

    print("=== TREATMENT-arm per-cluster sentiment (v_2 rebuilt pack) ===")
    cluster_dir = {}
    for name, tally in sorted(by_persona.items()):
        d = direction(tally)
        cluster_dir[name] = d
        print(f"  {name:34} n={tally['n']:>2}  +{tally['positive']} ~{tally['neutral']} -{tally['negative']}  => {d.upper()}")

    print("\n=== Face-validity vs PM authored table (via cluster->archetype mapping) ===")
    matches = 0
    rows = []
    # invert mapping: archetype -> cluster
    arch_to_cluster = {v: k for k, v in CLUSTER_TO_ARCHETYPE.items()}
    for archetype, pm_label in PM.items():
        cluster = arch_to_cluster.get(archetype)
        sim_dir = cluster_dir.get(cluster, "no-data") if cluster else "no-cluster"
        expected = pm_band(pm_label)
        agree = (sim_dir == expected)
        if agree:
            matches += 1
        rows.append((archetype, pm_label, cluster, sim_dir, agree))
        flag = "AGREE" if agree else "DISAGREE"
        print(f"  {archetype:30} PM={pm_label:18} (band={expected:8}) <- {cluster or '(none)':34} sim={sim_dir:9} {flag}")

    print(f"\nFACE-VALIDITY TALLY: {matches}/6 PM archetypes matched (treatment-arm direction).")
    unmapped = [n for n in by_persona if n not in CLUSTER_TO_ARCHETYPE]
    if unmapped:
        print("Unmapped clusters (no clean PM counterpart):")
        for n in unmapped:
            print(f"  {n}: {cluster_dir.get(n)}")

    out = {
        "cluster_directions": cluster_dir,
        "cluster_tallies": dict(by_persona),
        "mapping": CLUSTER_TO_ARCHETYPE,
        "comparison": [
            {"archetype": a, "pm_label": pl, "pm_band": pm_band(pl),
             "cluster": c, "sim_direction": sd, "agree": ag}
            for (a, pl, c, sd, ag) in rows
        ],
        "matches": matches,
        "total": 6,
        "unmapped_clusters": {n: cluster_dir.get(n) for n in unmapped},
    }
    (HERE / "streamly_v11_face_validity.json").write_text(json.dumps(out, indent=2, default=str))
    print("\nwrote streamly_v11_face_validity.json")


if __name__ == "__main__":
    main()
