"""E3-P merge + seal. Concatenates the three assemblers' backlog/truth files,
writes e3p_backlog.json + e3p_truths.json, seals the truths with sha256.

BLINDING: prints ONLY counts and the truths hash — never truth contents.
The orchestrator never opens e3p_truths*.json; only e3p_score.py does,
after predictions are sealed.
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
SOURCES = ["goodui", "industry", "local"]


def main() -> None:
    backlog, truths = [], []
    for src in SOURCES:
        bp = HERE / f"e3p_backlog_{src}.json"
        tp = HERE / f"e3p_truths_{src}.json"
        if not bp.exists() or not tp.exists():
            print(f"MISSING source files for {src}", file=sys.stderr)
            sys.exit(1)
        b = json.loads(bp.read_text())
        t = json.loads(tp.read_text())
        backlog.extend(b)
        truths.extend(t)
        print(f"{src}: {len(b)} backlog cases, {len(t)} truth rows")

    bids = [c["id"] for c in backlog]
    tids = {r["id"] for r in truths}
    if len(bids) != len(set(bids)):
        print("DUPLICATE backlog ids", file=sys.stderr)
        sys.exit(1)
    missing = [i for i in bids if i not in tids]
    if missing:
        print(f"backlog ids without truth rows: {missing}", file=sys.stderr)
        sys.exit(1)

    # leak scan: no outcome vocabulary in the backlog prose/notes
    leak_words = ("won", "lost", "winner", "loser", "lift", "improved",
                  "increased", "decreased", "surprising", "failed",
                  "outperform", "significant")
    leaks = []
    for c in backlog:
        blob = json.dumps({k: v for k, v in c.items()
                           if k not in ("arm_a_tables", "arm_b_tables")}).lower()
        hits = [w for w in leak_words if w in blob]
        if hits:
            leaks.append((c["id"], hits))
    if leaks:
        print(f"LEAK-SCAN WARNINGS (review wording, numbers in tables are fine): {leaks}")

    (HERE / "e3p_backlog.json").write_text(json.dumps(backlog, indent=1))
    truths_text = json.dumps(truths, indent=1)
    (HERE / "e3p_truths.json").write_text(truths_text)
    h = hashlib.sha256(truths_text.encode()).hexdigest()
    (HERE / "e3p_truths.sha256").write_text(h + "  e3p_truths.json\n")

    realistic = sum(1 for c in backlog if c["stratum"] == "realistic")
    curated = sum(1 for c in backlog if c["stratum"] == "curated")
    with_b = sum(1 for c in backlog if c.get("arm_b_tables"))
    with_a = sum(1 for c in backlog if c.get("arm_a_tables"))
    print(f"TOTAL {len(backlog)} (realistic {realistic} / curated {curated}); "
          f"arm_a_tables present {with_a}, arm_b_tables present {with_b}")
    print(f"TRUTHS SEALED sha256={h}")


if __name__ == "__main__":
    main()
