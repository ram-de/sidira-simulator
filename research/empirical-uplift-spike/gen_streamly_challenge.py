"""
gen_streamly_challenge.py — SELF-BLINDING generator for the Synthetic Streamly Challenge.

codex (the intended independent generator) wedged, so this generates the 10-regime benchmark
WITHOUT codex while preserving a real blind:
  * a SECRET seed is drawn from os.urandom and NEVER printed;
  * the 10 regimes are SHUFFLED across file numbers by that secret;
  * the sealed answer key (regimes + true effects + the secret) is written OUTSIDE the
    worktree to ~/streamly_challenge_SEALED.json, which the predictor commits NOT to read;
  * only the dataset count + sealed path + sha256 are printed.
So the author knows the generation LOGIC but not which file is which regime, nor the realized
signs/magnitudes — the frozen causal_estimator runs blind.

All 10 CSVs share an IDENTICAL column schema + generic names (got_feature / outcome) so the
index cannot leak the regime. Honest label: self-generated => MECH-ONLY (mechanism test),
never real-world validation.

Deps: numpy, pandas. Run once:
  /opt/homebrew/bin/python3.11 research/empirical-uplift-spike/gen_streamly_challenge.py
"""
from __future__ import annotations
import hashlib, json, os
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUTDIR = HERE / ".data" / "synthetic_streamly"
INDEX = HERE / "synthetic_streamly_index.json"
SHA = HERE / "SYNTHETIC_STREAMLY_ANSWERS.sha256"
SEALED = Path.home() / "streamly_challenge_SEALED.json"   # OUTSIDE the worktree; do not read

COVARS = ["tenure_days", "plays_28d", "watch_minutes_28d", "avg_session_min",
          "titles_started_28d", "completion_rate", "plan_tier", "device_mobile",
          "region_code", "notifications_on"]
TREAT, OUT = "got_feature", "outcome"


def sigmoid(x): return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))

def base(rng, n):
    """Shared covariate block + a standardized activity index used for confounding."""
    tenure = rng.gamma(2.0, 180, n)
    plays = rng.poisson(np.clip(rng.gamma(2.0, 6, n), 0, None)) + 1
    watch = plays * rng.gamma(2.0, 8, n)
    session = rng.gamma(2.0, 6, n)
    titles = rng.poisson(np.clip(plays * 0.4, 0, None)) + 1
    completion = rng.beta(2, 2, n)
    plan = rng.integers(0, 3, n)
    mobile = rng.integers(0, 2, n)
    region = rng.integers(0, 8, n)
    notif = rng.integers(0, 2, n)
    df = pd.DataFrame({"tenure_days": tenure, "plays_28d": plays, "watch_minutes_28d": watch,
                       "avg_session_min": session, "titles_started_28d": titles,
                       "completion_rate": completion, "plan_tier": plan, "device_mobile": mobile,
                       "region_code": region, "notifications_on": notif})
    a = (np.log1p(plays) + np.log1p(watch) / 2 + completion + session / 10)
    activity = (a - a.mean()) / a.std()
    return df, activity

def _ate_binary(lin, tau):
    p0, p1 = sigmoid(lin), sigmoid(lin + tau)
    return float((p1 - p0).mean())

def finish_binary(df, rng, lin, tau, T):
    p0, p1 = sigmoid(lin), sigmoid(lin + tau)
    Y = rng.binomial(1, np.where(T == 1, p1, p0))
    df[TREAT] = T.astype(int); df[OUT] = Y.astype(int)
    return df, "binary", float((p1 - p0).mean())

def finish_continuous(df, rng, mu, tau_vec, T):
    Y = mu + np.where(T == 1, tau_vec, 0.0) + rng.normal(0, 1.0, len(df))
    df[TREAT] = T.astype(int); df[OUT] = Y
    return df, "continuous", float(np.mean(tau_vec))


# ----- 10 regimes. Each: (rng, n) -> (df, truth) ----------------------------- #
def r_clean_rct_moderate(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, 0.5, n)
    lin = -0.2 + 0.7 * a; df, ot, ate = finish_binary(df, rng, lin, 0.6, T)
    return df, dict(regime="clean_rct_moderate", outcome_type=ot, true_ate=ate,
                    assignment_rule="random p=0.5", hidden_driver=None)

def r_clean_rct_small(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, 0.5, n)
    mu = 30 + 8 * a; df, ot, ate = finish_continuous(df, rng, mu, np.full(n, 0.4), T)
    return df, dict(regime="clean_rct_small", outcome_type=ot, true_ate=ate,
                    assignment_rule="random p=0.5", hidden_driver=None)

def r_true_null_confounded(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.4 * a))
    lin = -0.1 + 1.0 * a; df, ot, ate = finish_binary(df, rng, lin, 0.0, T)  # tau=0 -> null
    return df, dict(regime="true_null_confounded", outcome_type=ot, true_ate=ate,
                    assignment_rule="prop=sigmoid(1.4*activity)", hidden_driver=None)

def r_confounded_observed_moderate(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.2 * a))
    lin = -0.2 + 0.9 * a; df, ot, ate = finish_binary(df, rng, lin, 0.5, T)
    return df, dict(regime="confounded_observed_moderate", outcome_type=ot, true_ate=ate,
                    assignment_rule="prop=sigmoid(1.2*activity)", hidden_driver=None)

