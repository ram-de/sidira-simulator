"""
Method Bake-Off Wave 3 — AUTO-DISCOVERY of the effect-modifier.

Can a non-LLM method discover WHICH covariate the treatment effect concentrates/flips on,
WITHOUT being told, and report NO modifier on homogeneous/true-null data?

No installs (numpy/pandas/sklearn only). Reuses wave-1/2 helpers + causal_estimator read-only.
Writes only under this dir. Run ONCE.
"""
from __future__ import annotations
import sys, json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.tree import DecisionTreeRegressor

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
WT = "/Users/ram/Projects/sidira-simulator/.claude/worktrees/empirical-uplift-spike"
SPIKE = f"{WT}/research/empirical-uplift-spike"
sys.path.insert(0, SPIKE)
from bakeoff import sign, sigmoid, BETA, SEL_SEED  # read-only

RNG = np.random.default_rng(20260630)
KPLACEBO = 8
NSUB = 6000
RF_KW = dict(n_estimators=80, min_samples_leaf=120, random_state=0, n_jobs=-1)
RATIO = 1.5
USAGE = {"plays_28d", "watch_minutes_28d", "avg_session_min", "completion_rate", "titles_started_28d"}
STREAM_COVS = ["tenure_days", "plays_28d", "watch_minutes_28d", "avg_session_min",
               "titles_started_28d", "completion_rate", "plan_tier", "device_mobile",
               "region_code", "notifications_on"]

def std(x):
    x = np.asarray(x, float); return (x - x.mean()) / (x.std() + 1e-12)

def subsample(df, n=NSUB):
    if len(df) <= n:
        return df.reset_index(drop=True)
    idx = np.random.default_rng(7).permutation(len(df))[:n]
    return df.iloc[idx].reset_index(drop=True)

# ---------- CATE estimators -------------------------------------------------- #
def x_learner_cate(Xm, T, Y, binary):
    if binary:
        m1 = LogisticRegression(max_iter=2000).fit(Xm[T == 1], Y[T == 1])
        m0 = LogisticRegression(max_iter=2000).fit(Xm[T == 0], Y[T == 0])
        mu1, mu0 = m1.predict_proba(Xm)[:, 1], m0.predict_proba(Xm)[:, 1]
    else:
        m1 = LinearRegression().fit(Xm[T == 1], Y[T == 1])
        m0 = LinearRegression().fit(Xm[T == 0], Y[T == 0])
        mu1, mu0 = m1.predict(Xm), m0.predict(Xm)
    d1 = Y[T == 1] - mu0[T == 1]; d0 = mu1[T == 0] - Y[T == 0]
    tau1 = RandomForestRegressor(**RF_KW).fit(Xm[T == 1], d1)
    tau0 = RandomForestRegressor(**RF_KW).fit(Xm[T == 0], d0)
    g = np.clip(RandomForestClassifier(**RF_KW).fit(Xm, T).predict_proba(Xm)[:, 1], 0.05, 0.95)
    return g * tau0.predict(Xm) + (1 - g) * tau1.predict(Xm)

def propensity(Xm, T):
    return np.clip(LogisticRegression(max_iter=2000).fit(Xm, T).predict_proba(Xm)[:, 1], 0.05, 0.95)

def transformed_outcome(Xm, T, Y):
    e = propensity(Xm, T)
    return T * Y / e - (1 - T) * Y / (1 - e)

# ---------- method statistics ------------------------------------------------ #
def m1_importance(Xm, cate, covs):
    """RF maps covariates->CATE; permutation importance (hand-rolled). Returns dict + top."""
    rf = RandomForestRegressor(**RF_KW).fit(Xm, cate)
    base = rf.predict(Xm)
    base_mse = np.mean((cate - base) ** 2) + 1e-12
    imp = {}
    rng = np.random.default_rng(11)
    for j, c in enumerate(covs):
        Xp = Xm.copy(); Xp[:, j] = Xp[rng.permutation(len(Xp)), j]
        mse = np.mean((cate - rf.predict(Xp)) ** 2)
        imp[c] = float((mse - base_mse) / base_mse)   # relative MSE inflation
    return imp

