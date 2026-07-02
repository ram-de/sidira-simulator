"""
Method Bake-Off Wave 2 — more real RCTs (incl. counter-intuitive) + the HETEROGENEITY test.
Runs ONCE. No package installs (numpy/pandas/sklearn/scipy only). Imports causal_estimator.py
and wave-1 bakeoff.py read-only. Writes only under this dir + the scratchpad.

Part 1: GOTV / Karlan / Orange — ATE sign vs truth in A / B_obs / B_hidden + NC-guard.
Part 2: Karlan match-ratio 3:1-vs-1:1 NULL sub-test.
Part 3: synthetic streaming heterogeneity — per-segment CATE (X-learner/T-learner) vs plain ATE.
"""
from __future__ import annotations
import sys, json, hashlib, os
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
WT = "/Users/ram/Projects/sidira-simulator/.claude/worktrees/empirical-uplift-spike"
SPIKE = f"{WT}/research/empirical-uplift-spike"
REVAL = f"{WT}/research/estimability-theory/revalidation/.data"
sys.path.insert(0, SPIKE)
from causal_estimator import estimate as ce_estimate, negative_control_guard  # read-only
from bakeoff import dr_aipw_ate, x_learner_ate, sign, sigmoid, BETA, SEL_SEED, NC_SEED  # read-only

def std(x):
    x = np.asarray(x, float); return (x - x.mean()) / (x.std() + 1e-12)

def inject_sel(df, conf_col, treat_high=True):
    c = df[conf_col].to_numpy(float); T = df["T"].to_numpy()
    s = 1.0 if treat_high else -1.0
    keep_p = np.where(T == 1, sigmoid(s * BETA * c), sigmoid(-s * BETA * c))
    return np.random.default_rng(SEL_SEED).random(len(df)) < keep_p

# ---------- per-row CATE variants (for the heterogeneity test) ---------------- #
def x_learner_cate_rows(Xm, T, Y, binary):
    if binary:
        m1 = LogisticRegression(max_iter=3000).fit(Xm[T == 1], Y[T == 1])
        m0 = LogisticRegression(max_iter=3000).fit(Xm[T == 0], Y[T == 0])
        mu1, mu0 = m1.predict_proba(Xm)[:, 1], m0.predict_proba(Xm)[:, 1]
    else:
        m1 = LinearRegression().fit(Xm[T == 1], Y[T == 1])
        m0 = LinearRegression().fit(Xm[T == 0], Y[T == 0])
        mu1, mu0 = m1.predict(Xm), m0.predict(Xm)
    d1 = Y[T == 1] - mu0[T == 1]; d0 = mu1[T == 0] - Y[T == 0]
    rf = lambda: RandomForestRegressor(n_estimators=200, min_samples_leaf=50, random_state=0)
    tau1 = rf().fit(Xm[T == 1], d1); tau0 = rf().fit(Xm[T == 0], d0)
    g = np.clip(RandomForestClassifier(n_estimators=200, min_samples_leaf=50, random_state=0)
                .fit(Xm, T).predict_proba(Xm)[:, 1], 0.02, 0.98)
    return g * tau0.predict(Xm) + (1 - g) * tau1.predict(Xm)

def t_learner_cate_rows(Xm, T, Y, binary):
    if binary:
        m1 = LogisticRegression(max_iter=3000).fit(Xm[T == 1], Y[T == 1])
        m0 = LogisticRegression(max_iter=3000).fit(Xm[T == 0], Y[T == 0])
        return m1.predict_proba(Xm)[:, 1] - m0.predict_proba(Xm)[:, 1]
    m1 = LinearRegression().fit(Xm[T == 1], Y[T == 1])
    m0 = LinearRegression().fit(Xm[T == 0], Y[T == 0])
    return m1.predict(Xm) - m0.predict(Xm)

