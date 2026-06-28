"""
Empirical/causal route on REAL public data — Cookie Cats (Phase B, real-data).

Upgrades the synthetic spike (uplift_spike.py) to real 90,189-player A/B rows.
Runs the design SEALED in PREREG_REALDATA.json (sha256 in the .sha256 file):

  Part 1 — PLUMBING: full-RCT diff-in-means = the true effect (gate_30 wins,
           ATE_retention_7 = -0.82pp). This MEASURES a real randomized experiment;
           it is not a prediction.
  Part 2 — THE TEST: inject selection bias on engagement so the analyzed sample is
           no longer balanced, then check that causal adjustment recovers the true
           NEGATIVE sign where naive averaging is fooled.

Selection (per prereg): every user keeps their REAL arm + REAL outcome; we only
choose who enters the sample, with keep-prob depending on (arm, engagement). This
is selection-on-an-observable, so adjusting for that observable is valid; the true
target stays the full-RCT effect.

Data: fetched once to .data/cookie_cats.csv (gitignored) from the mirror the
portfolio cites. Deterministic. Deps: numpy, pandas, scikit-learn.
  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/realdata_uplift.py
"""
from __future__ import annotations
import json, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
PREREG = json.loads((HERE / "PREREG_REALDATA.json").read_text())
DATA = HERE / ".data" / "cookie_cats.csv"
MIRROR = ("https://raw.githubusercontent.com/ryanschaub/"
          "Mobile-Games-A-B-Testing-with-Cookie-Cats/master/cookie_cats.csv")
BETA = PREREG["design"]["beta"]
SEED = PREREG["design"]["seed"]

def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

def load() -> pd.DataFrame:
    if not DATA.exists():
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(urllib.request.urlopen(MIRROR, timeout=30).read().decode())
    df = pd.read_csv(DATA)
    for m in ("retention_1", "retention_7"):
        df[m] = df[m].astype(str).str.lower().map({"true": 1, "false": 0})
    df = df.dropna(subset=["retention_1", "retention_7", "sum_gamerounds", "version"])
    df["T"] = (df["version"] == "gate_40").astype(int)   # treatment = moved gate
    df["z"] = (np.log1p(df["sum_gamerounds"]) - np.log1p(df["sum_gamerounds"]).mean()) \
              / np.log1p(df["sum_gamerounds"]).std()
    return df.reset_index(drop=True)

# ----- estimators (Z = engagement features; standardize/weight over full pop) ----- #
def design(z):  # logistic features: z and z^2 (retention is nonlinear in engagement)
    return np.column_stack([z, z ** 2])

def naive(T, Y):
    return Y[T == 1].mean() - Y[T == 0].mean()

def t_learner(Zfull, Zs, Ts, Ys):
    """Fit E[Y|z] per arm on the (selected) sample; standardize over the FULL
    population z to recover the population ATE."""
    m1 = LogisticRegression(max_iter=2000).fit(Zs[Ts == 1], Ys[Ts == 1])
    m0 = LogisticRegression(max_iter=2000).fit(Zs[Ts == 0], Ys[Ts == 0])
    return (m1.predict_proba(Zfull)[:, 1] - m0.predict_proba(Zfull)[:, 1]).mean()

def ipw_selection(keep_p, T, Y):
    """Undo the selection by inverse keep-probability weighting -> population means."""
    w = 1.0 / np.clip(keep_p, 0.02, 1.0)
    def wmean(mask): return np.sum(w[mask] * Y[mask]) / np.sum(w[mask])
    return wmean(T == 1) - wmean(T == 0)

def run(df, metric):
    Y = df[metric].to_numpy(); T = df["T"].to_numpy(); z = df["z"].to_numpy()
    eng = df["sum_gamerounds"].to_numpy()
    true_ate = naive(T, Y)                                   # full RCT (unbiased)

    rng = np.random.default_rng(SEED)
    keep_p = np.where(T == 1, sigmoid(BETA * z), sigmoid(-BETA * z))
    sel = rng.random(len(df)) < keep_p                      # injected selection
    Ts, Ys, Zs = T[sel], Y[sel], design(z[sel])

    n_naive = naive(Ts, Ys)
    tl = t_learner(design(z), Zs, Ts, Ys)
    ipw = ipw_selection(keep_p[sel], Ts, Ys)

    def sign_ok(est): return np.sign(est) == np.sign(true_ate)
    return {
        "metric": metric,
        "true_ate_pp": round(true_ate * 100, 3),
        "selected_n": int(sel.sum()),
        "eng_treat_vs_control": [round(float(eng[sel & (T == 1)].mean()), 1),
                                 round(float(eng[sel & (T == 0)].mean()), 1)],
        "naive_confounded_pp": round(n_naive * 100, 3),
        "t_learner_pp": round(tl * 100, 3),
        "ipw_selection_pp": round(ipw * 100, 3),
        "sign": {"true": "control" if true_ate < 0 else "treatment",
                 "naive": "RIGHT" if sign_ok(n_naive) else "WRONG",
                 "t_learner": "RIGHT" if sign_ok(tl) else "WRONG",
                 "ipw_selection": "RIGHT" if sign_ok(ipw) else "WRONG"},
    }

def main():
    df = load()
    print(f"Cookie Cats: {len(df)} users  |  prereg sha256 sealed  |  beta={BETA} seed={SEED}\n")
    results = []
    for metric in ("retention_7", "retention_1"):
        r = run(df, metric)
        results.append(r)
        print(f"=== {metric}  (TRUE ATE {r['true_ate_pp']:+.2f}pp -> {r['sign']['true']} wins) ===")
        print(f"  injected sample n={r['selected_n']}  engagement treat/control = "
              f"{r['eng_treat_vs_control'][0]} / {r['eng_treat_vs_control'][1]} rounds (imbalanced by design)")
        print(f"  naive diff-in-means (confounded)  {r['naive_confounded_pp']:+6.2f}pp   sign:{r['sign']['naive']}")
        print(f"  T-learner standardization (causal){r['t_learner_pp']:+6.2f}pp   sign:{r['sign']['t_learner']}")
        print(f"  IPW selection-corrected (causal)  {r['ipw_selection_pp']:+6.2f}pp   sign:{r['sign']['ipw_selection']}")
        print()
    out = HERE / "realdata_cookiecats_result.json"
    out.write_text(json.dumps({"dataset": "cookie_cats", "n": len(df), "beta": BETA,
                               "seed": SEED, "results": results}, indent=2))
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
