"""GoodUI reverse-PRD analysis — does REAL product context beat the headline floor,
and can the engine confidently KILL real losing product changes?

Input results_goodui.csv: signal (engine lift), true_direction (+1 change won / -1 lost),
effect (real % effect, signed). The change is always the treatment (real product use).
"""
from __future__ import annotations
import sys, csv, math
import numpy as np
sys.path.insert(0, "/Users/ram/Projects/sidira-simulator/.claude/worktrees/pivot-flag-default/backend")
from sidira_simulator.services.calibration import PlattCalibrator  # noqa

CEIL = 0.05; MIN_KILLS = 8

def load(path):
    rows = [r for r in csv.DictReader(open(path)) if (r["signal"] or "").strip()]
    sig = np.array([float(r["signal"]) for r in rows])
    truth = np.array([int(float(r["true_direction"])) for r in rows])
    # The calibrator only reduces observed lifts to a SIGN, and true_direction is exactly
    # that sign — so we fit on true_direction. This also lets the analysis run from the
    # committed ToS-safe results_goodui_min.csv (no raw GoodUI effect sizes). (codex P2)
    eff = truth.astype(float)
    return sig, truth, eff

def crossfit_pneg(sig, eff, k=5, seed=13):
    n=len(sig); idx=np.arange(n); np.random.default_rng(seed).shuffle(idx)
    folds=np.array_split(idx,k); pn=np.full(n,np.nan)
    for f in range(k):
        te=folds[f]; tr=np.concatenate([folds[j] for j in range(k) if j!=f])
        cal=PlattCalibrator.fit(sig[tr].tolist(), eff[tr].tolist())
        for i in te: pn[i]=cal.predict(float(sig[i])).p_neg
    return pn

def main(path):
    sig, truth, eff = load(path)
    n=len(sig)
    called = sig != 0                       # engine made a directional call
    acc = np.mean(np.sign(sig[called])==truth[called]) if called.sum() else float('nan')
    se = math.sqrt(0.25/max(1,called.sum())); z=(acc-0.5)/se
    print(f"N={n}  winners={int((truth==1).sum())} losers={int((truth==-1).sum())}  "
          f"engine abstained(lift=0)={int((~called).sum())}")
    print(f"\nDIRECTIONAL ACCURACY (change won vs lost), on {int(called.sum())} called:")
    print(f"  accuracy = {acc:.3f}   vs coin flip z={z:.2f}, p={2*(1-0.5*(1+math.erf(abs(z)/math.sqrt(2)))):.3f}")
    print(f"  (Upworthy headline floor was 0.52, NOT significant)")

    # --- confident-KILL on real losing changes ---
    print(f"\nCONFIDENT-KILL — KILL the change when engine lift <= -delta:")
    print(f"  {'delta':>6} {'killed':>7} {'killed-winner':>14} {'coverage(losers killed)':>24}")
    nlose = int((truth==-1).sum()); best=None
    for d in [0,5,10,15,20]:
        kill = (sig <= -d) & (sig < 0); k=int(kill.sum())   # zero signal = abstention, not KILL (codex P3)
        if k==0: print(f"  {d:>6} {0:>7} {'--':>14} {0.0:>24.3f}"); continue
        kw=float(np.mean(truth[kill]==1)); cov=float(np.sum((truth==-1)&kill)/max(1,nlose))
        flag = "  clean" if (kw<=CEIL and k>=MIN_KILLS) else ""
        print(f"  {d:>6} {k:>7} {kw:>14.3f} {cov:>24.3f}{flag}")
        if kw<=CEIL and k>=MIN_KILLS and (best is None or cov>best[2]): best=("margin",d,cov,kw,k)

    # calibrated cross-fit
    pn=crossfit_pneg(sig,eff)
    print(f"\nCALIBRATED cross-fit KILL (P(neg)>=tau):")
    print(f"  {'tau':>6} {'killed':>7} {'killed-winner':>14} {'coverage':>10}")
    for tau in [0.6,0.7,0.8,0.9]:
        kill=pn>=tau; k=int(kill.sum())
        if k==0: continue
        kw=float(np.mean(truth[kill]==1)); cov=float(np.sum((truth==-1)&kill)/max(1,nlose))
        flag="  clean" if (kw<=CEIL and k>=MIN_KILLS) else ""
        print(f"  {tau:>6.2f} {k:>7} {kw:>14.3f} {cov:>10.3f}{flag}")
        if kw<=CEIL and k>=MIN_KILLS and (best is None or cov>best[2]): best=("cal",tau,cov,kw,k)

    print(f"\nGO/NO-GO (killed-winner<= {CEIL:.0%}, >= {MIN_KILLS} kills):")
    if best:
        print(f"  GO ✅  {best[0]}={best[1]}: coverage={best[2]:.1%} of real losers, killed-winner={best[3]:.1%}, kills={best[4]}")
        print(f"  => with REAL product context, the screen confidently kills losing changes.")
    else:
        print(f"  NO-GO ❌  no clean KILL region even with real product context.")

if __name__=="__main__":
    main(sys.argv[1] if len(sys.argv)>1 else "results_goodui.csv")