def r_confounded_sign_flip(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.6 * a))
    lin = -0.1 + 1.3 * a; df, ot, ate = finish_binary(df, rng, lin, -0.35, T)  # true NEGATIVE
    return df, dict(regime="confounded_sign_flip", outcome_type=ot, true_ate=ate,
                    assignment_rule="prop=sigmoid(1.6*activity); strong activity->outcome",
                    hidden_driver=None)

def r_confounded_strong_poor_overlap(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(3.2 * a))  # near-deterministic
    lin = -0.2 + 0.8 * a; df, ot, ate = finish_binary(df, rng, lin, 0.5, T)
    return df, dict(regime="confounded_strong_poor_overlap", outcome_type=ot, true_ate=ate,
                    assignment_rule="prop=sigmoid(3.2*activity) -> poor overlap", hidden_driver=None)

def r_confounded_nonlinear(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.1 * a))
    mu = 25 + 6 * a + 5 * a**2 + 4 * (a * (df["completion_rate"].to_numpy() - 0.5))
    df, ot, ate = finish_continuous(df, rng, mu, np.full(n, 0.6), T)
    return df, dict(regime="confounded_nonlinear", outcome_type=ot, true_ate=ate,
                    assignment_rule="prop=sigmoid(1.1*activity); nonlinear outcome", hidden_driver=None)

def r_heterogeneous(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.0 * a))
    tau = np.where(a < 0, 0.9, -0.2)          # helps low-activity, hurts high; net positive
    mu = 28 + 7 * a; df, ot, ate = finish_continuous(df, rng, mu, tau, T)
    return df, dict(regime="heterogeneous_net_positive", outcome_type=ot, true_ate=ate,
                    assignment_rule="prop=sigmoid(1.0*activity); CATE varies by activity",
                    hidden_driver=None)

def r_unobserved_no_proxy(rng, n):
    df, a = base(rng, n)
    U = rng.normal(0, 1, n)                    # latent, INDEPENDENT of observed covariates
    T = rng.binomial(1, sigmoid(1.8 * U))
    lin = -0.1 + 1.4 * U                       # U drives outcome; observed covars do NOT proxy U
    df, ot, ate = finish_binary(df, rng, lin, -0.3, T)  # true NEGATIVE
    return df, dict(regime="unobserved_no_proxy", outcome_type=ot, true_ate=ate,
                    assignment_rule="latent U drives T and Y; U not observed, no proxy",
                    hidden_driver="independent latent U (omitted)")

def r_unobserved_with_proxy(rng, n):
    df, a = base(rng, n)
    U = rng.normal(0, 1, n)
    # observed covariates carry noisy PROXIES of U (Hillstrom-like)
    df["completion_rate"] = np.clip(sigmoid(U + rng.normal(0, 0.6, n)), 0, 1)
    df["watch_minutes_28d"] = df["watch_minutes_28d"].to_numpy() * (1 + 0.5 * sigmoid(U))
    T = rng.binomial(1, sigmoid(1.6 * U))
    lin = -0.1 + 1.2 * U; df, ot, ate = finish_binary(df, rng, lin, -0.3, T)  # true NEGATIVE
    return df, dict(regime="unobserved_with_proxy", outcome_type=ot, true_ate=ate,
                    assignment_rule="latent U drives T and Y; observed covars proxy U",
                    hidden_driver="latent U (omitted) with observed proxies")

REGIMES = [r_clean_rct_moderate, r_clean_rct_small, r_true_null_confounded,
           r_confounded_observed_moderate, r_confounded_sign_flip,
           r_confounded_strong_poor_overlap, r_confounded_nonlinear, r_heterogeneous,
           r_unobserved_no_proxy, r_unobserved_with_proxy]


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    secret = int.from_bytes(os.urandom(16), "big")          # NEVER printed
    master = np.random.default_rng(secret)
    order = list(range(len(REGIMES)))
    master.shuffle(order)                                    # hidden regime -> file mapping
    sizes = master.integers(8000, 30000, len(REGIMES))

    index, answers = [], []
    for file_no, (regime_idx, n) in enumerate(zip(order, sizes), start=1):
        sub = np.random.default_rng(master.integers(0, 2**63))
        df, truth = REGIMES[regime_idx](sub, int(n))
        df = df[COVARS + [TREAT, OUT]]                       # fixed schema; drop any latent
        fname = f"dataset_{file_no:02d}.csv"
        df.to_csv(OUTDIR / fname, index=False)
        index.append(dict(filename=fname, n_rows=int(n), treatment_col=TREAT,
                          outcome_col=OUT, outcome_type=truth["outcome_type"],
                          covariate_cols=COVARS))
        true_sign = "null" if abs(truth["true_ate"]) < (0.003 if truth["outcome_type"] == "binary"
                                                         else 0.05) else (
                    "positive" if truth["true_ate"] > 0 else "negative")
        answers.append(dict(filename=fname, true_winner=("treatment" if true_sign == "positive"
                            else "control" if true_sign == "negative" else "null"),
                            true_sign=true_sign, **truth))

    INDEX.write_text(json.dumps({"datasets": index}, indent=2))
    payload = json.dumps({"generator": "claude-self-blind", "secret_seed": str(secret),
                          "datasets": answers}, indent=2)
    SEALED.write_text(payload)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    SHA.write_text(f"{digest}  {SEALED.name}\n")
    print(f"datasets={len(index)} sealed={SEALED} sha256={digest}")


if __name__ == "__main__":
    main()
