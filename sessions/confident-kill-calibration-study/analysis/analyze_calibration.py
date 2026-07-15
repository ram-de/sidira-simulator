"""Phase 4 — fit the calibrator, sweep KILL threshold + deadzone, produce go/no-go.

Input CSV columns: signal, true_direction (+1/-1), real_lift (signed).

Method:
  - 5-fold CROSS-FIT calibrated P(neg) (never fit & score the same pair).
  - KILL rule (product screen): KILL when calibrated P(negative) >= tau, and,
    with a deadzone, only when |signal| > deadzone (small margins abstain).
  - Raw MARGIN sweep: KILL when signal <= -delta (no fitting — a direct empirical
    read of whether the large-negative-margin region is clean).
  - killed-winner rate (the FN that must stay under the ceiling) = of the pairs we
    KILL, how many were actually the real winner.
  - coverage = of the true losers, how many we confidently KILL.
  - MIN_KILLS support guard: a GO needs enough kills to estimate the rate honestly.
"""
from __future__ import annotations
import sys, csv
import numpy as np

sys.path.insert(0, "/Users/ram/Projects/sidira-simulator/.claude/worktrees/pivot-flag-default/backend")
from sidira_simulator.services.calibration import PlattCalibrator  # noqa: E402

CEILING = 0.05          # trust gate: killed-winner rate must stay <= this
MIN_KILLS = 15          # need >= this many kills before a rate estimate is trustworthy

def load(path):
    rows = [r for r in csv.DictReader(open(path)) if (r["signal"] or "").strip()]
    sig = np.array([float(r["signal"]) for r in rows])
    truth = np.array([int(float(r["true_direction"])) for r in rows])
    real = np.array([float(r["real_lift"]) for r in rows])
    return sig, truth, real

# NOTE: the signal deadzone is applied by the CALLER via an |signal|>deadzone mask at
# KILL time — NOT passed into PlattCalibrator.fit. fit's deadzone acts on observed_lifts
# (~[-0.06,0.04]); a signal-scale deadzone (5,10,...) there would flatten every training
# label and produce a degenerate calibrator (codex P1). So fit always uses deadzone=0.
def crossfit_pneg(sig, real, deadzone=0.0, k=5, seed=13):
    n = len(sig); idx = np.arange(n)
    np.random.default_rng(seed).shuffle(idx)
    folds = np.array_split(idx, k)
    p_neg = np.full(n, np.nan)
    for f in range(k):
        test = folds[f]
        train = np.concatenate([folds[j] for j in range(k) if j != f])
        cal = PlattCalibrator.fit(sig[train].tolist(), real[train].tolist())  # deadzone=0; see note above
        for i in test:
            p_neg[i] = cal.predict(float(sig[i])).p_neg
    return p_neg

def kw_cov(truth, kill):
    k = int(kill.sum())
    if k == 0: return k, None, 0.0
    kw = float(np.mean(truth[kill] == 1))
    cov = float(np.sum((truth == -1) & kill) / max(1, np.sum(truth == -1)))
    return k, kw, cov

def main(path):
    sig, truth, real = load(path)
    n = len(sig)
    raw_sign = np.sign(sig)
    print(f"N pairs                 : {n}")
    print(f"directional accuracy    : {np.mean(raw_sign==truth):.3f}  (raw sign vs truth)")
    print(f"base rate treatment-win : {np.mean(truth==1):.3f}")

    naive = raw_sign < 0
    k, kw, cov = kw_cov(truth, naive)
    print(f"\nBASELINE naive 'sign<0 => KILL': killed {k}/{n}  killed-winner={kw:.3f}  coverage={cov:.3f}")

    # --- 1) RAW MARGIN sweep (no fitting): KILL when signal <= -delta ---
    print(f"\nRAW MARGIN sweep — KILL when engine lift <= -delta (is the big-margin region clean?):")
    print(f"  {'delta':>6} {'killed':>7} {'killed-winner':>14} {'coverage':>9}")
    amax = np.percentile(np.abs(sig), 98)
    best = None  # (label, killed-winner, coverage, killed, param)
    for d in [0, 2, 4, 6, 8, 10, 14, 18, 22, 28]:
        if d > amax: break
        kill = (sig <= -d) & (sig < 0)   # exact-zero signal is an abstention, never a KILL (codex P3)
        k, kw, cov = kw_cov(truth, kill)
        if kw is None:
            print(f"  {d:>6} {0:>7} {'--':>14} {0.0:>9.3f}"); continue
        flag = "  <= ceiling" if (kw <= CEILING and k >= MIN_KILLS) else ""
        print(f"  {d:>6} {k:>7} {kw:>14.3f} {cov:>9.3f}{flag}")
        if kw <= CEILING and k >= MIN_KILLS and (best is None or cov > best[2]):
            best = (f"raw margin delta={d}", kw, cov, k)

    # --- 2) CALIBRATED deadzone x tau grid (cross-fit) ---
    print(f"\nCALIBRATED cross-fit grid — KILL when P(neg)>=tau AND |signal|>deadzone:")
    print(f"  {'deadz':>6} {'tau':>6} {'killed':>7} {'killed-winner':>14} {'coverage':>9}")
    for dz in [0.0, 5.0, 10.0, 15.0, 20.0]:
        p_neg = crossfit_pneg(sig, real, deadzone=dz)
        alive = np.abs(sig) > dz
        for tau in [0.60, 0.80, 0.90, 0.95, 0.99]:
            kill = (p_neg >= tau) & alive
            k, kw, cov = kw_cov(truth, kill)
            if kw is None:
                continue
            flag = "  <= ceiling" if (kw <= CEILING and k >= MIN_KILLS) else ""
            print(f"  {dz:>6.0f} {tau:>6.2f} {k:>7} {kw:>14.3f} {cov:>9.3f}{flag}")
            if kw <= CEILING and k >= MIN_KILLS and (best is None or cov > best[2]):
                best = (f"calibrated deadzone={dz:.0f} tau={tau:.2f}", kw, cov, k)

    print(f"\nGO / NO-GO  (killed-winner ceiling={CEILING:.0%}, min support={MIN_KILLS} kills):")
    if best:
        label, kw, cov, k = best
        print(f"  GO ✅  best clean operating point: {label}")
        print(f"         kills {k}/{n}, killed-winner={kw:.1%} (<= {CEILING:.0%}), coverage={cov:.1%} of true losers.")
    else:
        print(f"  NO-GO ❌  no config (margin OR calibrated+deadzone) keeps killed-winner <= {CEILING:.0%}")
        print(f"           with >= {MIN_KILLS} kills. On this corpus the screen should PASS/ABSTAIN, not KILL.")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "results.csv")