def m2_tree_split(Xm, T, Y, covs):
    """Honest transformed-outcome tree: split sample picks structure, top split = modifier.
    Statistic = normalized impurity reduction at the root split."""
    n = len(Xm); rng = np.random.default_rng(5)
    perm = rng.permutation(n); half = n // 2
    s_idx, _ = perm[:half], perm[half:]
    ystar = transformed_outcome(Xm, T, Y)
    tree = DecisionTreeRegressor(max_depth=3, min_samples_leaf=max(50, n // 40), random_state=0)
    tree.fit(Xm[s_idx], ystar[s_idx])
    t = tree.tree_
    root = 0
    if t.feature[root] < 0:
        return {c: 0.0 for c in covs}, None, 0.0
    # impurity reduction at root, normalized by total variance
    n_root = t.n_node_samples[root]
    imp_root = t.impurity[root]
    l, r = t.children_left[root], t.children_right[root]
    nl, nr = t.n_node_samples[l], t.n_node_samples[r]
    red = imp_root - (nl / n_root) * t.impurity[l] - (nr / n_root) * t.impurity[r]
    norm_red = float(red / (imp_root + 1e-12))
    top = covs[t.feature[root]]
    # rank all features by their best impurity reduction anywhere as split var (depth-limited)
    feat_red = {c: 0.0 for c in covs}
    for node in range(t.node_count):
        f = t.feature[node]
        if f < 0:
            continue
        nn = t.n_node_samples[node]
        cl, cr = t.children_left[node], t.children_right[node]
        rr = t.impurity[node] - (t.n_node_samples[cl] / nn) * t.impurity[cl] \
             - (t.n_node_samples[cr] / nn) * t.impurity[cr]
        feat_red[covs[f]] += float(rr * nn / n)   # weighted by node mass
    return feat_red, top, norm_red

def m3_blp(Xm, cate, covs):
    Xs = np.column_stack([std(Xm[:, j]) for j in range(Xm.shape[1])])
    coef = LinearRegression().fit(Xs, std(cate)).coef_
    return {c: float(abs(coef[j])) for j, c in enumerate(covs)}

# ---------- discovery with placebo floor ------------------------------------- #
def discover(df, covs, binary, outcome="outcome", treat="got_feature"):
    Xm = df[covs].to_numpy(float); T = df[treat].to_numpy(); Y = df[outcome].to_numpy(float)
    # REAL
    cate = x_learner_cate(Xm, T, Y, binary)
    var_real = float(np.var(cate))
    imp1 = m1_importance(Xm, cate, covs)
    feat2, top2, red2 = m2_tree_split(Xm, T, Y, covs)
    imp3 = m3_blp(Xm, cate, covs)
    S = {"m1": max(imp1.values()), "m2": red2, "m3": max(imp3.values())}
    rank = {"m1": sorted(imp1, key=imp1.get, reverse=True),
            "m2": sorted(feat2, key=feat2.get, reverse=True),
            "m3": sorted(imp3, key=imp3.get, reverse=True)}
    # PLACEBO null
    null = {"m1": [], "m2": [], "m3": [], "var": []}
    for k in range(KPLACEBO):
        Tp = np.random.default_rng(100 + k).permutation(T)
        cate_p = x_learner_cate(Xm, Tp, Y, binary)
        null["var"].append(float(np.var(cate_p)))
        null["m1"].append(max(m1_importance(Xm, cate_p, covs).values()))
        _, _, r2 = m2_tree_split(Xm, Tp, Y, covs)
        null["m2"].append(r2)
        null["m3"].append(max(m3_blp(Xm, cate_p, covs).values()))
    out = {"n": len(df), "cate_var_real": round(var_real, 6),
           "cate_var_ratio": round(var_real / (np.median(null["var"]) + 1e-12), 3),
           "methods": {}}
    for m in ("m1", "m2", "m3"):
        floor = float(np.percentile(null[m], 95))
        ratio = S[m] / (np.median(null[m]) + 1e-12)
        discovered = bool(S[m] > floor and ratio >= RATIO)
        top = rank[m][0]
        plan_pos = rank[m].index("plan_tier") if "plan_tier" in rank[m] else None
        top_pos = 0
        out["methods"][m] = dict(
            stat_real=round(float(S[m]), 5), floor95=round(floor, 5),
            ratio=round(float(ratio), 3), discovered=discovered,
            top_covariate=top, top3=rank[m][:3],
            top_is_usage=top in USAGE, plan_tier_rank=plan_pos,
            top_above_plan=(plan_pos is None or top_pos < plan_pos))
    return out, rank, cate

# ---------- downstream: auto-split on discovered modifier --------------------- #
def downstream_sign(df, covs, binary, discovered_cov, cate, outcome="outcome", treat="got_feature"):
    """Split at median of discovered covariate; low-usage side should be +, high-usage side -."""
    v = df[discovered_cov].to_numpy(float)
    med = np.median(v)
    low = v <= med; high = v > med
    lo_cate = float(cate[low].mean()); hi_cate = float(cate[high].mean())
    # usage covariates increase with usage -> low side = casual (+), high side = power (-)
    return dict(modifier=discovered_cov, median=round(float(med), 4),
                low_usage_cate=round(lo_cate, 5), low_sign=sign(lo_cate),
                high_usage_cate=round(hi_cate, 5), high_sign=sign(hi_cate),
                low_recovers_positive=sign(lo_cate) == "positive",
                high_recovers_negative=sign(hi_cate) == "negative",
                both_signs_recovered=(sign(lo_cate) == "positive" and sign(hi_cate) == "negative"))

# ---------- confounding stress ----------------------------------------------- #
def inject_sel(df, conf_col, treat="got_feature"):
    c = std(df[conf_col].to_numpy(float)); T = df[treat].to_numpy()
    keep_p = np.where(T == 1, sigmoid(BETA * c), sigmoid(-BETA * c))
    return np.random.default_rng(SEL_SEED).random(len(df)) < keep_p

# ---------- runners ---------------------------------------------------------- #
def is_binary(Y): return set(np.unique(Y)) <= {0.0, 1.0}

def run_streaming(tag, path, role):
    df = subsample(pd.read_csv(path))
    binary = is_binary(df["outcome"].to_numpy(float))
    res, rank, cate = discover(df, STREAM_COVS, binary)
    res.update(tag=tag, role=role, outcome_type=("binary" if binary else "continuous"))
    # downstream on each method's top covariate (auto-discovered)
    res["downstream"] = {}
    for m in ("m1", "m2", "m3"):
        topc = res["methods"][m]["top_covariate"]
        res["downstream"][m] = downstream_sign(df, STREAM_COVS, binary, topc, cate)
    return res

def run_streaming_stress(tag, path):
    df = subsample(pd.read_csv(path))
    mask = inject_sel(df, "tenure_days")
    d = df.loc[mask].reset_index(drop=True)
    binary = is_binary(d["outcome"].to_numpy(float))
    res, rank, cate = discover(d, STREAM_COVS, binary)
    res.update(tag=tag + " [+confounding on tenure_days]", role="hetero_stress",
               outcome_type=("binary" if binary else "continuous"),
               injected_on="tenure_days")
    res["downstream"] = {}
    for m in ("m1", "m2", "m3"):
        topc = res["methods"][m]["top_covariate"]
        res["downstream"][m] = downstream_sign(d, STREAM_COVS, binary, topc, cate)
    return res

def run_truenull(tag, path):
    df = subsample(pd.read_csv(path))
    covs = [c for c in df.columns if c.startswith("x")]
    binary = is_binary(df["outcome"].to_numpy(float))
    res, rank, cate = discover(df, covs, binary)
    res.update(tag=tag, role="true_null", outcome_type=("binary" if binary else "continuous"),
               covs=covs)
    return res

def main():
    out = {"config": dict(K=KPLACEBO, nsub=NSUB, ratio=RATIO, rf=RF_KW), "results": []}
    print("hetero v2/ds06 ..."); out["results"].append(
        run_streaming("v2/dataset_06", f"{SPIKE}/.data/synthetic_streamly_v2/dataset_06.csv", "hetero"))
    print("hetero v3/ds09 ..."); out["results"].append(
        run_streaming("v3/dataset_09", f"{SPIKE}/.data/synthetic_streamly_v3/dataset_09.csv", "hetero"))
    print("hetero-stress v2/ds06 ..."); out["results"].append(
        run_streaming_stress("v2/dataset_06", f"{SPIKE}/.data/synthetic_streamly_v2/dataset_06.csv"))
    for ds in ("dataset_03", "dataset_08", "dataset_01"):
        print(f"constant-effect specificity v2/{ds} ..."); out["results"].append(
            run_streaming(f"v2/{ds}", f"{SPIKE}/.data/synthetic_streamly_v2/{ds}.csv", "constant_specificity"))
    for tn in ("tn_01", "tn_03", "tn_05", "tn_07"):
        print(f"true-null {tn} ..."); out["results"].append(
            run_truenull(tn, f"{SPIKE}/.data/synthetic_truenull/{tn}.csv"))
    (HERE / "bakeoff_wave3_results.json").write_text(json.dumps(out, indent=2))
    print("wrote bakeoff_wave3_results.json")

if __name__ == "__main__":
    main()
