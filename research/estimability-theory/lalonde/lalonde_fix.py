"""
lalonde_fix.py — sealed FIX diagnostic per research/estimability-theory/PREREG_LALONDE_FIX.md.

Single pre-specified change: recompute the negative-control (re74) placebo residual with re75
REMOVED from the NC's adjustment set. re75 STAYS in the main re78 outcome/propensity model — only
the NC residual computation drops it. Also report the stricter no-covariate raw placebo as the
sensitivity upper bound. Trip logic = the validated 3-part gate (floor=0.05, ratio=1.5), applied
with main effect = adjusted re78 (full covariates incl re75) vs NC residual (re75-removed).

Reuses data + causal_estimator.estimate. One run, no tuning beyond the single re75-removal.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "empirical-uplift-spike"))
from causal_estimator import estimate  # noqa: E402

DATA = HERE / "data"
# main outcome/propensity model keeps the full set (incl. re75)
MAIN_COV = ["age", "education", "black", "hispanic", "married", "nodegree", "re75"]
# the single fix: NC adjustment set drops re75 (its near-collinear twin)
NC_COV = ["age", "education", "black", "hispanic", "married", "nodegree"]
NC = "re74"
OUTCOME = "re78"
FLOOR = 0.05
RATIO = 1.5


def load():
    exp = pd.read_stata(DATA / "nsw_dw.dta")
    psid = pd.read_stata(DATA / "psid_controls.dta")
    cps = pd.read_stata(DATA / "cps_controls.dta")
    treated = exp[exp["treat"] == 1].copy()
    exp_ctrl = exp[exp["treat"] == 0].copy()
    cond = {
        "A_experimental":       pd.concat([treated, exp_ctrl], ignore_index=True),
        "B_psid_observational": pd.concat([treated, psid], ignore_index=True),
        "C_cps_observational":  pd.concat([treated, cps], ignore_index=True),
    }
    for df in cond.values():
        df["treat"] = df["treat"].astype(int)
    return cond


def run_condition(name: str, df: pd.DataFrame) -> dict:
    scale = float(df[OUTCOME].std(ddof=1))   # same standardization as the promotion run
    df = df.copy()
    df["re78_z"] = df[OUTCOME] / scale
    df["re74_z"] = df[NC] / scale

    # main effect: adjusted re78 on the FULL covariate set (incl. re75) — unchanged
    main = estimate(df, "treat", "re78_z", MAIN_COV)

    # NC residual WITH re75 removed (the fix)
    nc_fix = estimate(df, "treat", "re74_z", NC_COV)
    nc_resid = float(nc_fix.t_learner_ate)

    # raw placebo (NO covariates) = naive treated-control diff of re74_z  (upper bound)
    raw_placebo = float(df.loc[df.treat == 1, "re74_z"].mean()
                        - df.loc[df.treat == 0, "re74_z"].mean())

    # 3-part gate applied with the fixed NC residual
    nc_mag = abs(nc_resid)
    main_mag = abs(main.t_learner_ate)
    hidden = nc_mag > FLOOR
    indistinct = main_mag <= RATIO * nc_mag
    trips = bool(hidden or indistinct)
    if hidden:
        reason = (f"NC re74 residual {nc_resid:+.4f} (re75-removed) > |{FLOOR}|: hidden "
                  "confounding -> abstain")
    elif indistinct:
        reason = (f"main {main.t_learner_ate:+.4f} not > {RATIO}x NC bias ({nc_resid:+.4f}): "
                  "indistinguishable -> abstain")
    else:
        reason = (f"main {main.t_learner_ate:+.4f} clears {RATIO}x NC bias ({nc_resid:+.4f}): "
                  "estimate trusted")

    return {
        "n": int(len(df)),
        "main_adjusted_re78_std": float(main.t_learner_ate),
        "nc_residual_re74_std_re75_REMOVED": nc_resid,
        "nc_residual_re74_dollars_re75_REMOVED": nc_resid * scale,
        "raw_placebo_re74_std_NO_covariates": raw_placebo,
        "raw_placebo_re74_dollars_NO_covariates": raw_placebo * scale,
        "floor": FLOOR,
        "hidden_confounding_flag": bool(hidden),
        "indistinct_flag": bool(indistinct),
        "guard_trips": trips,
        "guard_reason": reason,
    }


def main():
    cond = load()
    results = {name: run_condition(name, df) for name, df in cond.items()}
    A, B, C = (results["A_experimental"], results["B_psid_observational"],
               results["C_cps_observational"])

    p1_detection_restored = bool(B["guard_trips"] and C["guard_trips"]
                                 and abs(B["nc_residual_re74_std_re75_REMOVED"]) > FLOOR
                                 and abs(C["nc_residual_re74_std_re75_REMOVED"]) > FLOOR)
    # specificity: does the COLLINEARITY mechanism falsely trip A? report the NC residual + whether
    # a trip on A is driven by the NC-hidden flag (this mechanism) vs other.
    a_nc_hidden = bool(abs(A["nc_residual_re74_std_re75_REMOVED"]) > FLOOR)

    verdict = {
        "P1_detection_restored_BC_PASS": p1_detection_restored,
        "P2_A_nc_residual_std": A["nc_residual_re74_std_re75_REMOVED"],
        "P2_A_trips_from_nc_hidden_mechanism": a_nc_hidden,
        "P2_A_guard_trips_overall": A["guard_trips"],
        "note": "P1 PASS => failure is the collinearity mechanism; principled NC-aware adjustment "
                "restores detection on LaLonde (candidate fix / LEAD, NOT promotion — needs synthetic "
                "re-validation with NC-collinear covariates + other real RCTs). Fix raises NC "
                "sensitivity globally (honest limit, prereg P3).",
    }

    out = {
        "benchmark": "LaLonde NSW (Dehejia-Wahba) — FIX diagnostic",
        "change": "re75 removed from NC(re74) adjustment set only; main re78 model unchanged",
        "interpreter": sys.version.split()[0],
        "main_covariates": MAIN_COV,
        "nc_covariates_fixed": NC_COV,
        "guard_params": {"floor": FLOOR, "ratio": RATIO},
        "conditions": results,
        "verdict": verdict,
    }
    out_path = HERE / "lalonde_fix_result.json"
    out_path.write_text(json.dumps(out, indent=2))

    print("=" * 78)
    print("LaLonde FIX DIAGNOSTIC — re75 removed from NC adjustment (raw, one run)")
    print("=" * 78)
    for nm, r in results.items():
        print(f"\n--- {nm} (n={r['n']}) ---")
        print(f"  main adjusted re78 (std, re75 IN)      : {r['main_adjusted_re78_std']:+.4f}")
        print(f"  NC re74 residual (std, re75 REMOVED)   : "
              f"{r['nc_residual_re74_std_re75_REMOVED']:+.4f}  "
              f"(${r['nc_residual_re74_dollars_re75_REMOVED']:+.0f})   floor=±{FLOOR}")
        print(f"  NC re74 raw placebo (std, NO covariates): "
              f"{r['raw_placebo_re74_std_NO_covariates']:+.4f}  "
              f"(${r['raw_placebo_re74_dollars_NO_covariates']:+.0f})")
        print(f"  hidden={r['hidden_confounding_flag']} indistinct={r['indistinct_flag']} "
              f"-> TRIPS={r['guard_trips']}")
        print(f"  reason: {r['guard_reason']}")
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    for k, v in verdict.items():
        print(f"  {k}: {v}")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
