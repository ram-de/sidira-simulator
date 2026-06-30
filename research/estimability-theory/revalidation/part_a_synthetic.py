"""
part_a_synthetic.py — Part A of PREREG_FIX_REVALIDATION.md (the decisive synthetic test).

Re-validates the NC-collinearity fix from the LaLonde failure:
  FIX RULE (frozen): when computing the negative-control (NC) residual, DROP any covariate
  with |corr(covariate, NC outcome W)| > 0.8 from the NC's adjustment set. The dropped
  covariate STAYS in the main outcome/propensity model. Threshold 0.8 is frozen, NOT tuned.

DGP = the LaLonde twin structure (re74/re75/re78 analog):
  - U  : latent confounder (drives treatment propensity AND main outcome Y) -- the "selection dip".
  - V  : nuisance shared factor (the "permanent income" component), independent of U, drives
         neither T nor Y. X_c and W BOTH load on V -> this is the benign collinearity.
  - W  : CONTINUOUS negative-control outcome (re74 analog). W = 0.4*U + 0.911*V + 0.10*eps.
         Loads on U (corr 0.4) so it genuinely carries the confounding (RAW residual nonzero),
         and on V (the part shared with X_c). True treatment effect on W is ZERO.
  - X_c: collinear covariate (re75 analog). X_c = p*U + q*V + r*eps with q chosen so that
         corr(X_c, W) == c EXACTLY (population). p = DIFFERENTIAL-CLEANING knob = how well X_c
         proxies U (= how much of Y's confounding it can clean). Low p => X_c proxies W (via V)
         far better than it proxies Y's confounder U => the re75-adjacent / re78-distal asymmetry.
  - X_b: a benign second covariate (age/educ analog), proxies U weakly (corr 0.3), corr with W
         ~0.12 (<0.8 -> always KEPT by FIXED). Gives FIXED a covariate to adjust on so it is not
         trivially identical to RAW, and a fair chance to absorb benign association.
  - Y  : BINARY main outcome. logit = B0 + tau*T + bY*U   (confounded by U; true signed effect tau).

  Two regimes per the prereg:
   * CONFOUNDED: propensity = sigmoid(gamma*U); Y confounded by U (bY=1.2). Hidden confounding.
     truth_sign = sign(tau). (tau=0 here = confounded-but-null-effect; guard SHOULD still trip.)
   * NULL (true-null specificity cells, prediction 3): NO unobserved confounding. tau=0. Treatment
     is benignly selected on the OBSERVED covariate X_c: propensity = sigmoid(gamma*X_c). Y has no
     U term (logit = B0 + 0.5*X_c, observed). truth_sign = 0. X_c is still collinear with W. This is
     the genuine specificity risk: dropping X_c re-introduces the X_c-driven (V-channel) benign
     association into the NC residual -> does FIXED manufacture a false alarm?

Three guard variants per cell (main estimate ALWAYS uses full covariates [X_c, X_b]):
  - OLD   : NC adjusted on ALL covariates incl. X_c (the current negative_control_guard).
  - FIXED : NC adjusted on covariates EXCEPT any with sample |corr(cov, W)| > 0.8 (drops X_c at
            high collinearity; X_b kept; X_c stays in the main model).
  - RAW   : NC unadjusted (naive W diff-in-means) -- sensitivity upper bound.
Floor 0.05, ratio 1.5 unchanged (frozen).

Primary trip metric = the NC CONFOUNDING-DETECTION channel: |NC residual| > floor. This is the
channel the fix actually modifies and the channel all three predictions are about (detect / miss /
false-detect confounding via the NC). The full guard decision also fires an orthogonal "indistinct"
rule (main effect not > ratio x bias) which on tau=0 cells trips for EVERY variant regardless of the
fix; we report that full-trip rate too for transparency, but verdicts use the NC-detection channel.

INTEGRITY: implemented per spec; scored grid run ONCE; estimators/thresholds frozen; no tuning to
hit predictions. Prediction 3 is genuinely uncertain. Report raw either way.

Run:  /opt/homebrew/bin/python3.11 research/estimability-theory/revalidation/part_a_synthetic.py
"""
from __future__ import annotations
import json, sys, time
from itertools import product
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent.parent / "empirical-uplift-spike"   # research/empirical-uplift-spike
sys.path.insert(0, str(SPIKE))
from causal_estimator import estimate, negative_control_guard   # noqa: E402

OUT = HERE / "part_a_result.json"

