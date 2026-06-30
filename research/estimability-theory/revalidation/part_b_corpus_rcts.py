"""
part_b_corpus_rcts.py — Part B of PREREG_FIX_REVALIDATION.md (sealed; run once, no tuning).

Real clean RANDOMIZED RCTs => no confounding => SPECIFICITY + sign-recovery test:
  - empirical adjusted (T-learner) estimate should recover the PUBLISHED directional sign (P4)
  - the FIXED negative-control guard should NOT trip (NC residual ~= 0) because randomization
    balances the NC (P5). Any HIDDEN-confounding trip on a clean RCT is direct real-data
    evidence against Part A prediction-3's specificity, reported loudly.

FIXED guard rule (frozen, threshold 0.8 not tuned): compute the NC residual by adjusting the NC
on the covariate set EXCEPT any covariate with |corr(covariate, NC)| > 0.8 (those near-collinear
twins stay in the MAIN outcome model, only the NC adjustment drops them). 3-part gate floor=0.05,
ratio=1.5, identical to causal_estimator.negative_control_guard / lalonde_fix.

Reuses research/empirical-uplift-spike/causal_estimator.estimate. One run; report raw.
  /opt/homebrew/bin/python3.11 research/estimability-theory/revalidation/part_b_corpus_rcts.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent.parent          # worktree root
EUS = REPO / "research" / "empirical-uplift-spike"
sys.path.insert(0, str(EUS))
from causal_estimator import estimate      # noqa: E402

DATA = HERE / ".data"
FLOOR, RATIO, COLLINEAR_THRESH = 0.05, 1.5, 0.8
OUT = HERE / "part_b_result.json"


def _ci_diff_prop(df, T, Y):
    """Rough 95% CI for the naive binary diff-in-means (treatment - control)."""
    y1 = df.loc[df[T] == 1, Y].to_numpy(float); y0 = df.loc[df[T] == 0, Y].to_numpy(float)
    p1, p0, n1, n0 = y1.mean(), y0.mean(), len(y1), len(y0)
    se = np.sqrt(p1 * (1 - p1) / n1 + p0 * (1 - p0) / n0)
    d = p1 - p0
    return float(d), [float(d - 1.96 * se), float(d + 1.96 * se)]


def run_dataset(name, df, T, Y, X, nc_col, nc_continuous, published_sign, notes):
    df = df.reset_index(drop=True).copy()
    # standardize a continuous NC so the 0.05 floor means "5% of an SD" (matches lalonde_fix)
    nc_used = nc_col
    if nc_continuous:
        nc_used = nc_col + "_z"
        df[nc_used] = df[nc_col] / float(df[nc_col].std(ddof=1))

    naive, naive_ci = _ci_diff_prop(df, T, Y)

    # main adjusted effect on the outcome — full covariate set X (NC excluded from X by construction)
    main = estimate(df, T, Y, X)
    main_ate = float(main.t_learner_ate)

    # FIXED rule: drop covariates near-collinear with the NC from the NC adjustment set only
    corrs = {x: float(np.corrcoef(df[x].to_numpy(float), df[nc_used].to_numpy(float))[0, 1]) for x in X}
    dropped = [x for x in X if abs(corrs[x]) > COLLINEAR_THRESH]
    X_nc = [x for x in X if x not in dropped]
    nc_est = estimate(df, T, nc_used, X_nc)
    nc_resid = float(nc_est.t_learner_ate)

    # 3-part gate (floor + ratio), separating the two abstain reasons
    nc_mag, main_mag = abs(nc_resid), abs(main_ate)
    hidden = bool(nc_mag > FLOOR)                       # NC residual => specificity-relevant false alarm
    indistinct = bool(main_mag <= RATIO * nc_mag)       # effect not bigger than bias => can't tell from null
    trips = bool(hidden or indistinct)

    measured_sign = "positive" if main_ate > 0 else "negative"
    sign_match = (None if published_sign is None
                  else bool(measured_sign == published_sign))
    if hidden:
        reason = f"NC '{nc_col}' residual {nc_resid:+.4f} > |{FLOOR}|: HIDDEN confounding (false alarm on a clean RCT)"
    elif indistinct:
        reason = (f"main {main_ate:+.4f} not > {RATIO}x NC bias ({nc_resid:+.4f}): "
                  "indistinguishable from null (effect too small, NOT a false alarm)")
    else:
        reason = f"main {main_ate:+.4f} clears {RATIO}x NC bias ({nc_resid:+.4f}): estimate trusted"

    return {
        "source": name,
        "n": int(len(df)),
        "treatment": T, "outcome": Y,
        "covariates": X,
        "neg_control": nc_col, "nc_continuous": bool(nc_continuous),
        "nc_covariates_collinear_dropped": dropped,
        "max_cov_nc_corr": round(max((abs(v) for v in corrs.values()), default=0.0), 3),
        "naive_ate": round(naive, 5), "naive_95ci": [round(c, 5) for c in naive_ci],
        "adjusted_ate_tlearner": round(main_ate, 5),
        "adjusted_ipw_ate": round(float(main.ipw_ate), 5),
        "measured_sign": measured_sign,
        "published_sign": published_sign,
        "sign_match": sign_match,
        "nc_residual": round(nc_resid, 5),
        "floor": FLOOR, "ratio": RATIO,
        "hidden_confounding_flag": hidden,
        "indistinct_flag": indistinct,
        "guard_trips": trips,
        "guard_reason": reason,
        "notes": notes,
    }


# --------------------------------------------------------------------------- loaders
def load_hillstrom():
    df = pd.read_csv(EUS / ".data" / "hillstrom.csv")
    df = df[df["segment"].isin(["Womens E-Mail", "No E-Mail"])].copy()
    df["T"] = (df["segment"] == "Womens E-Mail").astype(int)
    df["log_history"] = np.log1p(df["history"])
    dums = pd.get_dummies(df[["channel", "zip_code"]], drop_first=True).astype(float)
    dums.columns = [str(c) for c in dums.columns]
    df = pd.concat([df.reset_index(drop=True), dums.reset_index(drop=True)], axis=1)
    X = ["recency", "log_history", "newbie", "womens"] + list(dums.columns)  # NC=mens excluded
    return dict(name="hillstrom", df=df, T="T", Y="visit", X=X, nc_col="mens",
                nc_continuous=False, published_sign="positive",
                notes="Womens E-Mail vs No E-Mail; true RCT, email lifts visits ~+4.5pp. "
                      "NC=mens (pre-treatment mens-merch buyer flag, email cannot cause it).")


def load_gotv():
    df = pd.read_csv(DATA / "gotv_social.csv")
    df = df[df["messages"].isin(["Neighbors", "Control"])].copy()
    df["T"] = (df["messages"] == "Neighbors").astype(int)
    df["male"] = (df["sex"] == "male").astype(float)
    df["age"] = 2006.0 - df["yearofbirth"].astype(float)
    df["hhsize"] = df["hhsize"].astype(float)
    X = ["male", "age", "hhsize"]                          # NC=primary2004 excluded
    return dict(name="gotv_ggl2008", df=df, T="T", Y="primary2006", X=X, nc_col="primary2004",
                nc_continuous=False, published_sign="positive",
                notes="Gerber-Green-Larimer 2008 social-pressure GOTV; Neighbors mailer vs Control, "
                      "published ~+8pp turnout. NC=primary2004 (voted in 2004 primary, BEFORE the "
                      "2006 mailer => mailer cannot cause it).")


def load_karlan():
    k = pd.read_stata(DATA / "karlan_aer.dta", convert_categoricals=False)
    cols = ["treatment", "gave", "hpa", "freq", "years", "dormant", "female", "couple", "pwhite", "mrm2"]
    k = k[cols].apply(pd.to_numeric, errors="coerce").dropna().reset_index(drop=True)
    X = ["freq", "years", "dormant", "female", "couple", "pwhite", "mrm2"]   # NC=hpa excluded
    return dict(name="karlan_list2007", df=k, T="treatment", Y="gave", X=X, nc_col="hpa",
                nc_continuous=True, published_sign="positive",
                notes="Karlan-List 2007 charitable match (any match offer vs control); published "
                      "small + on prob(gave) (~+0.4pp). NC=hpa (highest previous contribution $, "
                      "fixed pre-experiment). dropna on used cols.")


def load_orange():
    df = pd.read_csv(DATA / "orange_belgium.csv")
    X = [f"PC{i}" for i in range(1, 21)]                   # NC=PC21 excluded
    return dict(name="orange_belgium_openml45580", df=df, T="t", Y="y", X=X, nc_col="PC21",
                nc_continuous=True, published_sign=None,
                notes="Orange-Belgium telecom retention RCT (PCA-anonymized covariates). Documented "
                      "BACKFIRE/null: retention outreach does not help (can raise churn). published_sign "
                      "left None (counter-intuitive null/backfire) — report measured sign, do not force. "
                      "NC=PC21 (an arbitrary pre-treatment PCA component, balanced by randomization).")


def main():
    specs = [load_hillstrom(), load_gotv(), load_karlan(), load_orange()]
    results = []
    for s in specs:
        results.append(run_dataset(s["name"], s["df"], s["T"], s["Y"], s["X"], s["nc_col"],
                                   s["nc_continuous"], s["published_sign"], s["notes"]))

    out = {
        "part": "B — corpus RCT breadth (PREREG_FIX_REVALIDATION.md)",
        "prereg_sha256_file": "research/estimability-theory/PREREG_FIX_REVALIDATION.md.sha256",
        "interpreter": sys.version.split()[0],
        "guard_rule": {"collinear_drop_threshold": COLLINEAR_THRESH, "floor": FLOOR, "ratio": RATIO,
                       "note": "FIXED guard: NC adjusted on covariates EXCEPT |corr(cov,NC)|>0.8"},
        "datasets_loaded": [r["source"] for r in results],
        "datasets_skipped": {
            "information_r_insurance": "only available as R binary (.rda); pyreadr/pyreadstat not "
                                       "installed — per spec, skip R-binary-only sources.",
            "bertrand2010": "optional/time-permitting; not attempted (target >=4 met with 4 loaded).",
        },
        "results": results,
    }

    # scorecards
    clear = [r for r in results if r["published_sign"] is not None]
    sign_pass = [r for r in clear if r["sign_match"]]
    hidden_trips = [r for r in results if r["hidden_confounding_flag"]]
    out["scorecard"] = {
        "P4_sign_recovery": f"{len(sign_pass)}/{len(clear)} clear-effect RCTs recover published sign",
        "P4_verdict": "PASS" if len(sign_pass) == len(clear) else "PARTIAL/FAIL",
        "P5_no_false_alarm": f"{len(hidden_trips)}/{len(results)} datasets HIDDEN-trip (false alarm)",
        "P5_verdict": "PASS" if len(hidden_trips) == 0 else "FAIL — false alarm on a clean RCT",
        "note": "indistinct-trips on genuine ~null RCTs (Orange backfire; Karlan tiny effect) are NOT "
                "specificity failures — only hidden_confounding_flag is the P5-relevant false alarm.",
    }
    OUT.write_text(json.dumps(out, indent=2))

    print("=" * 84)
    print("PART B — corpus RCTs (FIXED NC-collinearity guard, run once, raw)")
    print("=" * 84)
    for r in results:
        print(f"\n--- {r['source']} (n={r['n']})  T={r['treatment']} -> Y={r['outcome']} ---")
        print(f"  naive      {r['naive_ate']:+.5f}  95%CI {r['naive_95ci']}")
        print(f"  adjusted   T-learner {r['adjusted_ate_tlearner']:+.5f}  IPW {r['adjusted_ipw_ate']:+.5f}"
              f"  -> sign {r['measured_sign']} (published {r['published_sign']}) match={r['sign_match']}")
        print(f"  NC={r['neg_control']}  collinear-dropped={r['nc_covariates_collinear_dropped']} "
              f"(max|corr|={r['max_cov_nc_corr']})  residual={r['nc_residual']:+.5f} (floor ±{FLOOR})")
        print(f"  hidden={r['hidden_confounding_flag']} indistinct={r['indistinct_flag']} "
              f"-> TRIPS={r['guard_trips']}")
        print(f"  {r['guard_reason']}")
    print("\n" + "=" * 84)
    print("SCORECARD")
    for k, v in out["scorecard"].items():
        print(f"  {k}: {v}")
    print(f"\nwrote {OUT}")


if __name__ == "__main__":
    main()