# --------------------------------------------------------------------------- #
# Part 1: real RCT under A / B_obs / B_hidden
# --------------------------------------------------------------------------- #
def run_real(name, df, outcome, truth_sign, cov_full, cov_hidden, nc_controls,
             conf_col="z", treat_high=True):
    binary = set(np.unique(df[outcome].to_numpy(float))) <= {0.0, 1.0}
    sel = inject_sel(df, conf_col, treat_high)
    conds = {"A": (np.ones(len(df), bool), cov_full),
             "B_obs": (sel, cov_full), "B_hidden": (sel, cov_hidden)}
    rows = []
    for cond, (mask, cov) in conds.items():
        d = df.loc[mask].reset_index(drop=True)
        T = d["T"].to_numpy(); Y = d[outcome].to_numpy(float); Xm = d[cov].to_numpy(float)
        ce = ce_estimate(d, "T", outcome, cov)
        vals = {"naive_diff_in_means": ce.naive_ate, "t_learner": ce.t_learner_ate,
                "ipw": ce.ipw_ate, "x_learner": x_learner_ate(Xm, T, Y, binary),
                "dr_aipw": dr_aipw_ate(Xm, T, Y, binary)}
        for meth, v in vals.items():
            rows.append(dict(dataset=name, outcome=outcome, method=meth, condition=cond,
                             estimate=round(float(v), 6), est_sign=sign(v),
                             recovers_truth=sign(v) == truth_sign, n=int(mask.sum())))
        g = negative_control_guard(d, "T", outcome, nc_controls, cov, floor=0.05, ratio=1.5)
        rows.append(dict(dataset=name, outcome=outcome, method="negative_control_guard",
                         condition=cond, estimate=round(float(g.estimate.t_learner_ate), 6),
                         est_sign=g.estimate.sign_adjusted,
                         recovers_truth=g.estimate.sign_adjusted == truth_sign,
                         guard_trips=bool(g.trips), guard_confidence=g.confidence,
                         nc_decisive_residual=round(float(g.neg_control_effect), 6),
                         nc_effects={k: round(float(v), 6) for k, v in g.neg_control_effects.items()},
                         guard_reason=g.reason, n=int(mask.sum())))
    return rows

# ---- loaders ---------------------------------------------------------------- #
def load_gotv():
    df = pd.read_csv(f"{REVAL}/gotv_social.csv")
    df = df[df["messages"].isin(["Neighbors", "Control"])].copy().reset_index(drop=True)
    df["T"] = (df["messages"] == "Neighbors").astype(int)
    df["age"] = 2006 - df["yearofbirth"].astype(float)
    df["male"] = (df["sex"].astype(str).str.lower() == "male").astype(int)
    df["hhsize"] = df["hhsize"].astype(float)
    # seeded 50k subsample, keep both arms
    rng = np.random.default_rng(7)
    idx = rng.permutation(len(df))[:50000]
    df = df.iloc[idx].reset_index(drop=True)
    df["z"] = std(df["age"]); df["noise"] = np.random.default_rng(99).standard_normal(len(df))
    df["primary2004"] = df["primary2004"].astype(int)
    df["nc_z"] = (np.random.default_rng(NC_SEED).random(len(df)) < sigmoid(1.0 * df["z"].to_numpy())).astype(int)
    return df

def load_karlan():
    df = pd.read_stata(f"{REVAL}/karlan_aer.dta")
    df["T"] = df["treatment"].astype(int); df["gave"] = df["gave"].astype(float)
    cov = ["freq", "years", "dormant", "female", "couple", "pwhite", "mrm2"]
    for c in cov:
        df[c] = pd.to_numeric(df[c], errors="coerce")
        df[c] = df[c].fillna(df[c].median())
    df = df.dropna(subset=["T", "gave"]).reset_index(drop=True)
    df["z"] = std(df["freq"]); df["noise"] = np.random.default_rng(99).standard_normal(len(df))
    hpa = pd.to_numeric(df["hpa"], errors="coerce").fillna(pd.to_numeric(df["hpa"], errors="coerce").median())
    df["hpa_hi"] = (hpa > hpa.median()).astype(int)
    df["nc_z"] = (np.random.default_rng(NC_SEED).random(len(df)) < sigmoid(1.0 * df["z"].to_numpy())).astype(int)
    return df, cov

