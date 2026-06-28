"""
causal_estimator.py — the route-agnostic EMPIRICAL engine core (router foundation).

Generalizes the validated logic from realdata_uplift.py (Cookie Cats) and
realdata_hillstrom.py (Hillstrom) into one reusable function pair the router calls:

  support_check(df, T, Y, X)  -> can we even estimate this empirically?  (no LLM)
  estimate(df, T, Y, X)       -> naive vs causal ATE + honesty diagnostics  (no LLM)

The router's contract: if support_check says supportable -> run estimate and ship the
adjusted ATE with its diagnostics; else hand the hypothesis to the LLM engine, flagged.

No LLM. Deps: numpy, pandas, scikit-learn.  Self-test: run this file (uses the cached
Cookie Cats / Hillstrom CSVs under .data/ if present).
"""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression


@dataclass
class Support:
    supportable: bool
    reasons: list[str]
    n_treat: int
    n_control: int
    overlap_fraction: float        # share of units with propensity in [0.05, 0.95]


@dataclass
class Estimate:
    n: int
    outcome_is_binary: bool
    naive_ate: float
    t_learner_ate: float           # standardization over the full sample (causal)
    ipw_ate: float                 # inverse-propensity weighted (causal)
    naive_adjusted_gap: float      # |naive - t_learner|: how much confounding was corrected
    overlap_fraction: float
    sign_adjusted: str             # 'positive' | 'negative'


def _Xmat(df: pd.DataFrame, X: list[str]) -> np.ndarray:
    return df[X].to_numpy(float)

def _propensity(Xm: np.ndarray, T: np.ndarray) -> np.ndarray:
    return LogisticRegression(max_iter=3000).fit(Xm, T).predict_proba(Xm)[:, 1]


def support_check(df, treatment, outcome, covariates, min_arm=200, min_overlap=0.1) -> Support:
    """Pure data/stats gate: is this hypothesis empirically estimable from the data?"""
    reasons: list[str] = []
    T = df[treatment].to_numpy()
    n_t, n_c = int((T == 1).sum()), int((T == 0).sum())
    if n_t < min_arm or n_c < min_arm:
        reasons.append(f"thin arm(s): treat={n_t}, control={n_c} (< {min_arm})")
    if df[outcome].nunique() < 2:
        reasons.append("outcome has no variation")
    overlap = float("nan")
    if n_t >= 2 and n_c >= 2 and covariates:
        e = _propensity(_Xmat(df, covariates), T)
        overlap = float(np.mean((e > 0.05) & (e < 0.95)))
        if overlap < min_overlap:
            reasons.append(f"poor covariate overlap/positivity ({overlap:.2f} < {min_overlap})")
    return Support(supportable=not reasons, reasons=reasons,
                   n_treat=n_t, n_control=n_c, overlap_fraction=overlap)


def estimate(df, treatment, outcome, covariates) -> Estimate:
    """Naive vs causal ATE (treatment - control) with honesty diagnostics. No LLM."""
    T = df[treatment].to_numpy(); Y = df[outcome].to_numpy(float); Xm = _Xmat(df, covariates)
    binary = set(np.unique(Y)) <= {0.0, 1.0}
    naive = Y[T == 1].mean() - Y[T == 0].mean()

    # T-learner standardization: per-arm outcome model, predict both on the full sample.
    if binary:
        m1 = LogisticRegression(max_iter=3000).fit(Xm[T == 1], Y[T == 1])
        m0 = LogisticRegression(max_iter=3000).fit(Xm[T == 0], Y[T == 0])
        tl = (m1.predict_proba(Xm)[:, 1] - m0.predict_proba(Xm)[:, 1]).mean()
    else:
        from sklearn.linear_model import LinearRegression
        m1 = LinearRegression().fit(Xm[T == 1], Y[T == 1])
        m0 = LinearRegression().fit(Xm[T == 0], Y[T == 0])
        tl = (m1.predict(Xm) - m0.predict(Xm)).mean()

    e = np.clip(_propensity(Xm, T), 0.02, 0.98)
    ipw = (T * Y / e - (1 - T) * Y / (1 - e)).mean()
    overlap = float(np.mean((e > 0.05) & (e < 0.95)))
    return Estimate(n=len(df), outcome_is_binary=binary, naive_ate=naive, t_learner_ate=tl,
                    ipw_ate=ipw, naive_adjusted_gap=abs(naive - tl), overlap_fraction=overlap,
                    sign_adjusted="positive" if tl > 0 else "negative")


# --------------------------------------------------------------------------- #
# Self-test: reproduce the validated real-data results through the generic API
# --------------------------------------------------------------------------- #
def _selftest():
    from pathlib import Path
    d = Path(__file__).resolve().parent / ".data"

    def show(name, sup, est, expect_sign):
        ok = "OK " if est.sign_adjusted == expect_sign else "!! "
        print(f"{ok}{name}: supportable={sup.supportable} overlap={sup.overlap_fraction:.2f} "
              f"| naive={est.naive_ate*100:+.2f}pp t_learner={est.t_learner_ate*100:+.2f}pp "
              f"ipw={est.ipw_ate*100:+.2f}pp (expect {expect_sign})")

    cc = d / "cookie_cats.csv"
    if cc.exists():
        df = pd.read_csv(cc)
        for m in ("retention_1", "retention_7"):
            df[m] = df[m].astype(str).str.lower().map({"true": 1, "false": 0})
        df["T"] = (df["version"] == "gate_40").astype(int)
        df["logeng"] = np.log1p(df["sum_gamerounds"])
        sup = support_check(df, "T", "retention_7", ["logeng"])
        est = estimate(df, "T", "retention_7", ["logeng"])
        show("CookieCats RCT retention_7", sup, est, "negative")   # gate_30 wins
        # degenerate: constant treatment -> not supportable
        df0 = df.assign(T=0)
        print(f"   degenerate (no treatment variation): supportable="
              f"{support_check(df0, 'T', 'retention_7', ['logeng']).supportable}")
    else:
        print("(.data/cookie_cats.csv absent — run realdata_uplift.py once to cache it)")

    hs = d / "hillstrom.csv"
    if hs.exists():
        df = pd.read_csv(hs)
        df = df[df["segment"].isin(["Womens E-Mail", "No E-Mail"])].copy()
        df["T"] = (df["segment"] == "Womens E-Mail").astype(int)
        df["loghist"] = np.log1p(df["history"])
        X = ["recency", "loghist", "mens", "womens", "newbie"]
        sup = support_check(df, "T", "visit", X)
        est = estimate(df, "T", "visit", X)
        show("Hillstrom RCT visit", sup, est, "positive")          # email wins
    else:
        print("(.data/hillstrom.csv absent — run realdata_hillstrom.py once to cache it)")


if __name__ == "__main__":
    _selftest()
