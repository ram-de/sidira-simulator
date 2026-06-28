"""
gen_streamly_challenge_v2.py — iter1 challenge: adds a NEGATIVE-CONTROL outcome.

Same self-blinding protocol as v1 (secret os.urandom seed, hidden regime->file shuffle,
sealed key OUTSIDE the worktree). Adds one column `neg_control`: a binary metric with TRUE
treatment effect = 0, driven by the SAME confound signal as the real outcome (observed
`activity` for observed-confounding regimes; latent `U` for the unobserved regimes). The
predictor estimates treatment->neg_control; a non-zero estimate reveals residual confounding
overlap can't see.

  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/gen_streamly_challenge_v2.py
"""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import numpy as np
import pandas as pd

SUF = os.environ.get("CHALLENGE_SUFFIX", "v2")     # iter1=v2; iter2 held-out=v3
HERE = Path(__file__).resolve().parent
OUTDIR = HERE / ".data" / f"synthetic_streamly_{SUF}"
INDEX = HERE / f"synthetic_streamly_{SUF}_index.json"
SHA = HERE / f"SYNTHETIC_STREAMLY_{SUF.upper()}_ANSWERS.sha256"
SEALED = Path.home() / f"streamly_challenge_{SUF}_SEALED.json"

COVARS = ["tenure_days", "plays_28d", "watch_minutes_28d", "avg_session_min",
          "titles_started_28d", "completion_rate", "plan_tier", "device_mobile",
          "region_code", "notifications_on"]
TREAT, OUT, NC = "got_feature", "outcome", "neg_control"


def sigmoid(x): return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

def base(rng, n):
    plays = rng.poisson(np.clip(rng.gamma(2.0, 6, n), 0, None)) + 1
    watch = plays * rng.gamma(2.0, 8, n)
    session = rng.gamma(2.0, 6, n); completion = rng.beta(2, 2, n)
    df = pd.DataFrame({"tenure_days": rng.gamma(2.0, 180, n), "plays_28d": plays,
                       "watch_minutes_28d": watch, "avg_session_min": session,
                       "titles_started_28d": rng.poisson(np.clip(plays * 0.4, 0, None)) + 1,
                       "completion_rate": completion, "plan_tier": rng.integers(0, 3, n),
                       "device_mobile": rng.integers(0, 2, n), "region_code": rng.integers(0, 8, n),
                       "notifications_on": rng.integers(0, 2, n)})
    a = np.log1p(plays) + np.log1p(watch) / 2 + completion + session / 10
    return df, (a - a.mean()) / a.std()

def neg_control(rng, signal):
    """binary metric, TRUE effect of treatment = 0, driven by the confound `signal`."""
    s = (signal - signal.mean()) / signal.std()
    return rng.binomial(1, sigmoid(-0.1 + 1.3 * s))

def fin_bin(df, rng, lin, tau, T, signal):
    p0, p1 = sigmoid(lin), sigmoid(lin + tau)
    df[TREAT] = T.astype(int); df[OUT] = rng.binomial(1, np.where(T == 1, p1, p0)).astype(int)
    df[NC] = neg_control(rng, signal).astype(int)
    return df, "binary", float((p1 - p0).mean())

def fin_cont(df, rng, mu, tau_vec, T, signal):
    df[TREAT] = T.astype(int); df[OUT] = mu + np.where(T == 1, tau_vec, 0.0) + rng.normal(0, 1, len(df))
    df[NC] = neg_control(rng, signal).astype(int)
    return df, "continuous", float(np.mean(tau_vec))


