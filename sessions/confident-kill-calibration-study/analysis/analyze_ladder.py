"""Graded-ladder analysis — where does confident-KILL survive as variants get subtler?

Input: results_ladder.csv. Every treatment is a WEAKER variant (true_direction=-1),
at three flaw intensities: L3 (clearly weak) -> L2 (noticeably weaker) -> L1 (slightly
weaker). A working screen should KILL the weaker variant (drive lift negative) more
often, and more confidently, as the flaw gets more obvious (L3 > L2 > L1).

Reports per level:
  - detection rate   : engine correctly calls it a loser (sign(lift) < 0)
  - median lift      : how negative (how confident)
  - confident-KILL@d : fraction driven past a real kill margin (lift <= -d)
Anchors: L0 = obvious junk (100% / -24 from the junk test), and real optimized
loser = ~chance (from the subtle 600). The ladder fills the middle.
"""
from __future__ import annotations
import sys, csv
import numpy as np

def load(path):
    rows = [r for r in csv.DictReader(open(path)) if (r["signal"] or "").strip()]
    sig = np.array([float(r["signal"]) for r in rows])
    kind = np.array([r.get("kind", "") for r in rows])
    return sig, kind

def main(path):
    sig, kind = load(path)
    print(f"N ladder pairs: {len(sig)}  (every treatment is a weaker variant; correct = KILL it)\n")
    print(f"  {'level':<26} {'n':>4} {'detect(lift<0)':>14} {'median lift':>12} {'KILL@10':>8} {'KILL@20':>8}")
    order = [("L1", "L1 slightly weaker"), ("L2", "L2 noticeably weaker"),
             ("L3", "L3 clearly weak")]
    for key, label in order:
        m = kind == key
        s = sig[m]
        if len(s) == 0:
            print(f"  {label:<26} (none)"); continue
        det = float(np.mean(s < 0))
        k10 = float(np.mean(s <= -10)); k20 = float(np.mean(s <= -20))
        print(f"  {label:<26} {len(s):>4} {det:>14.3f} {np.median(s):>12.1f} {k10:>8.3f} {k20:>8.3f}")
    print(f"\n  anchors — obvious junk: detect~1.00, median ~ -24  |  real optimized loser: detect~0.50 (chance)")
    # overall trend
    for key in ("L3", "L2", "L1"):
        m = kind == key
        if m.sum():
            print(f"  {key}: detect={np.mean(sig[m]<0):.2f}", end="  ")
    print()

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results_ladder.csv")
