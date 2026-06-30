"""
proximal_ci.py — Sealed proximal-causal-inference experiment.

Implements PREREG_PROXIMAL_CI.md EXACTLY. Tests whether moving from DETECT-and-abstain
(the single negative-control guard) to CORRECT-and-answer (COCA, Tchetgen Tchetgen 2014,
additive equi-confounding) expands the estimable slice — and where it backfires.

INTEGRITY: implement per spec; run the scored grid ONCE; do NOT tune estimators/thresholds
to hit predictions. Report raw numbers including refuted predictions.

Estimators (all reuse research/empirical-uplift-spike/causal_estimator.py):
  - naive     : diff-in-means on Y                     (estimate().naive_ate)
  - adjusted  : T-learner standardization on X          (estimate().t_learner_ate)
  - guard     : single-NC abstain (floor=0.05, ratio=1.5)  (negative_control_guard)
  - COCA      : adjusted_ate(Y) - adjusted_ate(W)        (subtract the NC residual the guard computes)

Run:  /opt/homebrew/bin/python3.11 research/estimability-theory/proximal/proximal_ci.py
"""
from __future__ import annotations
import json, sys, time
from itertools import product
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SPIKE = HERE.parent.parent / "empirical-uplift-spike"     # research/empirical-uplift-spike
sys.path.insert(0, str(SPIKE))
from causal_estimator import estimate, negative_control_guard   # noqa: E402

DATA = SPIKE / ".data"
OUT = HERE / "proximal_ci_result.json"

FLOOR, RATIO = 0.05, 1.5          # frozen guard params (from causal_estimator / campaign iter2)
N = 8000
SEEDS = 20
# DGP fixed structure
B0 = -0.2                          # Y intercept (base rate ~0.45)
BW0 = -0.2                         # W intercept — matched to Y for clean EQUI home turf
BETA_Y_VIOLATED = 1.0             # in VIOLATED, Y's U-loading is fixed; W's = kappa (mismatch)

# Grid (frozen in prereg)
RHO = [0.0, 0.25, 0.5, 0.75, 1.0]
GAMMA = [0.5, 1.5, 2.5]
TAU = [-0.35, -0.10, 0.0, 0.10, 0.35]
KAPPA = [0.3, 0.6, 1.0, 1.3]
MODE = ["EQUI", "VIOLATED"]


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def gen_cell(rho, gamma, tau, kappa, mode, seed):
    """Controlled DGP. U latent; X = rho*U + sqrt(1-rho^2)*noise observes a fraction of U.
    propensity = sigmoid(gamma*U); Y binary, true log-odds effect tau, U-loading beta_Y;
    W binary NCO with TRUE T-effect 0 and U-loading beta_W.
      EQUI:     beta_Y = beta_W = kappa  (W loads on U identically to Y's confounding path)
      VIOLATED: beta_Y = 1.0 (fixed), beta_W = kappa  (mismatch; equi broken except kappa==1)
    """
    rng = np.random.default_rng(seed)
    U = rng.standard_normal(N)
    X = rho * U + np.sqrt(max(0.0, 1.0 - rho * rho)) * rng.standard_normal(N)
    e = sigmoid(gamma * U)
    T = (rng.random(N) < e).astype(int)
    if mode == "EQUI":
        beta_Y = kappa
        beta_W = kappa
    else:  # VIOLATED
        beta_Y = BETA_Y_VIOLATED
        beta_W = kappa
    Y = (rng.random(N) < sigmoid(B0 + tau * T + beta_Y * U)).astype(int)
    W = (rng.random(N) < sigmoid(BW0 + 0.0 * T + beta_W * U)).astype(int)
    return pd.DataFrame({"T": T, "Y": Y, "W": W, "X": X})


