"""Junk-detection analysis — can the engine confidently KILL obviously-bad variants?

Input: results_junk.csv (signal, true_direction, kind). true_direction=+1 when the
treatment arm is the REAL WINNER, -1 when the treatment arm is the DELIBERATELY-BAD
variant. A correct screen KILLs the bad arm and spares the good one.

Reports overall + per-category:
  - directional accuracy: sign(lift) == truth (good beats junk)
  - confident-KILL: KILL treatment when lift <= -delta;
      killed-winner = of kills, how many were actually the GOOD headline (must be ~0)
      coverage      = of bad-treatment cases, how many confidently killed
  - margin separation: median engine lift when treatment=good vs treatment=bad
"""
from __future__ import annotations
import sys, csv
import numpy as np

def load(path):
    rows = [r for r in csv.DictReader(open(path)) if (r["signal"] or "").strip()]
    sig = np.array([float(r["signal"]) for r in rows])
    truth = np.array([int(float(r["true_direction"])) for r in rows])
    kind = np.array([r.get("kind", "") for r in rows])
    return sig, truth, kind

def block(sig, truth, label):
    n = len(sig)
    if n == 0:
        print(f"  {label:<10} (no rows)"); return
    acc = np.mean(np.sign(sig) == truth)
    good = sig[truth == 1]; bad = sig[truth == -1]
    gmed = np.median(good) if len(good) else float("nan")
    bmed = np.median(bad) if len(bad) else float("nan")
    print(f"  {label:<10} n={n:<4} dir-acc={acc:.3f}   median lift  good={gmed:+.1f}  bad={bmed:+.1f}")

def kill_sweep(sig, truth):
    print(f"\nCONFIDENT-KILL on junk — KILL treatment when lift <= -delta:")
    print(f"  {'delta':>6} {'killed':>7} {'killed-winner':>14} {'coverage(bad killed)':>22}")
    nbad = int(np.sum(truth == -1))
    for d in [0, 5, 10, 15, 20]:
        kill = (sig <= -d) & (sig < 0)   # zero signal = abstention, not KILL
        k = int(kill.sum())
        kw = float(np.mean(truth[kill] == 1)) if k else float("nan")
        cov = float(np.sum((truth == -1) & kill) / max(1, nbad))
        print(f"  {d:>6} {k:>7} {kw:>14.3f} {cov:>22.3f}")

def main(path):
    sig, truth, kind = load(path)
    print(f"N junk pairs: {len(sig)}   base rate treatment=good: {np.mean(truth==1):.3f}")
    print(f"\nOVERALL + per junk category (dir-acc = engine picks good over junk):")
    block(sig, truth, "OVERALL")
    for k in ["empty", "gibberish", "offtopic", "vague"]:
        m = kind == k
        block(sig[m], truth[m], k)
    kill_sweep(sig, truth)

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results_junk.csv")
