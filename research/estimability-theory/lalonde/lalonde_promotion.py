"""
lalonde_promotion.py — sealed PROMOTION test on naturally-confounded REAL data.

Implements research/estimability-theory/PREREG_LALONDE_PROMOTION.md EXACTLY.
Reuses research/empirical-uplift-spike/causal_estimator.py (estimate + negative_control_guard).

Benchmark: LaLonde 1986 / Dehejia-Wahba 1999 NSW job-training data.
  Data source: NBER/Dehejia canonical .dta files (http://users.nber.org/~rdehejia/data/)
    nsw_dw.dta       — experimental NSW (185 treated + 260 experimental controls)
    psid_controls.dta — 2490 PSID non-experimental controls
    cps_controls.dta  — 15992 CPS1 non-experimental controls
  Read natively with pandas.read_stata (no pyreadstat needed).

Conditions:
  A — experimental NSW: treated vs experimental controls (true ATE on re78 ~ +$1.6-1.8k)
  B — NSW-treated vs PSID controls (observational, severe selection confounding)
  C — NSW-treated vs CPS controls  (observational, severe selection confounding)

Method (per prereg):
  - adjusted = T-learner on X = {age, education, black, hispanic, married, nodegree, re75}
    (NOT re74, which is the negative-control outcome).
  - estimate() auto-detects continuous outcome (earnings) -> LinearRegression path. We do
    NOT coerce to binary.
  - Negative-control guard: NC outcome = re74 (1974 earnings, PRE-treatment; training was
    1976-77, so treatment cannot cause it). floor=0.05, ratio=1.5 (the validated 3-part gate).
  - STANDARDIZE: earnings are large/continuous. We divide BOTH re78 and re74 by a single
    common scale = the pooled SD of re78 in that condition. This puts the guard's 0.05 floor
    on a comparable (SD-of-outcome) scale to the synthetic validation, and keeps re74 and re78
    on the SAME scale so the guard's main-vs-bias ratio rule and COCA subtraction are valid.
  - COCA = adjusted_ate(re78) - adjusted_ate(re74), sign. Reported in raw $ and standardized.

One scored run. No estimator/threshold tuning. Raw numbers reported even if refuted.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
# reuse the validated engine core
sys.path.insert(0, str(HERE.parent.parent / "empirical-uplift-spike"))
from causal_estimator import estimate, support_check, negative_control_guard  # noqa: E402

DATA = HERE / "data"
COVARIATES = ["age", "education", "black", "hispanic", "married", "nodegree", "re75"]
NC = "re74"
OUTCOME = "re78"
FLOOR = 0.05
RATIO = 1.5


def load():
    exp = pd.read_stata(DATA / "nsw_dw.dta")          # has treat=1 (185) and treat=0 (260)
    psid = pd.read_stata(DATA / "psid_controls.dta")  # all treat=0
    cps = pd.read_stata(DATA / "cps_controls.dta")    # all treat=0
    treated = exp[exp["treat"] == 1].copy()
    exp_ctrl = exp[exp["treat"] == 0].copy()
    cond = {
        "A_experimental":      pd.concat([treated, exp_ctrl], ignore_index=True),
        "B_psid_observational": pd.concat([treated, psid], ignore_index=True),
        "C_cps_observational":  pd.concat([treated, cps], ignore_index=True),
    }
    for df in cond.values():
        df["treat"] = df["treat"].astype(int)
    return cond


def run_condition(name: str, df: pd.DataFrame) -> dict:
    # common scale = pooled SD of re78; standardize BOTH outcomes by it
    scale = float(df[OUTCOME].std(ddof=1))
    df = df.copy()
    df["re78_z"] = df[OUTCOME] / scale
    df["re74_z"] = df[NC] / scale

    sup = support_check(df, "treat", OUTCOME, COVARIATES)

    # raw-$ effects
    est_raw = estimate(df, "treat", OUTCOME, COVARIATES)       # treatment -> re78 ($)
    nc_raw = estimate(df, "treat", NC, COVARIATES)             # treatment -> re74 ($) placebo

    # standardized effects
    est_z = estimate(df, "treat", "re78_z", COVARIATES)
    nc_z = estimate(df, "treat", "re74_z", COVARIATES)

    # guard on the standardized scale, NC = re74_z, floor=0.05 ratio=1.5
    guard = negative_control_guard(df, "treat", "re78_z", "re74_z",
                                   COVARIATES, floor=FLOOR, ratio=RATIO)

    coca_raw = est_raw.t_learner_ate - nc_raw.t_learner_ate
    coca_z = est_z.t_learner_ate - nc_z.t_learner_ate

    return {
        "n": int(len(df)),
        "n_treat": int((df["treat"] == 1).sum()),
        "n_control": int((df["treat"] == 0).sum()),
        "re78_scale_used_for_standardization": scale,
        "overlap_fraction": est_raw.overlap_fraction,
        "support_supportable": sup.supportable,
        "support_reasons": sup.reasons,
        # raw dollars
        "naive_ate_re78_raw$": est_raw.naive_ate,
        "adjusted_ate_re78_raw$": est_raw.t_learner_ate,
        "ipw_ate_re78_raw$": est_raw.ipw_ate,
        "naive_placebo_re74_raw$": nc_raw.naive_ate,
        "adjusted_placebo_re74_raw$": nc_raw.t_learner_ate,
        "coca_raw$": coca_raw,
        "coca_sign_raw": "positive" if coca_raw > 0 else "negative",
        # standardized (re78-SD units)
        "naive_ate_re78_std": est_z.naive_ate,
        "adjusted_ate_re78_std": est_z.t_learner_ate,
        "adjusted_placebo_re74_std": nc_z.t_learner_ate,
        "coca_std": coca_z,
        "coca_sign_std": "positive" if coca_z > 0 else "negative",
        # guard decision
        "guard_nc_residual_std": guard.neg_control_effect,
        "guard_floor": guard.floor,
        "guard_ratio": RATIO,
        "guard_trips": guard.trips,
        "guard_confidence": guard.confidence,
        "guard_reason": guard.reason,
        # signs
        "naive_sign_re78": "positive" if est_raw.naive_ate > 0 else "negative",
        "adjusted_sign_re78": est_raw.sign_adjusted,
    }


def main():
    cond = load()
    results = {name: run_condition(name, df) for name, df in cond.items()}

    # ---- scored prediction evaluation (sealed) ----
    A, B, C = results["A_experimental"], results["B_psid_observational"], results["C_cps_observational"]

    # P1 Specificity on clean RCT (A): guard does NOT trip AND adjusted+COCA positive
    p1 = (not A["guard_trips"]
          and A["adjusted_sign_re78"] == "positive"
          and A["coca_sign_std"] == "positive")

    # P2 Detection on B,C: naive sign WRONG (negative) AND re74 placebo LARGE AND guard TRIPS
    def detect(r):
        return (r["naive_sign_re78"] == "negative"
                and abs(r["adjusted_placebo_re74_std"]) > FLOOR
                and r["guard_trips"])
    p2 = detect(B) and detect(C)

    # P3 COCA recovery (leaned NO): does COCA flip to experimental positive on B AND C?
    p3_coca_recovers = (B["coca_sign_std"] == "positive" and C["coca_sign_std"] == "positive")

    verdict = {
        "P1_specificity_A_PASS": bool(p1),
        "P2_detection_BC_PASS": bool(p2),
        "P3_coca_recovers_positive_on_BC": bool(p3_coca_recovers),
        "GUARD_PROMOTED": bool(p1 and p2),   # prereg verdict mapping
        "note": "P3 leaned NO; recovery would be a STRONGER-than-bet result. "
                "Guard PROMOTED iff P1 and P2 both hold.",
    }

    out = {
        "benchmark": "LaLonde 1986 / Dehejia-Wahba 1999 NSW",
        "data_source": "NBER/Dehejia canonical .dta (users.nber.org/~rdehejia/data) "
                       "via pandas.read_stata",
        "interpreter": sys.version.split()[0],
        "covariates_adjusted": COVARIATES,
        "negative_control_outcome": NC,
        "outcome": OUTCOME,
        "standardization": "both re78 and re74 divided by pooled SD(re78) per condition",
        "guard_params": {"floor": FLOOR, "ratio": RATIO},
        "conditions": results,
        "verdict": verdict,
    }

    out_path = HERE / "lalonde_promotion_result.json"
    out_path.write_text(json.dumps(out, indent=2))

    # ---- human-readable raw report ----
    def line(r, key, fmt="{:+.1f}"):
        return fmt.format(r[key])

    print("=" * 78)
    print("LaLonde NSW PROMOTION TEST — RAW RESULTS (one scored run, no tuning)")
    print("=" * 78)
    for nm, r in results.items():
        print(f"\n--- {nm}  (n={r['n']}, treat={r['n_treat']}, control={r['n_control']}, "
              f"overlap={r['overlap_fraction']:.2f}) ---")
        print(f"  naive ATE re78          : {r['naive_ate_re78_raw$']:+10.1f} $   "
              f"(std {r['naive_ate_re78_std']:+.3f})  [{r['naive_sign_re78']}]")
        print(f"  adjusted ATE re78 (T-lrn): {r['adjusted_ate_re78_raw$']:+10.1f} $   "
              f"(std {r['adjusted_ate_re78_std']:+.3f})  [{r['adjusted_sign_re78']}]")
        print(f"  ipw ATE re78            : {r['ipw_ate_re78_raw$']:+10.1f} $")
        print(f"  re74 PLACEBO naive      : {r['naive_placebo_re74_raw$']:+10.1f} $")
        print(f"  re74 PLACEBO adjusted   : {r['adjusted_placebo_re74_raw$']:+10.1f} $   "
              f"(std {r['adjusted_placebo_re74_std']:+.3f})   floor=±{FLOOR}")
        print(f"  COCA = adj(re78)-adj(re74): {r['coca_raw$']:+10.1f} $   "
              f"(std {r['coca_std']:+.3f})  [{r['coca_sign_std']}]")
        print(f"  GUARD trips={r['guard_trips']}  conf={r['guard_confidence']}")
        print(f"        reason: {r['guard_reason']}")
    print("\n" + "=" * 78)
    print("VERDICT")
    print("=" * 78)
    for k, v in verdict.items():
        print(f"  {k}: {v}")
    print(f"\nwrote {out_path}")


if __name__ == "__main__":
    main()
