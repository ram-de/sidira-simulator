"""
Empirical/causal route on REAL data — Hillstrom (the CLEAN pre-treatment version).

Cookie Cats (realdata_uplift.py) carried one caveat: its only covariate
(sum_gamerounds) is plausibly POST-treatment. Hillstrom fixes that — all 8
covariates (recency, history, mens, womens, newbie, channel, zip, history_segment)
are measured BEFORE the email, so adjusting for them is unimpeachable.

Design SEALED in PREREG_HILLSTROM.json (sha256 in the .sha256 file):
  Contrast: Womens E-Mail (T=1) vs No E-Mail (T=0).  True RCT: email lifts visits
  +4.52pp (treatment wins).
  Part 1 PLUMBING — full-RCT diff-in-means = true effect.
  Part 2 THE TEST — inject selection on baseline spend (email arm over-samples LOW
  spenders -> naive biased toward the WRONG negative sign), then:
     * adjust WITH the confounder (full covariates)      -> should recover +.
     * adjust WITHOUT it (ablated, "unobserved")          -> should FAIL (real-data S2).

Deterministic. Deps: numpy, pandas, scikit-learn.
  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/realdata_hillstrom.py
"""
from __future__ import annotations
import json, urllib.request
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

HERE = Path(__file__).resolve().parent
PREREG = json.loads((HERE / "PREREG_HILLSTROM.json").read_text())
DATA = HERE / ".data" / "hillstrom.csv"
URL = ("http://www.minethatdata.com/"
       "Kevin_Hillstrom_MineThatData_E-MailAnalytics_DataMiningChallenge_2008.03.20.csv")
BETA = PREREG["design"]["beta"]
SEED = PREREG["design"]["seed"]

def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))

def load() -> pd.DataFrame:
    if not DATA.exists():
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(urllib.request.urlopen(URL, timeout=30).read().decode())
    df = pd.read_csv(DATA)
    df = df[df["segment"].isin(["Womens E-Mail", "No E-Mail"])].copy()
    df["T"] = (df["segment"] == "Womens E-Mail").astype(int)
    df["log_history"] = np.log1p(df["history"])
    return df.reset_index(drop=True)

def covariates(df, include_confounder: bool) -> np.ndarray:
    cols = [df["recency"].to_numpy(float),
            df["mens"].to_numpy(float), df["womens"].to_numpy(float),
            df["newbie"].to_numpy(float)]
    if include_confounder:
        cols.append(df["log_history"].to_numpy(float))
    cat = pd.get_dummies(df[["channel", "zip_code"]], drop_first=True).to_numpy(float)
    return np.column_stack(cols + [cat])

def naive(T, Y): return Y[T == 1].mean() - Y[T == 0].mean()

def t_learner(Xs, Ts, Ys, Xfull):
    m1 = LogisticRegression(max_iter=3000).fit(Xs[Ts == 1], Ys[Ts == 1])
    m0 = LogisticRegression(max_iter=3000).fit(Xs[Ts == 0], Ys[Ts == 0])
    return (m1.predict_proba(Xfull)[:, 1] - m0.predict_proba(Xfull)[:, 1]).mean()

def ipw_treatment(Xs, Ts, Ys):
    e = np.clip(LogisticRegression(max_iter=3000).fit(Xs, Ts).predict_proba(Xs)[:, 1], 0.02, 0.98)
    return (Ts * Ys / e - (1 - Ts) * Ys / (1 - e)).mean()

def run(df, metric):
    Y = df[metric].to_numpy(float); T = df["T"].to_numpy()
    true_ate = naive(T, Y)

    h = (df["log_history"].to_numpy() - df["log_history"].mean()) / df["log_history"].std()
    rng = np.random.default_rng(SEED)
    keep_p = np.where(T == 1, sigmoid(-BETA * h), sigmoid(BETA * h))   # email over-samples LOW spenders
    sel = rng.random(len(df)) < keep_p
    Ts, Ys = T[sel], Y[sel]

    def block(include):
        Xfull = covariates(df, include); Xs = Xfull[sel]
        return t_learner(Xs, Ts, Ys, Xfull), ipw_treatment(Xs, Ts, Ys)
    tl_full, ipw_full = block(True)
    tl_abl,  ipw_abl  = block(False)
    n = naive(Ts, Ys)

    ok = lambda e: "RIGHT" if np.sign(e) == np.sign(true_ate) else "WRONG"
    hist_sel = df.loc[sel, "history"].to_numpy()
    return {"metric": metric, "true_ate_pp": round(true_ate*100, 3), "selected_n": int(sel.sum()),
            "hist_treat_vs_control": [round(float(hist_sel[Ts == 1].mean()), 1),
                                      round(float(hist_sel[Ts == 0].mean()), 1)],
            "naive_pp": round(n*100, 3), "naive_sign": ok(n),
            "tl_full_pp": round(tl_full*100, 3), "tl_full_sign": ok(tl_full),
            "ipw_full_pp": round(ipw_full*100, 3), "ipw_full_sign": ok(ipw_full),
            "tl_ablated_pp": round(tl_abl*100, 3), "tl_ablated_sign": ok(tl_abl),
            "ipw_ablated_pp": round(ipw_abl*100, 3), "ipw_ablated_sign": ok(ipw_abl)}

def main():
    df = load()
    print(f"Hillstrom: {len(df)} customers (Womens vs No E-Mail)  |  prereg sealed  |  beta={BETA} seed={SEED}\n")
    results = []
    for metric in ("visit", "conversion"):
        r = run(df, metric); results.append(r)
        print(f"=== {metric}  (TRUE ATE {r['true_ate_pp']:+.2f}pp -> treatment/email wins) ===")
        print(f"  injected sample n={r['selected_n']}  history treat/control = "
              f"${r['hist_treat_vs_control'][0]} / ${r['hist_treat_vs_control'][1]} (imbalanced by design)")
        print(f"  naive diff-in-means (confounded)        {r['naive_pp']:+6.2f}pp   sign:{r['naive_sign']}")
        print(f"  causal, adjust WITH confounder  T-learner{r['tl_full_pp']:+6.2f}pp   sign:{r['tl_full_sign']}")
        print(f"                                  IPW      {r['ipw_full_pp']:+6.2f}pp   sign:{r['ipw_full_sign']}")
        print(f"  causal, WITHOUT confounder (S2) T-learner{r['tl_ablated_pp']:+6.2f}pp   sign:{r['tl_ablated_sign']}")
        print(f"                                  IPW      {r['ipw_ablated_pp']:+6.2f}pp   sign:{r['ipw_ablated_sign']}")
        print()
    out = HERE / "realdata_hillstrom_result.json"
    out.write_text(json.dumps({"dataset": "hillstrom", "n": len(df), "beta": BETA, "seed": SEED,
                               "results": results}, indent=2))
    print(f"wrote {out}")

if __name__ == "__main__":
    main()
