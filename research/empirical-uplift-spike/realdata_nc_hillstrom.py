"""
realdata_nc_hillstrom.py — iter3: negative-control guard on REAL Hillstrom RCT.

Design sealed in research/engine-strength-campaign/PREREG_ITER3_NCREAL.md (sha256 96a2e6e8).
T = Womens E-Mail. Main Y = visit. Negative control = `mens` (pre-treatment, email cannot cause
it). Adjustment set X excludes BOTH `history` (the deliberately-hidden confounder) and `mens`.
Two conditions: (A) clean RCT, (B) inject selection on hidden log_history. Same frozen estimator
+ 0.05 negative-control floor from iter2.

  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/realdata_nc_hillstrom.py
"""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from causal_estimator import estimate            # noqa: E402
from realdata_hillstrom import load              # noqa: E402  (reuse the loader)

NC_BAND = 0.05
BETA, SEED = 1.5, 20260629
OUT = HERE / "realdata_nc_hillstrom_result.json"


def sigmoid(x): return 1.0 / (1.0 + np.exp(-x))


ALL_PRETREAT = ["recency", "womens", "newbie", "mens"]


def adjustment_frame(df, nc_col):
    """X = pre-treatment numerics + channel/zip dummies, EXCLUDING history (hidden) and the NC col."""
    nums = [c for c in ["recency", "womens", "newbie", "mens"] if c != nc_col]
    base = df[nums].astype(float).reset_index(drop=True)
    cat = pd.get_dummies(df[["channel", "zip_code"]], drop_first=True).astype(float).reset_index(drop=True)
    X = pd.concat([base, cat], axis=1)
    X.columns = [str(c) for c in X.columns]
    return X


def condition(df, inject, nc_col="mens", seed=SEED):
    df = df.reset_index(drop=True)
    if inject:
        h = (df["log_history"].to_numpy() - df["log_history"].mean()) / df["log_history"].std()
        rng = np.random.default_rng(seed)
        keep_p = np.where(df["T"].to_numpy() == 1, sigmoid(-BETA * h), sigmoid(BETA * h))
        df = df.loc[rng.random(len(df)) < keep_p].reset_index(drop=True)
    X = adjustment_frame(df, nc_col)
    xcols = list(X.columns)
    frame = pd.concat([df[["T", "visit", nc_col]].reset_index(drop=True), X], axis=1)
    main = estimate(frame, "T", "visit", xcols)        # T -> visit (history hidden from X)
    nc = estimate(frame, "T", nc_col, xcols)           # T -> negative control
    hist = df["history"].to_numpy()
    return {
        "condition": "injected_hidden" if inject else "clean_rct",
        "n": int(len(df)),
        "history_treat_vs_control": [round(float(hist[df["T"].to_numpy() == 1].mean()), 1),
                                     round(float(hist[df["T"].to_numpy() == 0].mean()), 1)],
        "main_visit_ate_pp": round(main.t_learner_ate * 100, 3),
        "main_naive_pp": round(main.naive_ate * 100, 3),
        "neg_control_ate": round(nc.t_learner_ate, 4),
        "neg_control_naive": round(nc.naive_ate, 4),
        "nc_tripped": bool(abs(nc.t_learner_ate) > NC_BAND),
    }


def main():
    df = load()
    clean = condition(df, inject=False)
    inj = condition(df, inject=True)
    res = {"design_sha": "96a2e6e8", "true_email_lift_pp_approx": 4.52,
           "nc_band": NC_BAND, "clean_rct": clean, "injected_hidden": inj}
    OUT.write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))

    p1 = (not clean["nc_tripped"]) and abs(clean["neg_control_ate"]) < NC_BAND
    p2 = abs(inj["neg_control_ate"]) > abs(clean["neg_control_ate"])
    p3 = inj["nc_tripped"]
    print(f"\nP1 specificity (clean does NOT trip): {'PASS' if p1 else 'FAIL'} "
          f"(clean nc={clean['neg_control_ate']:+.4f})")
    print(f"P2 sensitivity (injected nc > clean nc): {'PASS' if p2 else 'FAIL'} "
          f"(injected nc={inj['neg_control_ate']:+.4f})")
    print(f"P3 trips on injected (|nc|>{NC_BAND}): {'PASS' if p3 else 'FAIL'}")
    print(f"main visit estimate: clean {clean['main_visit_ate_pp']:+.2f}pp  "
          f"injected {inj['main_visit_ate_pp']:+.2f}pp (true ~+4.52pp)")
    verdict = ("LEAD (real-data replication)" if (p1 and p2 and p3) else
               "MECH-ONLY/partial — directional but floor doesn't transfer (proxy absorption?)"
               if (p1 and p2) else "NULL")
    print(f"VERDICT (preregistered mens/seed {SEED}): {verdict}")

    # --- Adversarial robustness: other negative controls x seeds. Report ALL, pass or fail. ---
    print("\nADVERSARIAL SWEEP (clean must NOT trip; injected SHOULD trip):")
    grid = []
    for nc_col in ["mens", "newbie", "womens", "recency"]:
        for sd in (20260629, 7, 99):
            c = condition(df, False, nc_col, sd)
            i = condition(df, True, nc_col, sd)
            spec = bool(not c["nc_tripped"])
            sens = bool(i["nc_tripped"] and abs(i["neg_control_ate"]) > abs(c["neg_control_ate"]))
            grid.append((nc_col, sd, c["neg_control_ate"], i["neg_control_ate"], spec, sens))
            print(f"  nc={nc_col:8} seed={sd:<9} clean={c['neg_control_ate']:+.4f} "
                  f"inj={i['neg_control_ate']:+.4f}  spec={'Y' if spec else 'N'} "
                  f"sens={'Y' if sens else 'N'}")
    spec_rate = sum(g[4] for g in grid) / len(grid)
    sens_rate = sum(g[5] for g in grid) / len(grid)
    res["adversarial"] = {"specificity_rate": round(spec_rate, 3), "sensitivity_rate": round(sens_rate, 3),
                          "grid": [{"nc": g[0], "seed": g[1], "clean": g[2], "inj": g[3],
                                    "spec": g[4], "sens": g[5]} for g in grid]}
    OUT.write_text(json.dumps(res, indent=2))
    print(f"  -> specificity {spec_rate:.0%}, sensitivity {sens_rate:.0%} across "
          f"{len(grid)} (negative-control x seed) cells")


if __name__ == "__main__":
    main()
