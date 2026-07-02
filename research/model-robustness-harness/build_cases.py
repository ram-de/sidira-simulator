"""Rebuild the sealed AMBDOM + GNCE case set (narrative + truth/grounded/llama signs).

Promoted verbatim-in-logic from the scratchpad `build_cases.py`; the only change is
that file paths are resolved against a `data_dir` (default: ./results) so the harness
is runnable from anywhere without a chdir. The battery itself is NOT rebuilt from
scratch — it is reconstructed from the sealed result JSON + the original llama LLM
logs, exactly as the historical scorecards were.

Each case dict: tag, battery, narrative, llama_sign, truth_sign, grounded_sign.
"""

import json
import os
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.join(HERE, "results")


def s2i(s):
    return {"+": 1, "-": -1, "0": 0}.get(str(s), 0)


def build(data_dir=None):
    """Reconstruct the 59-case battery from sealed results + original llama logs."""
    d = data_dir or DEFAULT_DATA_DIR

    def path(name):
        return os.path.join(d, name)

    cases = []  # each: tag, battery, narrative, llama_sign, truth_sign, grounded_sign

    # AMBDOM
    amb = json.load(open(path("bakeoff_ambdom_results.json")))
    bytag = defaultdict(deque)
    for e in amb["arm_a"]:
        tag = f'{e["cell"]}|pol{e["polarity"]}|s{e["seed"]}'
        bytag[tag].append(e)
    b1 = amb["arm_b1"]
    for line in open(path("ambdom_llm_log.jsonl")):
        L = json.loads(line)
        tag = L["tag"]
        if tag == "B1-cookiecats":
            truth = b1["sign_measured"]
            grounded = b1["sign_pred"]
        elif tag == "B2-streamly":
            truth = "+"        # all measured naive '+'; grounded recovered '+' 10/10
            grounded = "+"
        else:
            e = bytag[tag].popleft()
            truth = e["truth_sign"]
            grounded = e["grounded"]["sign"]
        cases.append(dict(
            tag=tag, battery="AMBDOM", narrative=L["narrative"],
            llama_sign=s2i(L["parsed_sign"]),
            truth_sign=s2i(truth), grounded_sign=s2i(grounded)))

    # GNCE: index-aligned within grouped order
    gn = json.load(open(path("bakeoff_gnce_results.json")))
    glog = [json.loads(x) for x in open(path("gnce_llm_log.jsonl"))]
    assert len(glog) == len(gn["arm_a"]) == 21, (len(glog), len(gn["arm_a"]))
    for L, e in zip(glog, gn["arm_a"]):
        assert L["archetype"] == e["archetype"], (L["archetype"], e["archetype"])
        cases.append(dict(
            tag=f'{e["archetype"]}|s{e["seed"]}', battery="GNCE", narrative=L["narrative"],
            llama_sign=s2i(L["parsed_sign"]),
            truth_sign=s2i(e["truth_sign"]), grounded_sign=s2i(e["grounded"]["sign"])))

    return cases


def cell_type(tag, battery):
    """Slice taxonomy (promoted from run_gpt55.cell_type).

    FLIP      = AMBDOM DISAGREE-* (magnitude-driven flips; the ceiling slice)
    GUESSABLE = AMBDOM AGREE-WIDE + all non-null GNCE archetypes (sign readable from prose)
    NULL      = KNIFE + GNCE NULL (near-zero; excluded from accuracy)
    REAL      = B1-cookiecats + B2-streamly (real/realistic probes)
    """
    p = tag.split("|")[0]
    if p in ("B1-cookiecats", "B2-streamly"):
        return "REAL"
    if p == "KNIFE":
        return "NULL"
    if battery == "GNCE" and p == "NULL":
        return "NULL"
    if p.startswith("DISAGREE-"):
        return "FLIP"
    if p == "AGREE-WIDE":
        return "GUESSABLE"
    if battery == "GNCE":
        return "GUESSABLE"
    return "OTHER"


def is_clean_flip(tag):
    """The load-bearing magnitude-driven-flip slice: clean DISAGREE (WIDE + NARROW)."""
    return tag.startswith("DISAGREE-WIDE") or tag.startswith("DISAGREE-NARROW")


if __name__ == "__main__":
    from collections import Counter
    cs = build()
    print("total cases", len(cs))
    print("battery counts", Counter(c["battery"] for c in cs))
    print("AMBDOM truth dist", Counter(c["truth_sign"] for c in cs if c["battery"] == "AMBDOM"))
    print("GNCE truth dist", Counter(c["truth_sign"] for c in cs if c["battery"] == "GNCE"))
    print("cell_type dist", Counter(cell_type(c["tag"], c["battery"]) for c in cs))