def r_clean_rct_moderate(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, 0.5, n)
    df, ot, ate = fin_bin(df, rng, -0.2 + 0.7 * a, 0.6, T, a)
    return df, dict(regime="clean_rct_moderate", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_clean_rct_small(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, 0.5, n)
    df, ot, ate = fin_cont(df, rng, 30 + 8 * a, np.full(n, 0.4), T, a)
    return df, dict(regime="clean_rct_small", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_true_null_confounded(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.4 * a))
    df, ot, ate = fin_bin(df, rng, -0.1 + 1.0 * a, 0.0, T, a)
    return df, dict(regime="true_null_confounded", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_confounded_observed_moderate(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.2 * a))
    df, ot, ate = fin_bin(df, rng, -0.2 + 0.9 * a, 0.5, T, a)
    return df, dict(regime="confounded_observed_moderate", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_confounded_sign_flip(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.6 * a))
    df, ot, ate = fin_bin(df, rng, -0.1 + 1.3 * a, -0.35, T, a)
    return df, dict(regime="confounded_sign_flip", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_confounded_strong_poor_overlap(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(3.2 * a))
    df, ot, ate = fin_bin(df, rng, -0.2 + 0.8 * a, 0.5, T, a)
    return df, dict(regime="confounded_strong_poor_overlap", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_confounded_nonlinear(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.1 * a))
    mu = 25 + 6 * a + 5 * a**2 + 4 * (a * (df["completion_rate"].to_numpy() - 0.5))
    df, ot, ate = fin_cont(df, rng, mu, np.full(n, 0.6), T, a)
    return df, dict(regime="confounded_nonlinear", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_heterogeneous(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.0 * a))
    df, ot, ate = fin_cont(df, rng, 28 + 7 * a, np.where(a < 0, 0.9, -0.2), T, a)
    return df, dict(regime="heterogeneous_net_positive", outcome_type=ot, true_ate=ate, nc_unobserved=False)

def r_unobserved_no_proxy(rng, n):
    df, a = base(rng, n); U = rng.normal(0, 1, n); T = rng.binomial(1, sigmoid(1.8 * U))
    df, ot, ate = fin_bin(df, rng, -0.1 + 1.4 * U, -0.3, T, U)   # neg_control driven by U
    return df, dict(regime="unobserved_no_proxy", outcome_type=ot, true_ate=ate, nc_unobserved=True)

def r_unobserved_with_proxy(rng, n):
    df, a = base(rng, n); U = rng.normal(0, 1, n)
    df["completion_rate"] = np.clip(sigmoid(U + rng.normal(0, 0.6, n)), 0, 1)
    df["watch_minutes_28d"] = df["watch_minutes_28d"].to_numpy() * (1 + 0.5 * sigmoid(U))
    T = rng.binomial(1, sigmoid(1.6 * U))
    df, ot, ate = fin_bin(df, rng, -0.1 + 1.2 * U, -0.3, T, U)
    return df, dict(regime="unobserved_with_proxy", outcome_type=ot, true_ate=ate, nc_unobserved=True)

REGIMES = [r_clean_rct_moderate, r_clean_rct_small, r_true_null_confounded,
           r_confounded_observed_moderate, r_confounded_sign_flip,
           r_confounded_strong_poor_overlap, r_confounded_nonlinear, r_heterogeneous,
           r_unobserved_no_proxy, r_unobserved_with_proxy]


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    secret = int.from_bytes(os.urandom(16), "big")
    master = np.random.default_rng(secret)
    order = list(range(len(REGIMES))); master.shuffle(order)
    sizes = master.integers(8000, 30000, len(REGIMES))
    index, answers = [], []
    for file_no, (ri, n) in enumerate(zip(order, sizes), start=1):
        sub = np.random.default_rng(master.integers(0, 2**63))
        df, truth = REGIMES[ri](sub, int(n))
        df = df[COVARS + [TREAT, OUT, NC]]
        fname = f"dataset_{file_no:02d}.csv"; df.to_csv(OUTDIR / fname, index=False)
        index.append(dict(filename=fname, n_rows=int(n), treatment_col=TREAT, outcome_col=OUT,
                          neg_control_col=NC, outcome_type=truth["outcome_type"], covariate_cols=COVARS))
        band = 0.003 if truth["outcome_type"] == "binary" else 0.05
        ts = "null" if abs(truth["true_ate"]) < band else ("positive" if truth["true_ate"] > 0 else "negative")
        answers.append(dict(filename=fname, true_winner=("treatment" if ts == "positive"
                            else "control" if ts == "negative" else "null"), true_sign=ts, **truth))
    INDEX.write_text(json.dumps({"datasets": index}, indent=2))
    payload = json.dumps({"generator": "claude-self-blind-v2", "secret_seed": str(secret),
                          "datasets": answers}, indent=2)
    SEALED.write_text(payload); digest = hashlib.sha256(payload.encode()).hexdigest()
    SHA.write_text(f"{digest}  {SEALED.name}\n")
    print(f"datasets={len(index)} sealed={SEALED} sha256={digest}")


if __name__ == "__main__":
    main()
