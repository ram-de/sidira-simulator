"""SYNTHETIC Table B (player_outcomes) generator — MACHINERY TEST ONLY (ticket #444).

⚠️  THIS IS SYNTHETIC DATA. NOT REAL PLAYERS. NOT REAL OUTCOMES. ⚠️

Its only purpose is to exercise the predict -> seal -> score machinery end-to-end
BEFORE any friend or family member has played the game. It emits a Table B shaped
EXACTLY like the real ``player_outcomes`` (player_id, arm, task_id, binary outcome)
plus a sidecar player_id->persona_id assignments map (so the optional player-level
scoring path can run in the test). The moment real players exist, the REAL sealed
Table B replaces this and the scorer is run against THAT.

The synthetic outcomes are drawn so the AUTHOR's bet wins on the 4 genuinely
counter-intuitive items (the arm the author bet, per obvious_priors.json, has a
higher base claim/convert rate) and default_stickiness has the obvious arm win — i.e.
a plausible "the engine should be able to call these" world. Whether the ENGINE
actually called them is decided by score.py against the SEALED predictions; this
generator never sees the engine's predictions.
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Local harness copy of the AUDITED priors (the harness is self-contained and
# depends on nothing under the extracted game app).
OBVIOUS_PRIORS_PATH = HERE / "obvious_priors.json"

# Per-item: the arm we synthesize as the REAL winner + its rate vs the loser's rate.
# Winner = author_bet_arm from obvious_priors.json. Default stickiness's winner is the
# OBVIOUS arm (stickiness:default), so the placebo also gets it right there.
WINNER_RATE = 0.70
LOSER_RATE = 0.40


def main() -> int:
    ap = argparse.ArgumentParser(description="SYNTHETIC Table B generator (machinery test).")
    ap.add_argument("--n", type=int, default=120, help="players per item arm-pair")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--out", default=str(HERE / "synthetic_player_outcomes.json"))
    ap.add_argument("--assignments-out", default=str(HERE / "synthetic_assignments.json"))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    priors = json.loads(OBVIOUS_PRIORS_PATH.read_text())
    rows = []
    assignments = {}
    personas = ["P01", "P02", "P03"]
    pid = 0
    for it in priors["items"]:
        task = it["task_id"]
        arms = it["arms"]
        winner = it["author_bet_arm"]
        for arm in arms:
            rate = WINNER_RATE if arm == winner else LOSER_RATE
            for _ in range(args.n):
                pid += 1
                player_id = f"synthetic-{pid:04d}"
                outcome = 1 if rng.random() < rate else 0
                rows.append({"player_id": player_id, "arm": arm, "task_id": task, "outcome": outcome})
                assignments[player_id] = rng.choice(personas)

    Path(args.out).write_text(json.dumps(
        {"_README": "SYNTHETIC player_outcomes — MACHINERY TEST ONLY, not real players/outcomes.",
         "is_synthetic": True, "rows": rows}, indent=2))
    Path(args.assignments_out).write_text(json.dumps(assignments, indent=2))
    print(f"SYNTHETIC Table B -> {args.out}  ({len(rows)} rows)")
    print(f"SYNTHETIC assignments -> {args.assignments_out}  ({len(assignments)} players)")
    print("  ⚠️  SYNTHETIC DATA for machinery testing only — not real players, not real outcomes.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
