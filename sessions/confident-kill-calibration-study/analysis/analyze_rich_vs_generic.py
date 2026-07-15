"""Rich vs generic persona ablation — paired comparison on the SAME 100 subtle pairs.

New-metric framing: the win condition is NOT higher raw accuracy, it's whether a
CLEAN CONFIDENT-KILL region appears (killed-winner <= ceiling with real coverage),
and whether the engine's confidence tracks correctness better with rich personas.
"""
from __future__ import annotations
import sys, csv
import numpy as np
sys.path.insert(0, "/Users/ram/Projects/sidira-simulator/.claude/worktrees/pivot-flag-default/backend")
from sidira_simulator.services.calibration import PlattCalibrator  # noqa

CEIL = 0.05; MIN_KILLS = 10

def load(path):
    d = {}
    for r in csv.DictReader(open(path)):
        if (r["signal"] or "").strip():
            d[r["test_id"]] = (float(r["signal"]), int(float(r["true_direction"])), float(r["real_lift"]))
    return d

def crossfit_pneg(sig, real, k=5, seed=13):
    n=len(sig); idx=np.arange(n); np.random.default_rng(seed).shuffle(idx)
    folds=np.array_split(idx,k); pn=np.full(n,np.nan)
    for f in range(k):
        te=folds[f]; tr=np.concatenate([folds[j] for j in range(k) if j!=f])
        cal=PlattCalibrator.fit(sig[tr].tolist(), real[tr].tolist())
        for i in te: pn[i]=cal.predict(float(sig[i])).p_neg
    return pn

def report(name, sig, truth, real):
    n=len(sig); acc=np.mean(np.sign(sig)==truth)
    # confidence usefulness: does correctness rise with |lift|? (rank corr proxy)
    order=np.argsort(-np.abs(sig)); corr_top=np.mean((np.sign(sig)==truth)[order[:max(1,n//4)]])
    # best clean KILL region (raw margin + calibrated), min support
    best=None; nbad=np.sum(truth==-1)
    for d in [0,5,10,15,20,25]:
        kill=(sig<=-d)&(sig<0); k=int(kill.sum())   # zero signal = abstention, not KILL
        if k<MIN_KILLS: continue
        kw=np.mean(truth[kill]==1); cov=np.sum((truth==-1)&kill)/max(1,nbad)
        if kw<=CEIL and (best is None or cov>best[1]): best=(f"margin{d}",cov,kw,k)
    pn=crossfit_pneg(sig,real)
    for tau in [0.6,0.8,0.9,0.95]:
        kill=pn>=tau; k=int(kill.sum())
        if k<MIN_KILLS: continue
        kw=np.mean(truth[kill]==1); cov=np.sum((truth==-1)&kill)/max(1,nbad)
        if kw<=CEIL and (best is None or cov>best[1]): best=(f"cal_tau{tau}",cov,kw,k)
    print(f"\n{name}  (n={n})")
    print(f"  raw directional accuracy   : {acc:.3f}")
    print(f"  accuracy in top-quartile |lift| (is confidence useful?): {corr_top:.3f}")
    if best: print(f"  BEST clean KILL region     : {best[0]} -> coverage={best[1]:.1%}, killed-winner={best[2]:.1%}, kills={best[3]}")
    else:    print(f"  BEST clean KILL region     : NONE (no config keeps killed-winner<= {CEIL:.0%} with >= {MIN_KILLS} kills)")
    return acc, best

def main(generic_path, rich_path):
    g=load(generic_path); r=load(rich_path)
    common=[t for t in r if t in g]
    print(f"matched pairs compared: {len(common)}")
    gs=np.array([g[t][0] for t in common]); gt=np.array([g[t][1] for t in common]); gr=np.array([g[t][2] for t in common])
    rs=np.array([r[t][0] for t in common]); rt=np.array([r[t][1] for t in common]); rr=np.array([r[t][2] for t in common])
    ga,gb=report("GENERIC (10 personas)", gs, gt, gr)
    ra,rb=report("RICH (24 behavioral personas, 48 agents/run)", rs, rt, rr)
    print("\nVERDICT:")
    print(f"  raw accuracy: generic {ga:.3f} -> rich {ra:.3f}  (delta {ra-ga:+.3f})")
    gcov = gb[1] if gb else 0.0; rcov = rb[1] if rb else 0.0
    print(f"  clean-KILL coverage: generic {gcov:.1%} -> rich {rcov:.1%}")
    if rb and not gb:
        print("  => RICH created a clean callable region where generic had none — richness HELPS the new metric.")
    elif rb and gb and rcov>gcov+0.05:
        print("  => RICH expanded the callable region — richness helps.")
    else:
        print("  => No meaningful callable region either way — richness does NOT rescue confident-KILL on subtle pairs.")

if __name__=="__main__":
    main(sys.argv[1], sys.argv[2])