def load_orange():
    df = pd.read_csv(f"{REVAL}/orange_belgium.csv")
    df["T"] = df["t"].astype(int); df["y"] = df["y"].astype(float)
    pcs = [c for c in df.columns if c.startswith("PC")]
    var = df[pcs].var().sort_values(ascending=False)
    top = list(var.index[:15])                     # top-15 PCs by variance
    df["z"] = std(df[top[0]]); df["noise"] = np.random.default_rng(99).standard_normal(len(df))
    df["nc_z"] = (np.random.default_rng(NC_SEED).random(len(df)) < sigmoid(1.0 * df["z"].to_numpy())).astype(int)
    return df, top

# --------------------------------------------------------------------------- #
# Part 2: Karlan match-ratio null sub-test (within treated: 3:1 vs 1:1)
# --------------------------------------------------------------------------- #
def karlan_match_ratio(df_full):
    df = df_full.copy()
    r = df["ratio"].astype(str)
    sub = df[r.isin(["1", "3"])].copy().reset_index(drop=True)
    sub["T"] = (sub["ratio"].astype(str) == "3").astype(int)   # 3:1 vs 1:1
    cov = ["freq", "years", "dormant", "female", "couple", "pwhite", "mrm2"]
    Y = sub["gave"].to_numpy(float); T = sub["T"].to_numpy(); Xm = sub[cov].to_numpy(float)
    ce = ce_estimate(sub, "T", "gave", cov)
    vals = {"naive_diff_in_means": ce.naive_ate, "t_learner": ce.t_learner_ate, "ipw": ce.ipw_ate,
            "x_learner": x_learner_ate(Xm, T, Y, True), "dr_aipw": dr_aipw_ate(Xm, T, Y, True)}
    BAND = 0.005
    out = []
    for m, v in vals.items():
        out.append(dict(method=m, estimate=round(float(v), 6),
                        calls_null=bool(abs(v) < BAND), n=len(sub),
                        n_1to1=int((T == 0).sum()), n_3to1=int((T == 1).sum())))
    return out, BAND

# --------------------------------------------------------------------------- #
# Part 3: heterogeneity (synthetic streaming)
# --------------------------------------------------------------------------- #
def reconstruct_activity(df):
    plays = df["plays_28d"].to_numpy(float); watch = df["watch_minutes_28d"].to_numpy(float)
    completion = df["completion_rate"].to_numpy(float); session = df["avg_session_min"].to_numpy(float)
    a_raw = np.log1p(plays) + np.log1p(watch) / 2 + completion + session / 10
    return std(a_raw)

def run_hetero(tag, csv_path, true_casual="positive", true_power="negative"):
    df = pd.read_csv(csv_path)
    covs = ["tenure_days", "plays_28d", "watch_minutes_28d", "avg_session_min",
            "titles_started_28d", "completion_rate", "plan_tier", "device_mobile",
            "region_code", "notifications_on"]
    T = df["got_feature"].to_numpy(); Y = df["outcome"].to_numpy(float); Xm = df[covs].to_numpy(float)
    binary = set(np.unique(Y)) <= {0.0, 1.0}
    a = reconstruct_activity(df)
    seg = np.where(a < 0, "casual_low_usage", "power_high_usage")   # design boundary a<0

    global_naive = float(Y[T == 1].mean() - Y[T == 0].mean())
    xc = x_learner_cate_rows(Xm, T, Y, binary)
    tc = t_learner_cate_rows(Xm, T, Y, binary)

    truth = {"casual_low_usage": true_casual, "power_high_usage": true_power}
    seg_rows = []
    for s in ("casual_low_usage", "power_high_usage"):
        m = seg == s
        naive_s = float(Y[m & (T == 1)].mean() - Y[m & (T == 0)].mean())
        xl_s = float(xc[m].mean()); tl_s = float(tc[m].mean())
        seg_rows.append(dict(segment=s, n=int(m.sum()), true_sign=truth[s],
                             plain_global_ate=round(global_naive, 5), plain_global_sign=sign(global_naive),
                             naive_within=round(naive_s, 5), naive_within_sign=sign(naive_s),
                             naive_within_recovers=sign(naive_s) == truth[s],
                             x_learner_cate=round(xl_s, 5), x_learner_sign=sign(xl_s),
                             x_learner_recovers=sign(xl_s) == truth[s],
                             t_learner_cate=round(tl_s, 5), t_learner_sign=sign(tl_s),
                             t_learner_recovers=sign(tl_s) == truth[s],
                             plain_ate_recovers=sign(global_naive) == truth[s]))

    # plan_tier negative-control segmentation (no true heterogeneity by construction)
    plan_rows = []
    for pt in sorted(df["plan_tier"].unique()):
        m = df["plan_tier"].to_numpy() == pt
        plan_rows.append(dict(plan_tier=int(pt), n=int(m.sum()),
                              x_learner_cate=round(float(xc[m].mean()), 5),
                              x_learner_sign=sign(float(xc[m].mean()))))

    # NC-guard on this regime (confounding observed -> expect trust)
    g = negative_control_guard(df, "got_feature", "outcome", ["neg_control"], covs, floor=0.05, ratio=1.5)
    guard = dict(trips=bool(g.trips), confidence=g.confidence,
                 nc_residual=round(float(g.neg_control_effect), 6), reason=g.reason)
    return dict(tag=tag, outcome_type=("binary" if binary else "continuous"),
                global_naive_ate=round(global_naive, 5), segments=seg_rows,
                plan_tier_control=plan_rows, guard=guard)