# ---- frozen guard params ----
FLOOR, RATIO = 0.05, 1.5
COLLIN_DROP = 0.8                  # FROZEN fix threshold: drop cov if |corr(cov, W)| > 0.8

# ---- DGP fixed structure ----
N = 8000
SEEDS = 20
B0 = -0.2                          # Y intercept (base rate ~0.45)
BY = 1.2                           # Y's U-loading (confounding strength) in CONFOUNDED regime
W_U, W_V, W_E = 0.4, 0.911, 0.10   # W = W_U*U + W_V*V + W_E*eps_w  (unit var; corr(W,U)=0.4)
XB_U = 0.3                         # X_b = XB_U*U + sqrt(1-XB_U^2)*eps_b (corr(X_b,U)=0.3)

# ---- grid (frozen) ----
COLLIN = [0.5, 0.8, 0.95]          # target corr(X_c, W)
GAMMA = [0.5, 1.5, 2.5]            # selection strength (on U if confounded, on X_c if null)
TAU = [-0.5, 0.0, 0.5]             # signed effect on Y logit (confounded regime); include 0
PCLEAN = [0.15, 0.35]             # differential-cleaning knob = X_c's loading on U (low = poor)
REGIME = ["confounded", "null"]


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def s(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def gen_cell(c, gamma, tau, p, regime, seed):
    rng = np.random.default_rng(seed)
    U = rng.standard_normal(N)
    V = rng.standard_normal(N)
    eps_w = rng.standard_normal(N)
    eps_b = rng.standard_normal(N)
    eps_x = rng.standard_normal(N)

    # X_c with corr(X_c, W) == c EXACTLY (population): q chosen so W_U*p + W_V*q == c.
    q = (c - W_U * p) / W_V
    r2 = 1.0 - p * p - q * q
    r = np.sqrt(r2) if r2 > 0 else 0.0
    X_c = p * U + q * V + r * eps_x

    W = W_U * U + W_V * V + W_E * eps_w
    X_b = XB_U * U + np.sqrt(1.0 - XB_U * XB_U) * eps_b

    if regime == "confounded":
        e = sigmoid(gamma * U)
        T = (rng.random(N) < e).astype(int)
        Y = (rng.random(N) < sigmoid(B0 + tau * T + BY * U)).astype(int)
        truth = s(tau)
    else:  # null: no unobserved confounding; benign OBSERVED selection on X_c; tau forced 0
        e = sigmoid(gamma * X_c)
        T = (rng.random(N) < e).astype(int)
        Y = (rng.random(N) < sigmoid(B0 + 0.0 * T + 0.5 * X_c)).astype(int)
        truth = 0

    df = pd.DataFrame({"T": T, "Y": Y, "W": W, "X_c": X_c, "X_b": X_b})
    return df, truth, q, r


def trip_from(nc_resid, main_ate):
    """Reproduce the guard's two trip channels for a given NC residual and main effect."""
    nc_mag = abs(nc_resid)
    main_mag = abs(main_ate)
    hidden = nc_mag > FLOOR                       # NC confounding-detection channel (the fix touches this)
    indistinct = main_mag <= RATIO * nc_mag       # orthogonal effect-size humility rule
    return bool(hidden), bool(hidden or indistinct)


def run_unit(c, gamma, tau, p, regime, seed):
    df, truth, q, r = gen_cell(c, gamma, tau, p, regime, seed)
    cov_full = ["X_c", "X_b"]

    # OLD = the current negative_control_guard verbatim (NC adjusted on full covariates).
    g_old = negative_control_guard(df, "T", "Y", ["W"], cov_full, floor=FLOOR, ratio=RATIO)
    main_ate = g_old.estimate.t_learner_ate          # main estimate (full covariates) -- shared by all
    old_resid = g_old.neg_control_effect
    old_hidden, old_full = trip_from(old_resid, main_ate)

    # FIXED = drop covariates with sample |corr(cov, W)| > 0.8 from the NC adjustment set.
    w = df["W"].to_numpy(float)
    corr_xc_w = float(np.corrcoef(df["X_c"].to_numpy(float), w)[0, 1])
    corr_xb_w = float(np.corrcoef(df["X_b"].to_numpy(float), w)[0, 1])
    cov_for_nc = [col for col in cov_full
                  if abs(float(np.corrcoef(df[col].to_numpy(float), w)[0, 1])) <= COLLIN_DROP]
    xc_dropped = "X_c" not in cov_for_nc
    if cov_for_nc:
        fixed_resid = float(estimate(df, "T", "W", cov_for_nc).t_learner_ate)
    else:  # nothing left -> unadjusted NC (degenerate; should not happen since X_b always kept)
        fixed_resid = float(w[df["T"].to_numpy() == 1].mean() - w[df["T"].to_numpy() == 0].mean())
    fixed_hidden, fixed_full = trip_from(fixed_resid, main_ate)

    # RAW = NC unadjusted (naive W diff-in-means).
    T = df["T"].to_numpy()
    raw_resid = float(w[T == 1].mean() - w[T == 0].mean())
    raw_hidden, raw_full = trip_from(raw_resid, main_ate)

    adj_sign = s(main_ate)
    adj_correct = (adj_sign == truth) if truth != 0 else None

    return {
        "regime": regime, "collin": c, "gamma": gamma, "tau": tau, "pclean": p, "seed": seed,
        "truth_sign": truth,
        "samp_corr_xc_w": round(corr_xc_w, 4), "samp_corr_xb_w": round(corr_xb_w, 4),
        "xc_dropped": bool(xc_dropped),
        "main_adj_ate": float(main_ate), "adj_sign": adj_sign, "adj_correct": adj_correct,
        "old_resid": float(old_resid), "fixed_resid": float(fixed_resid), "raw_resid": float(raw_resid),
        "old_hidden": old_hidden, "fixed_hidden": fixed_hidden, "raw_hidden": raw_hidden,
        "old_full": old_full, "fixed_full": fixed_full, "raw_full": raw_full,
    }


# --------------------------------------------------------------------------- #
def rate(units, key):
    return (sum(1 for u in units if u[key]) / len(units)) if units else None


def cell_aggregates(units):
    by = {}
    for u in units:
        k = (u["regime"], u["collin"], u["gamma"], u["tau"], u["pclean"])
        by.setdefault(k, []).append(u)
    rows = []
    for k, us in sorted(by.items()):
        rows.append({
            "regime": k[0], "collin": k[1], "gamma": k[2], "tau": k[3], "pclean": k[4],
            "n_seeds": len(us), "truth_sign": us[0]["truth_sign"],
            "xc_drop_rate": round(rate(us, "xc_dropped"), 3),
            "mean_samp_corr_xc_w": round(float(np.mean([u["samp_corr_xc_w"] for u in us])), 4),
            "mean_old_resid": round(float(np.mean([u["old_resid"] for u in us])), 4),
            "mean_fixed_resid": round(float(np.mean([u["fixed_resid"] for u in us])), 4),
            "mean_raw_resid": round(float(np.mean([u["raw_resid"] for u in us])), 4),
            "old_nc_trip": round(rate(us, "old_hidden"), 3),
            "fixed_nc_trip": round(rate(us, "fixed_hidden"), 3),
            "raw_nc_trip": round(rate(us, "raw_hidden"), 3),
            "old_full_trip": round(rate(us, "old_full"), 3),
            "fixed_full_trip": round(rate(us, "fixed_full"), 3),
            "adj_correct_rate": (round(rate([u for u in us if u["adj_correct"] is not None], "adj_correct"), 3)
                                 if any(u["adj_correct"] is not None for u in us) else None),
        })
    return rows


def split_table(units):
    """OLD/FIXED/RAW nc-trip + full-trip by (regime-class x collinearity)."""
    out = {}
    classes = {
        "confounded_signed": lambda u: u["regime"] == "confounded" and u["truth_sign"] != 0,
        "confounded_nulleffect": lambda u: u["regime"] == "confounded" and u["truth_sign"] == 0,
        "true_null": lambda u: u["regime"] == "null",
    }
    for cname, cfn in classes.items():
        out[cname] = {}
        for c in COLLIN + ["ALL"]:
            sub = [u for u in units if cfn(u) and (c == "ALL" or u["collin"] == c)]
            out[cname][str(c)] = {
                "n": len(sub),
                "old_nc_trip": rate(sub, "old_hidden"), "fixed_nc_trip": rate(sub, "fixed_hidden"),
                "raw_nc_trip": rate(sub, "raw_hidden"),
                "old_full_trip": rate(sub, "old_full"), "fixed_full_trip": rate(sub, "fixed_full"),
                "xc_drop_rate": rate(sub, "xc_dropped"),
                "adj_correct_rate": rate([u for u in sub if u["adj_correct"] is not None], "adj_correct"),
            }
    return out


def main():
    t0 = time.time()
    cells = [("confounded", c, g, tau, p) for c, g, tau, p in product(COLLIN, GAMMA, TAU, PCLEAN)]
    cells += [("null", c, g, 0.0, p) for c, g, p in product(COLLIN, GAMMA, PCLEAN)]
    print(f"Grid: {len(cells)} cells x {SEEDS} seeds x n={N} = {len(cells)*SEEDS} units. Running ONCE.")
    units = []
    for i, (regime, c, g, tau, p) in enumerate(cells):
        for sd in range(SEEDS):
            units.append(run_unit(c, g, tau, p, regime, seed=100_000 * i + sd))
        if (i + 1) % 12 == 0:
            print(f"  {i+1}/{len(cells)} cells  ({time.time()-t0:.0f}s)")

    tbl = split_table(units)

    # ---------- Prediction 1: reproduce the failure (c=0.95, confounded, signed) ----------
    p1_old = tbl["confounded_signed"]["0.95"]["old_nc_trip"]
    p1_fixed = tbl["confounded_signed"]["0.95"]["fixed_nc_trip"]
    p1_delta = (p1_fixed - p1_old) if (p1_old is not None and p1_fixed is not None) else None
    p1_pass = bool(p1_delta is not None and p1_delta >= 0.20 and p1_fixed > p1_old)

    # ---------- Prediction 2: fix restores detection where OLD missed ----------
    conf_signed = [u for u in units if u["regime"] == "confounded" and u["truth_sign"] != 0]
    pile_all = [u for u in conf_signed if not u["old_hidden"]]            # OLD missed
    pile_095 = [u for u in pile_all if u["collin"] == 0.95]
    p2_fixed_all = rate(pile_all, "fixed_hidden")
    p2_fixed_095 = rate(pile_095, "fixed_hidden")
    p2_pass = bool(p2_fixed_all is not None and p2_fixed_all >= 0.80)

    # ---------- Prediction 3 (decisive): specificity on true-null cells ----------
    nulls = [u for u in units if u["regime"] == "null"]
    nulls_095 = [u for u in nulls if u["collin"] == 0.95]
    p3_fixed_all = rate(nulls, "fixed_hidden")
    p3_fixed_095 = rate(nulls_095, "fixed_hidden")
    p3_old_all = rate(nulls, "old_hidden")
    p3_raw_all = rate(nulls, "raw_hidden")
    p3_pass = bool(p3_fixed_all is not None and p3_fixed_all <= 0.10)

    # ---------- verdict mapping (prereg) ----------
    if p1_pass and p2_pass and p3_pass:
        verdict = "FIX -> LEAD-confirmed (detection restored AND specificity preserved, synthetic)"
    elif not p3_pass:
        verdict = ("FIX -> NULL / route-to-proximal (specificity sacrificed: FIXED false-trips on "
                   "benign true-nulls; the covariate-drop rule is not enough -> needs proximal/double-NC)")
    else:
        verdict = "FIX -> PARTIAL (detection result mixed; see P1/P2 raw)"

    checks = {
        "prediction1_reproduce_failure": {
            "where": "collin=0.95, confounded, signed (tau!=0)", "channel": "NC-detection (|resid|>floor)",
            "old_nc_trip": p1_old, "fixed_nc_trip": p1_fixed, "delta_fixed_minus_old": p1_delta,
            "criterion": "delta >= 0.20 and FIXED > OLD", "result": "PASS" if p1_pass else "FAIL",
            "old_full_trip": tbl["confounded_signed"]["0.95"]["old_full_trip"],
            "fixed_full_trip": tbl["confounded_signed"]["0.95"]["fixed_full_trip"]},
        "prediction2_fix_restores_detection": {
            "pile": "confounded signed units where OLD's NC missed (no detect)",
            "pile_n_all": len(pile_all), "fixed_nc_trip_on_pile_all": p2_fixed_all,
            "pile_n_collin095": len(pile_095), "fixed_nc_trip_on_pile_095": p2_fixed_095,
            "criterion": "FIXED nc-trip on pile >= 0.80", "result": "PASS" if p2_pass else "FAIL"},
        "prediction3_specificity_DECISIVE": {
            "cells": "true-null (tau=0, no unobserved confounding), X_c still collinear, benign selection on X_c",
            "channel": "NC-detection (|resid|>floor) -- the channel the fix modifies",
            "fixed_false_trip_all": p3_fixed_all, "fixed_false_trip_collin095": p3_fixed_095,
            "old_false_trip_all": p3_old_all, "raw_false_trip_all": p3_raw_all,
            "criterion": "FIXED false-trip rate <= 0.10", "result": "PASS" if p3_pass else "FAIL",
            "note": ("full guard trip (hidden OR indistinct) is ~1.0 on tau=0 for ALL variants because "
                     "the orthogonal indistinct rule always fires when the true effect is 0; that is a "
                     "design constant unaffected by the fix, so the verdict uses the NC-detection channel."),
            "fixed_full_trip_all": rate(nulls, "fixed_full"), "old_full_trip_all": rate(nulls, "old_full")},
        "verdict": verdict,
    }

    result = {
        "prereg": "research/estimability-theory/PREREG_FIX_REVALIDATION.md (Part A)",
        "integrity": ("single scored run; estimators frozen; FLOOR=0.05 RATIO=1.5 COLLIN_DROP=0.8 frozen; "
                      "no tuning to predictions; prediction 3 genuinely uncertain"),
        "config": {
            "N": N, "SEEDS": SEEDS, "n_cells": len(cells), "n_units": len(units),
            "guard": {"floor": FLOOR, "ratio": RATIO, "collin_drop_threshold": COLLIN_DROP},
            "grid": {"collin": COLLIN, "gamma": GAMMA, "tau_confounded": TAU, "pclean": PCLEAN,
                     "regime": REGIME},
            "dgp": {"W": "0.4*U + 0.911*V + 0.10*eps  (continuous NC, corr(W,U)=0.4, true T-effect 0)",
                    "X_c": "p*U + q*V + r*eps, q s.t. corr(X_c,W)==collin exactly; p=pclean=cleaning knob",
                    "X_b": "0.3*U + 0.954*eps (corr(X_b,W)~0.12, always kept by FIXED)",
                    "Y": "binary, logit=B0+tau*T+1.2*U (confounded) | B0+0.5*X_c (null, no U, tau=0)",
                    "propensity": "sigmoid(gamma*U) confounded | sigmoid(gamma*X_c) null (benign observed)",
                    "B0": B0, "BY": BY},
            "trip_channels": {"primary_verdict": "NC-detection: |NC residual| > floor (the fix modifies this)",
                              "secondary": "full guard = NC-detection OR indistinct (actual abstain decision)"},
        },
        "verdict_checks": checks,
        "trip_table_by_class_and_collinearity": tbl,
        "cells": cell_aggregates(units),
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(result, indent=2))

    # ---------- console summary ----------
    def fmt(x):
        return "None" if x is None else f"{x:.3f}"
    print("\n================ PART A RESULT (raw) ================")
    print(f"runtime {result['runtime_sec']}s  units={len(units)}")
    print("\nNC-detection trip rates (|NC residual| > 0.05), by class x collinearity:")
    print("  class                 collin   OLD    FIXED   RAW    (xc_drop)")
    for cname in ("confounded_signed", "confounded_nulleffect", "true_null"):
        for c in COLLIN + ["ALL"]:
            r = tbl[cname][str(c)]
            print(f"  {cname:21s} {str(c):6s}  {fmt(r['old_nc_trip'])}  {fmt(r['fixed_nc_trip'])}  "
                  f"{fmt(r['raw_nc_trip'])}  ({fmt(r['xc_drop_rate'])})  n={r['n']}")
    print("\n--- PREDICTIONS ---")
    print(f"P1 reproduce failure (c=0.95 confounded signed): OLD={fmt(p1_old)} FIXED={fmt(p1_fixed)} "
          f"delta={fmt(p1_delta)} => {'PASS' if p1_pass else 'FAIL'}")
    print(f"P2 fix restores detection (FIXED nc-trip on OLD-missed pile): "
          f"all={fmt(p2_fixed_all)} (n={len(pile_all)}) c095={fmt(p2_fixed_095)} (n={len(pile_095)}) "
          f"=> {'PASS' if p2_pass else 'FAIL'} (>=0.80)")
    print(f"P3 SPECIFICITY (true-null FIXED false-trip): all={fmt(p3_fixed_all)} c095={fmt(p3_fixed_095)} "
          f"| OLD={fmt(p3_old_all)} RAW={fmt(p3_raw_all)} => {'PASS' if p3_pass else 'FAIL'} (<=0.10)")
    print(f"\nVERDICT: {verdict}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
