"""End-to-end MACHINERY TEST driver (ticket #444) — predict -> seal -> score on SYNTHETIC outcomes.

⚠️  MACHINERY TEST ONLY. The verdict produced here is on SYNTHETIC outcomes and is
NOT a real validation result. It exists solely to prove the harness produces a
coherent verdict object end-to-end before any real player has played.

Steps:
  1. predict.py --seal   -> runs the FULL engine on the F&F pack, writes PREREG_FF.json
                            (BLIND to outcomes). In a real run the engine-runner commits
                            this BEFORE step 2 exists.
  2. gen_synthetic_outcomes.py -> writes a synthetic Table B + assignments sidecar.
  3. score.py --synthetic -> verifies the pack SHA, scores engine vs placebo, prints the
                            GO/NO-GO verdict, clearly stamped SYNTHETIC.

Run (env must carry ANTHROPIC_API_KEY for step 1):
    set -a && . backend/.env && set +a
    PYTHONPATH=backend backend/.venv/bin/python sessions/ff-validation-game/harness/run_synthetic.py \
        [--population 8] [--model claude-sonnet-4-6] [--skip-predict]

``--skip-predict`` reuses an existing PREREG_FF.json (no LLM calls) so the seal+score
machinery can be exercised offline; it still runs gen-outcomes + score.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
PY = sys.executable


def _run(args: list[str]) -> None:
    print(f"\n$ {' '.join(str(a) for a in args)}")
    subprocess.run([PY, *args], check=True, cwd=str(REPO))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--population", type=int, default=8)
    ap.add_argument("--model", default="claude-sonnet-4-6")
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--skip-predict", action="store_true",
                    help="reuse existing PREREG_FF.json (offline; no LLM calls)")
    args = ap.parse_args()

    print("=" * 78)
    print("  F&F HARNESS END-TO-END MACHINERY TEST  (#444)")
    print("  ⚠️  SYNTHETIC OUTCOMES — NOT A REAL VALIDATION RESULT  ⚠️")
    print("=" * 78)

    predict = HERE / "predict.py"
    gen = HERE / "gen_synthetic_outcomes.py"
    score = HERE / "score.py"
    prereg = HERE / "PREREG_FF.json"
    outcomes = HERE / "synthetic_player_outcomes.json"
    assignments = HERE / "synthetic_assignments.json"

    if not args.skip_predict:
        _run([str(predict), "--seal", "--population", str(args.population), "--model", args.model])
    elif not prereg.exists():
        print("ERROR: --skip-predict given but no PREREG_FF.json exists.")
        return 1

    _run([str(gen), "--n", str(args.n)])
    _run([str(score), "--outcomes", str(outcomes), "--prereg", str(prereg),
          "--assignments", str(assignments), "--synthetic"])

    print("\n" + "=" * 78)
    print("  END-TO-END MACHINERY TEST COMPLETE.")
    print("  The verdict above is on SYNTHETIC outcomes — NOT a real validation result.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