# NC-guard sweep across all 10 streaming datasets (abstain behavior) ----------- #
def streaming_guard_sweep(version):
    sealed = json.loads((Path.home() / f"streamly_challenge_{version}_SEALED.json").read_text())
    reg = {d["filename"]: d for d in sealed["datasets"]}
    ddir = Path(SPIKE) / ".data" / f"synthetic_streamly_{version}"
    covs = ["tenure_days", "plays_28d", "watch_minutes_28d", "avg_session_min",
            "titles_started_28d", "completion_rate", "plan_tier", "device_mobile",
            "region_code", "notifications_on"]
    out = []
    for fn in sorted(reg):
        df = pd.read_csv(ddir / fn)
        g = negative_control_guard(df, "got_feature", "outcome", ["neg_control"], covs, floor=0.05, ratio=1.5)
        out.append(dict(version=version, file=fn, regime=reg[fn]["regime"],
                        nc_unobserved=reg[fn]["nc_unobserved"], true_sign=reg[fn]["true_sign"],
                        guard_abstains=bool(g.trips), nc_residual=round(float(g.neg_control_effect), 6)))
    return out

# --------------------------------------------------------------------------- #
def main():
    res = {}
    print("loading real RCTs...")
    gotv = load_gotv()
    karlan, kcov = load_karlan()
    orange, ocov = load_orange()

    print("GOTV...")
    res["gotv"] = run_real("gotv", gotv, "primary2006", "positive",
                           cov_full=["z", "male", "hhsize"], cov_hidden=["noise", "male", "hhsize"],
                           nc_controls=["primary2004", "nc_z"], conf_col="z", treat_high=True)
    print("Karlan...")
    res["karlan"] = run_real("karlan", karlan, "gave", "positive",
                             cov_full=["z"] + kcov, cov_hidden=["noise"] + kcov,
                             nc_controls=["hpa_hi", "nc_z"], conf_col="z", treat_high=True)
    print("Orange...")
    res["orange"] = run_real("orange", orange, "y", "positive",
                             cov_full=["z"] + ocov, cov_hidden=["noise"] + ocov,
                             nc_controls=["nc_z"], conf_col="z", treat_high=True)
    print("Karlan match-ratio null...")
    mr, band = karlan_match_ratio(karlan)
    res["karlan_match_ratio"] = {"band": band, "rows": mr}

    print("heterogeneity v2/ds06 + v3/ds09...")
    res["hetero"] = [run_hetero("v2/dataset_06", f"{SPIKE}/.data/synthetic_streamly_v2/dataset_06.csv"),
                     run_hetero("v3/dataset_09", f"{SPIKE}/.data/synthetic_streamly_v3/dataset_09.csv")]
    print("streaming guard sweep...")
    res["streaming_guard_sweep"] = streaming_guard_sweep("v2") + streaming_guard_sweep("v3")

    (HERE / "bakeoff_wave2_results.json").write_text(json.dumps(res, indent=2))
    print("wrote bakeoff_wave2_results.json")

if __name__ == "__main__":
    main()
