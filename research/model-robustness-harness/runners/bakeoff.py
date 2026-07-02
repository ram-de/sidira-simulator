"""
Method Bake-Off Wave 1 — hand-rolled non-LLM causal/behavior methods vs known-truth A/B tests.
Runs ONCE. No package installs. Imports causal_estimator.py read-only.

Conditions per (method x dataset):
  A        : clean randomized (ATE == ground truth)
  B_obs    : injected selection on a confounder that IS in the covariate set
  B_hidden : same selection, confounder ABLATED (unobserved)

Methods: naive, T-learner, IPW, X-learner, DR/AIPW, negative_control_guard,
         survival-hazard (CookieCats), discrete-choice conditional-logit (Hillstrom).
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from scipy.optimize import minimize

REPO = "/Users/ram/Projects/sidira-simulator/.claude/worktrees/empirical-uplift-spike/research/empirical-uplift-spike"
sys.path.insert(0, REPO)
from causal_estimator import estimate as ce_estimate, negative_control_guard  # read-only reuse

DATA = Path(REPO) / ".data"
HERE = Path(__file__).resolve().parent
BETA = 1.5            # selection strength
SEL_SEED = 20260630   # deterministic injection
NC_SEED = 12345       # constructed negative control

def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))
def sign(x): return "positive" if x > 0 else ("negative" if x < 0 else "zero")

# --------------------------------------------------------------------------- #
# Standalone hand-rolled estimators (operate on a sample + covariate matrix)
# --------------------------------------------------------------------------- #
def naive_ate(T, Y):
    return float(Y[T == 1].mean() - Y[T == 0].mean())

def _outcome_models(Xm, T, Y, binary):
    if binary:
        m1 = LogisticRegression(max_iter=3000).fit(Xm[T == 1], Y[T == 1])
        m0 = LogisticRegression(max_iter=3000).fit(Xm[T == 0], Y[T == 0])
        p1 = lambda X: m1.predict_proba(X)[:, 1]
        p0 = lambda X: m0.predict_proba(X)[:, 1]
    else:
        m1 = LinearRegression().fit(Xm[T == 1], Y[T == 1])
        m0 = LinearRegression().fit(Xm[T == 0], Y[T == 0])
        p1 = lambda X: m1.predict(X); p0 = lambda X: m0.predict(X)
    return p1, p0

def dr_aipw_ate(Xm, T, Y, binary):
    p1, p0 = _outcome_models(Xm, T, Y, binary)
    mu1, mu0 = p1(Xm), p0(Xm)
    e = np.clip(LogisticRegression(max_iter=3000).fit(Xm, T).predict_proba(Xm)[:, 1], 0.02, 0.98)
    psi = (mu1 - mu0) + T * (Y - mu1) / e - (1 - T) * (Y - mu0) / (1 - e)
    return float(psi.mean())

def x_learner_ate(Xm, T, Y, binary):
    p1, p0 = _outcome_models(Xm, T, Y, binary)
    mu0, mu1 = p0(Xm), p1(Xm)
    d1 = Y[T == 1] - mu0[T == 1]          # treated imputed effect
    d0 = mu1[T == 0] - Y[T == 0]          # control imputed effect
    rf = lambda: RandomForestRegressor(n_estimators=200, min_samples_leaf=50, random_state=0)
    tau1 = rf().fit(Xm[T == 1], d1)
    tau0 = rf().fit(Xm[T == 0], d0)
    g = np.clip(RandomForestClassifier(n_estimators=200, min_samples_leaf=50, random_state=0)
                .fit(Xm, T).predict_proba(Xm)[:, 1], 0.02, 0.98)
    cate = g * tau0.predict(Xm) + (1 - g) * tau1.predict(Xm)
    return float(cate.mean())

def survival_hazard_ate(df, T_col, X_cols, sel_mask):
    """Discrete-time logistic hazard, person-period (day1, day7) for Cookie Cats.
    Returns ATE on the S7 (=retention_7) scale: S7(gate40) - S7(gate30). Sign should match retention_7."""
    d = df.loc[sel_mask].reset_index(drop=True)
    # period-1 row for everyone: churn_by_day1 = 1 - retention_1
    p1 = pd.DataFrame({"churn": 1 - d["retention_1"].to_numpy(), "period7": 0.0,
                       "T": d[T_col].to_numpy(float)})
    # period-2 row only for survivors of day1 (retention_1==1): churn_by_day7 = 1 - retention_7
    surv = d[d["retention_1"] == 1]
    p2 = pd.DataFrame({"churn": 1 - surv["retention_7"].to_numpy(), "period7": 1.0,
                       "T": surv[T_col].to_numpy(float)})
    for c in X_cols:
        p1[c] = d[c].to_numpy(float); p2[c] = surv[c].to_numpy(float)
    pp = pd.concat([p1, p2], ignore_index=True)
    feats = ["period7", "T"] + X_cols
    Xh = pp[feats].to_numpy(float)
    mh = LogisticRegression(max_iter=4000).fit(Xh, pp["churn"].to_numpy())
    # predict survival to day7 per arm at the sample-mean covariate, standardized over full sel sample
    Xc = d[X_cols].to_numpy(float)
    def S7(tval):
        n = len(d)
        h1 = mh.predict_proba(np.column_stack([np.zeros(n), np.full(n, tval), Xc]))[:, 1]  # period1 hazard
        h7 = mh.predict_proba(np.column_stack([np.ones(n),  np.full(n, tval), Xc]))[:, 1]  # period2 hazard
        return ((1 - h1) * (1 - h7)).mean()
    return float(S7(1.0) - S7(0.0))

def discrete_choice_logit_ate(Xm, T, Y):
    """Binary-choice (visit vs not) MLE conditional logit via scipy. Features [1, T, X].
    Reduces to logistic regression — reported honestly as NOT a richer choice structure.
    Returns avg marginal effect of T: mean[P(visit|T=1,X) - P(visit|T=0,X)]."""
    n, k = Xm.shape
    Z = np.column_stack([np.ones(n), T.astype(float), Xm])   # [intercept, T, covariates]
    def nll(b):
        p = sigmoid(Z @ b)
        p = np.clip(p, 1e-9, 1 - 1e-9)
        return -np.sum(Y * np.log(p) + (1 - Y) * np.log(1 - p))
    res = minimize(nll, np.zeros(k + 2), method="L-BFGS-B")
    b = res.x
    Z1 = np.column_stack([np.ones(n), np.ones(n), Xm])
    Z0 = np.column_stack([np.ones(n), np.zeros(n), Xm])
    return float((sigmoid(Z1 @ b) - sigmoid(Z0 @ b)).mean())

# --------------------------------------------------------------------------- #
# Dataset loaders + injected selection
# --------------------------------------------------------------------------- #
def load_cookie_cats():
    df = pd.read_csv(DATA / "cookie_cats.csv")
    for m in ("retention_1", "retention_7"):
        df[m] = df[m].astype(str).str.lower().map({"true": 1, "false": 0})
    df = df.dropna(subset=["retention_1", "retention_7", "sum_gamerounds", "version"]).reset_index(drop=True)
    df["T"] = (df["version"] == "gate_40").astype(int)              # treatment = moved gate
    le = np.log1p(df["sum_gamerounds"])
    df["z"] = (le - le.mean()) / le.std()                          # confounder (post-treatment caveat)
    df["noise"] = np.random.default_rng(99).standard_normal(len(df))  # uninformative covariate for B_hidden
    # constructed pre-treatment negative control: trait coupled to engagement, ZERO treatment effect
    rng = np.random.default_rng(NC_SEED)
    df["nc_trait"] = (rng.random(len(df)) < sigmoid(1.0 * df["z"].to_numpy())).astype(int)
    return df

def load_hillstrom():
    df = pd.read_csv(DATA / "hillstrom.csv")
    df = df[df["segment"].isin(["Womens E-Mail", "No E-Mail"])].copy().reset_index(drop=True)
    df["T"] = (df["segment"] == "Womens E-Mail").astype(int)
    lh = np.log1p(df["history"])
    df["loghist"] = lh
    df["h"] = (lh - lh.mean()) / lh.std()                          # confounder = baseline spend
    df["noise"] = np.random.default_rng(99).standard_normal(len(df))
    rng = np.random.default_rng(NC_SEED)
    df["nc_trait"] = (rng.random(len(df)) < sigmoid(1.0 * df["h"].to_numpy())).astype(int)
    return df

def inject_selection(df, conf_col, treat_high=True):
    """Select into treatment on the confounder; T=1 over-samples high (treat_high) confounder, T=0 low."""
    c = df[conf_col].to_numpy()
    T = df["T"].to_numpy()
    s = 1.0 if treat_high else -1.0
    keep_p = np.where(T == 1, sigmoid(s * BETA * c), sigmoid(-s * BETA * c))
    sel = np.random.default_rng(SEL_SEED).random(len(df)) < keep_p
    return sel

# --------------------------------------------------------------------------- #
# Run one dataset across all methods x conditions
# --------------------------------------------------------------------------- #
def run_dataset(name, df, outcome, truth_sign, conf_col, cov_full, cov_hidden,
                nc_controls, treat_high, extra_method):
    binary = set(np.unique(df[outcome].to_numpy(float))) <= {0.0, 1.0}
    sel = inject_selection(df, conf_col, treat_high)
    full_idx = np.ones(len(df), dtype=bool)

    # condition -> (sample mask, covariate columns handed to the method)
    conds = {
        "A":        (full_idx, cov_full),     # clean RCT
        "B_obs":    (sel,      cov_full),     # confounder observed
        "B_hidden": (sel,      cov_hidden),   # confounder ablated
    }

    rows = []
    for cond, (mask, cov) in conds.items():
        d = df.loc[mask].reset_index(drop=True)
        T = d["T"].to_numpy(); Y = d[outcome].to_numpy(float)
        Xm = d[cov].to_numpy(float)

        ce = ce_estimate(d, "T", outcome, cov)   # naive, T-learner, IPW in one shot
        method_vals = {
            "naive_diff_in_means": ce.naive_ate,
            "t_learner": ce.t_learner_ate,
            "ipw": ce.ipw_ate,
            "x_learner": x_learner_ate(Xm, T, Y, binary),
            "dr_aipw": dr_aipw_ate(Xm, T, Y, binary),
        }
        if extra_method == "survival":
            method_vals["survival_hazard"] = survival_hazard_ate(df, "T", cov, mask)
        elif extra_method == "discrete_choice":
            method_vals["discrete_choice_logit"] = discrete_choice_logit_ate(Xm, T, Y)

        for meth, val in method_vals.items():
            rows.append({"dataset": name, "outcome": outcome, "method": meth, "condition": cond,
                         "estimate": round(float(val), 6), "est_sign": sign(val),
                         "recovers_truth": sign(val) == truth_sign, "n": int(mask.sum())})

        # negative-control guard (its own row; covariates = same set the methods got this condition)
        g = negative_control_guard(d, "T", outcome, nc_controls, cov, floor=0.05, ratio=1.5)
        rows.append({"dataset": name, "outcome": outcome, "method": "negative_control_guard",
                     "condition": cond, "estimate": round(float(g.estimate.t_learner_ate), 6),
                     "est_sign": g.estimate.sign_adjusted,
                     "recovers_truth": g.estimate.sign_adjusted == truth_sign,
                     "guard_trips": bool(g.trips), "guard_confidence": g.confidence,
                     "nc_decisive_residual": round(float(g.neg_control_effect), 6),
                     "nc_effects": {k: round(float(v), 6) for k, v in g.neg_control_effects.items()},
                     "guard_reason": g.reason, "n": int(mask.sum())})
    return rows

def main():
    cc = load_cookie_cats()
    hs = load_hillstrom()

    cc_rows = run_dataset(
        "cookie_cats", cc, outcome="retention_7", truth_sign="negative",
        conf_col="z", cov_full=["z"], cov_hidden=["noise"],
        nc_controls=["nc_trait"], treat_high=True, extra_method="survival")

    # supporting: retention_1 (same structure)
    cc_r1 = run_dataset(
        "cookie_cats", cc, outcome="retention_1", truth_sign="negative",
        conf_col="z", cov_full=["z"], cov_hidden=["noise"],
        nc_controls=["nc_trait"], treat_high=True, extra_method=None)

    hs_rows = run_dataset(
        "hillstrom", hs, outcome="visit", truth_sign="positive",
        conf_col="h", cov_full=["recency", "mens", "womens", "newbie", "loghist"],
        cov_hidden=["recency", "mens", "womens", "newbie"],   # ablate loghist (the confounder)
        nc_controls=["nc_trait", "mens", "womens"], treat_high=False, extra_method="discrete_choice")

    hs_conv = run_dataset(
        "hillstrom", hs, outcome="conversion", truth_sign="positive",
        conf_col="h", cov_full=["recency", "mens", "womens", "newbie", "loghist"],
        cov_hidden=["recency", "mens", "womens", "newbie"],
        nc_controls=["nc_trait", "mens", "womens"], treat_high=False, extra_method=None)

    out = {"headline": {"cookie_cats_retention_7": cc_rows, "hillstrom_visit": hs_rows},
           "supporting": {"cookie_cats_retention_1": cc_r1, "hillstrom_conversion": hs_conv},
           "ground_truth": {"cookie_cats_retention_7": "negative", "hillstrom_visit": "positive"},
           "params": {"beta": BETA, "sel_seed": SEL_SEED, "nc_seed": NC_SEED}}
    (HERE / "bakeoff_results.json").write_text(json.dumps(out, indent=2))
    print("wrote bakeoff_results.json")

    # console scoreboard (headline outcomes only)
    for label, rows in (("COOKIE CATS / retention_7 (truth=NEGATIVE)", cc_rows),
                        ("HILLSTROM / visit (truth=POSITIVE)", hs_rows)):
        print(f"\n=== {label} ===")
        print(f"{'method':24s} {'cond':9s} {'estimate':>11s} {'sign?':6s} {'guard':10s}")
        for r in rows:
            g = ("TRIP" if r.get("guard_trips") else ("trust" if "guard_trips" in r else ""))
            ok = "OK" if r["recovers_truth"] else "FLIP"
            print(f"{r['method']:24s} {r['condition']:9s} {r['estimate']:+11.5f} {ok:6s} {g:10s}")

if __name__ == "__main__":
    main()