def s(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


def run_unit(rho, gamma, tau, kappa, mode, seed):
    df = gen_cell(rho, gamma, tau, kappa, mode, seed)
    g = negative_control_guard(df, "T", "Y", ["W"], ["X"], floor=FLOOR, ratio=RATIO)
    adj = g.estimate.t_learner_ate
    nc = g.neg_control_effect           # adjusted_ate(W) — the residual the guard computes
    coca = adj - nc                     # COCA correction = adjusted(Y) - adjusted(W)
    naive = g.estimate.naive_ate
    truth = s(tau)
    return {
        "mode": mode, "rho_obs": rho, "gamma": gamma, "tau": tau, "kappa": kappa, "seed": seed,
        "hidden_confounding": rho < 1.0,
        "truth_sign": truth,
        "naive_ate": float(naive), "adj_ate": float(adj), "nc_resid": float(nc), "coca_ate": float(coca),
        "naive_sign": s(naive), "adj_sign": s(adj), "coca_sign": s(coca),
        "guard_trips": bool(g.trips),
        "naive_correct": (s(naive) == truth) if truth != 0 else None,
        "adj_correct": (s(adj) == truth) if truth != 0 else None,
        "coca_correct": (s(coca) == truth) if truth != 0 else None,
    }


# --------------------------------------------------------------------------- #
# Real anchors
# --------------------------------------------------------------------------- #
def anchor_hillstrom():
    df = pd.read_csv(DATA / "hillstrom.csv")
    df = df[df["segment"].isin(["Womens E-Mail", "No E-Mail"])].copy().reset_index(drop=True)
    df["T"] = (df["segment"] == "Womens E-Mail").astype(int)
    df["loghist"] = np.log1p(df["history"])
    # NC outcome = `mens` (pre-treatment; email cannot cause it) per iter3 convention.
    # X excludes the NC ('mens') and the deliberately-hidden confounder ('history').
    X = ["recency", "loghist", "womens", "newbie"]
    g = negative_control_guard(df, "T", "visit", ["mens"], X, floor=FLOOR, ratio=RATIO)
    adj = g.estimate.t_learner_ate
    coca = adj - g.neg_control_effect
    return {
        "name": "Hillstrom", "T": "Womens E-Mail vs No-Email", "Y": "visit",
        "nc_outcome": "mens", "X": X, "truth_sign": 1, "truth_note": "+4.52pp visit lift (RCT)",
        "naive_pp": round(g.estimate.naive_ate * 100, 3),
        "adj_pp": round(adj * 100, 3),
        "nc_resid": round(g.neg_control_effect, 4),
        "coca_pp": round(coca * 100, 3),
        "guard_trips": bool(g.trips),
        "adj_sign": s(adj), "coca_sign": s(coca),
        "coca_preserves_sign": bool(s(coca) == 1),
    }


def anchor_cookiecats():
    df = pd.read_csv(DATA / "cookie_cats.csv")
    for m in ("retention_1", "retention_7"):
        df[m] = df[m].astype(str).str.lower().map({"true": 1, "false": 0})
    df["T"] = (df["version"] == "gate_40").astype(int)
    df["logeng"] = np.log1p(df["sum_gamerounds"])
    # No clean pre-treatment NC outcome exists in Cookie Cats. We use retention_1 as the NC:
    # an IMPERFECT NC (day-1 retention carries a small real treatment effect), stated as a caveat.
    # In a clean RCT the adjusted residual is tiny, so COCA must remain a near no-op on retention_7.
    X = ["logeng"]
    g = negative_control_guard(df, "T", "retention_7", ["retention_1"], X, floor=FLOOR, ratio=RATIO)
    adj = g.estimate.t_learner_ate
    coca = adj - g.neg_control_effect
    return {
        "name": "CookieCats", "T": "gate_40 vs gate_30", "Y": "retention_7",
        "nc_outcome": "retention_1",
        "nc_caveat": "imperfect NC: retention_1 carries a small real treatment effect; no clean "
                     "pre-treatment NC exists in this dataset",
        "X": X, "truth_sign": -1, "truth_note": "~-0.82pp 7-day retention (gate_30 wins, RCT)",
        "naive_pp": round(g.estimate.naive_ate * 100, 3),
        "adj_pp": round(adj * 100, 3),
        "nc_resid": round(g.neg_control_effect, 4),
        "coca_pp": round(coca * 100, 3),
        "guard_trips": bool(g.trips),
        "adj_sign": s(adj), "coca_sign": s(coca),
        "coca_preserves_sign": bool(s(coca) == -1),
    }


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def frac(sub, key):
    sub = [u for u in sub if u[key] is not None]
    return (sum(1 for u in sub if u[key]) / len(sub)) if sub else None


def compute_metrics(units):
    nz = [u for u in units if u["truth_sign"] != 0]           # tau != 0 (signed truth)
    out = {}

    # ---- Prediction 1: EQUI recovery on the abstain pile ----
    # pile = EQUI, confounded, guard-abstained, tau!=0, adjusted got the sign WRONG.
    def recovery(mode):
        pile = [u for u in nz if u["mode"] == mode and u["hidden_confounding"]
                and u["guard_trips"] and not u["adj_correct"]]
        broad = [u for u in nz if u["mode"] == mode and u["hidden_confounding"] and u["guard_trips"]]
        return {
            "pile_n_adjusted_wrong": len(pile),
            "coca_recovery_rate": frac(pile, "coca_correct"),
            "adjusted_recovery_rate": frac(pile, "adj_correct"),   # 0 by construction
            "naive_recovery_rate": frac(pile, "naive_correct"),
            "broad_abstain_pile_n": len(broad),
            "broad_coca_correct_rate": frac(broad, "coca_correct"),
            "broad_adjusted_correct_rate": frac(broad, "adj_correct"),
            "broad_naive_correct_rate": frac(broad, "naive_correct"),
        }
    out["recovery_EQUI"] = recovery("EQUI")
    out["recovery_VIOLATED"] = recovery("VIOLATED")

    # ---- Prediction 2: silent-failure (region C) COCA vs guard ----
    # region C = confident AND directional AND wrong.
    #   guard confident = NOT abstain (ships adjusted); COCA = correct-and-answer, always confident.
    def regionC(mode):
        sub = [u for u in nz if u["mode"] == mode] if mode != "ALL" else nz
        guard_conf = [u for u in sub if not u["guard_trips"]]
        guard_C = (sum(1 for u in guard_conf if not u["adj_correct"]) / len(sub)) if sub else None
        coca_C = (sum(1 for u in sub if not u["coca_correct"]) / len(sub)) if sub else None
        # matched-denominator: among guard-CONFIDENT cells, COCA wrong vs guard wrong
        coca_on_conf = frac([{"x": not u["coca_correct"]} for u in guard_conf], "x") if guard_conf else None
        guard_on_conf = frac([{"x": not u["adj_correct"]} for u in guard_conf], "x") if guard_conf else None
        return {
            "n": len(sub),
            "guard_regionC_rate": guard_C,
            "coca_regionC_rate": coca_C,
            "guard_confident_n": len(guard_conf),
            "coca_worse": (coca_C > guard_C) if (coca_C is not None and guard_C is not None) else None,
            "matched_guardconf_coca_wrong": coca_on_conf,
            "matched_guardconf_guard_wrong": guard_on_conf,
        }
    out["silent_failure_EQUI"] = regionC("EQUI")
    out["silent_failure_VIOLATED"] = regionC("VIOLATED")
    out["silent_failure_ALL"] = regionC("ALL")

    # ---- Over-correction harm: adjusted RIGHT but COCA WRONG ----
    def overcorr(mode):
        sub = [u for u in nz if u["mode"] == mode]
        adj_right = [u for u in sub if u["adj_correct"]]
        flips = [u for u in adj_right if not u["coca_correct"]]
        return {"n_adjusted_right": len(adj_right), "n_coca_flips_wrong": len(flips),
                "harm_rate": (len(flips) / len(adj_right)) if adj_right else None}
    out["overcorrection_EQUI"] = overcorr("EQUI")
    out["overcorrection_VIOLATED"] = overcorr("VIOLATED")

    # ---- True-null (tau=0) direction invention (eps = 1pp magnitude => 'directional') ----
    EPS = 0.01
    nulls = [u for u in units if u["truth_sign"] == 0]
    def null_invent(mode):
        sub = [u for u in nulls if u["mode"] == mode] if mode != "ALL" else nulls
        coca_dir = (sum(1 for u in sub if abs(u["coca_ate"]) > EPS) / len(sub)) if sub else None
        guard_conf = [u for u in sub if not u["guard_trips"]]
        guard_dir = (sum(1 for u in guard_conf if abs(u["adj_ate"]) > EPS) / len(sub)) if sub else None
        return {"n": len(sub), "coca_directional_rate": coca_dir,
                "guard_confident_directional_rate": guard_dir, "eps_pp": EPS * 100}
    out["truenull_invention_EQUI"] = null_invent("EQUI")
    out["truenull_invention_VIOLATED"] = null_invent("VIOLATED")
    out["truenull_invention_ALL"] = null_invent("ALL")

    # ---- overall sign-recovery (all confounded tau!=0, regardless of guard) ----
    conf = [u for u in nz if u["hidden_confounding"]]
    out["overall_confounded"] = {
        "n": len(conf),
        "naive_correct_rate": frac(conf, "naive_correct"),
        "adjusted_correct_rate": frac(conf, "adj_correct"),
        "coca_correct_rate": frac(conf, "coca_correct"),
        "by_mode": {m: {
            "n": len([u for u in conf if u["mode"] == m]),
            "naive": frac([u for u in conf if u["mode"] == m], "naive_correct"),
            "adjusted": frac([u for u in conf if u["mode"] == m], "adj_correct"),
            "coca": frac([u for u in conf if u["mode"] == m], "coca_correct"),
        } for m in MODE},
    }
    return out


def cell_aggregates(units):
    by = {}
    for u in units:
        k = (u["mode"], u["rho_obs"], u["gamma"], u["tau"], u["kappa"])
        by.setdefault(k, []).append(u)
    rows = []
    for k, us in by.items():
        nz = [u for u in us if u["truth_sign"] != 0]
        rows.append({
            "mode": k[0], "rho_obs": k[1], "gamma": k[2], "tau": k[3], "kappa": k[4],
            "n_seeds": len(us), "hidden_confounding": us[0]["hidden_confounding"],
            "guard_trip_rate": round(sum(u["guard_trips"] for u in us) / len(us), 3),
            "mean_naive_ate": round(float(np.mean([u["naive_ate"] for u in us])), 4),
            "mean_adj_ate": round(float(np.mean([u["adj_ate"] for u in us])), 4),
            "mean_nc_resid": round(float(np.mean([u["nc_resid"] for u in us])), 4),
            "mean_coca_ate": round(float(np.mean([u["coca_ate"] for u in us])), 4),
            "naive_correct_rate": (round(sum(u["naive_correct"] for u in nz) / len(nz), 3) if nz else None),
            "adj_correct_rate": (round(sum(u["adj_correct"] for u in nz) / len(nz), 3) if nz else None),
            "coca_correct_rate": (round(sum(u["coca_correct"] for u in nz) / len(nz), 3) if nz else None),
        })
    rows.sort(key=lambda r: (r["mode"], r["rho_obs"], r["gamma"], r["tau"], r["kappa"]))
    return rows


def main():
    t0 = time.time()
    cells = list(product(RHO, GAMMA, TAU, KAPPA, MODE))
    print(f"Grid: {len(cells)} cells x {SEEDS} seeds x n={N} = {len(cells)*SEEDS} fits. Running ONCE.")
    units = []
    for i, (rho, gamma, tau, kappa, mode) in enumerate(cells):
        for sd in range(SEEDS):
            units.append(run_unit(rho, gamma, tau, kappa, mode, seed=10_000 * i + sd))
        if (i + 1) % 60 == 0:
            print(f"  {i+1}/{len(cells)} cells  ({time.time()-t0:.0f}s)")

    metrics = compute_metrics(units)
    anchors = {"hillstrom": anchor_hillstrom(), "cookie_cats": anchor_cookiecats()}

    # ---- Three pre-registered verdict checks ----
    p1_rate = metrics["recovery_EQUI"]["coca_recovery_rate"]
    p1 = (p1_rate is not None and p1_rate >= 0.50)
    vc = metrics["silent_failure_VIOLATED"]
    p2 = (vc["coca_worse"] is True)
    p3 = (anchors["hillstrom"]["coca_preserves_sign"] and anchors["cookie_cats"]["coca_preserves_sign"])

    # verdict mapping (prereg)
    harm_bounded = (metrics["overcorrection_EQUI"]["n_coca_flips_wrong"]
                    <= metrics["overcorrection_VIOLATED"]["n_coca_flips_wrong"])
    coca_beats_adj_pile = (p1_rate is not None and p1_rate > 0.0)
    if p1 and p3 and harm_bounded:
        verdict = "LEAD (COCA-correct INSIDE a guard that abstains when equi-confounding implausible)"
    elif not coca_beats_adj_pile:
        verdict = "NULL (COCA does not recover sign on the abstain pile)"
    else:
        verdict = "PARTIAL / MECH-ONLY"

    checks = {
        "prediction1_EQUI_recovery_ge_50pct": {
            "coca_recovery_rate": p1_rate, "threshold": 0.50, "result": "PASS" if p1 else "FAIL",
            "pile_n": metrics["recovery_EQUI"]["pile_n_adjusted_wrong"]},
        "prediction2_VIOLATED_coca_silentfail_strictly_worse": {
            "coca_regionC": vc["coca_regionC_rate"], "guard_regionC": vc["guard_regionC_rate"],
            "result": "PASS" if p2 else "FAIL"},
        "prediction3_real_anchor_safety": {
            "hillstrom_coca_sign": anchors["hillstrom"]["coca_sign"],
            "cookie_cats_coca_sign": anchors["cookie_cats"]["coca_sign"],
            "result": "PASS" if p3 else "FAIL"},
        "verdict": verdict,
    }

    result = {
        "prereg": "research/estimability-theory/PREREG_PROXIMAL_CI.md",
        "integrity": "single scored run; estimators/thresholds frozen (FLOOR=0.05, RATIO=1.5); no tuning to predictions",
        "config": {"N": N, "SEEDS": SEEDS, "n_cells": len(cells), "n_units": len(units),
                   "grid": {"rho_obs": RHO, "gamma": GAMMA, "tau": TAU, "kappa": KAPPA, "mode": MODE},
                   "dgp": {"B0": B0, "BW0": BW0, "beta_Y_EQUI": "kappa", "beta_W_EQUI": "kappa",
                           "beta_Y_VIOLATED": BETA_Y_VIOLATED, "beta_W_VIOLATED": "kappa"},
                   "proximal_bridge_double_NC": "SKIPPED (stretch; time-bound) — COCA single-NC correction only"},
        "verdict_checks": checks,
        "metrics": metrics,
        "real_anchors": anchors,
        "cells": cell_aggregates(units),
        "runtime_sec": round(time.time() - t0, 1),
    }
    OUT.write_text(json.dumps(result, indent=2))

    # ---- console summary ----
    print("\n================ RESULT (raw) ================")
    print(f"runtime {result['runtime_sec']}s")
    r = metrics["recovery_EQUI"]
    print(f"\nP1 EQUI recovery on abstain pile (adjusted-wrong, n={r['pile_n_adjusted_wrong']}):")
    print(f"   COCA={r['coca_recovery_rate']}  adjusted={r['adjusted_recovery_rate']}  naive={r['naive_recovery_rate']}")
    print(f"   broad EQUI abstain pile (n={r['broad_abstain_pile_n']}): "
          f"COCA={r['broad_coca_correct_rate']} adj={r['broad_adjusted_correct_rate']} naive={r['broad_naive_correct_rate']}")
    print(f"   => P1 {'PASS' if p1 else 'FAIL'} (>=0.50)")
    print(f"\nP2 VIOLATED silent-failure (regionC): COCA={vc['coca_regionC_rate']}  guard={vc['guard_regionC_rate']}")
    print(f"   matched (guard-confident cells): COCA-wrong={vc['matched_guardconf_coca_wrong']} "
          f"guard-wrong={vc['matched_guardconf_guard_wrong']}")
    print(f"   => P2 {'PASS' if p2 else 'FAIL'} (COCA strictly worse)")
    oc_e, oc_v = metrics["overcorrection_EQUI"], metrics["overcorrection_VIOLATED"]
    print(f"\nover-correction harm: EQUI flips={oc_e['n_coca_flips_wrong']}/{oc_e['n_adjusted_right']} "
          f"VIOLATED flips={oc_v['n_coca_flips_wrong']}/{oc_v['n_adjusted_right']}")
    h, c = anchors["hillstrom"], anchors["cookie_cats"]
    print(f"\nP3 real anchors:")
    print(f"   Hillstrom visit: naive={h['naive_pp']}pp adj={h['adj_pp']}pp ncResid={h['nc_resid']} "
          f"COCA={h['coca_pp']}pp sign={h['coca_sign']} (truth +) preserves={h['coca_preserves_sign']}")
    print(f"   CookieCats ret7: naive={c['naive_pp']}pp adj={c['adj_pp']}pp ncResid={c['nc_resid']} "
          f"COCA={c['coca_pp']}pp sign={c['coca_sign']} (truth -) preserves={c['coca_preserves_sign']}")
    print(f"   => P3 {'PASS' if p3 else 'FAIL'}")
    print(f"\nVERDICT: {verdict}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
