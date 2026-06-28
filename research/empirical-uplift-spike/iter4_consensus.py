"""
iter4_consensus.py — multi-negative-control CONSENSUS guard, self-blind (sealed bf203e85).

Two phases so blind predictions are committed before unsealing:
  phase 1:  python iter4_consensus.py genpredict   # writes data + blind predictions (commit these)
  phase 2:  python iter4_consensus.py score        # unseal + score (after commit)

Each dataset emits 3 negative controls of different coupling (strong/mid/weak). Compares
single-weak vs consensus(max) using the frozen causal_estimator. Floor 0.05 (from iter2).
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from causal_estimator import estimate  # noqa: E402

OUTDIR = HERE / ".data" / "synthetic_consensus"
INDEX = HERE / "synthetic_consensus_index.json"
SHA = HERE / "SYNTHETIC_CONSENSUS_ANSWERS.sha256"
SEALED = Path.home() / "consensus_challenge_SEALED.json"
PRED = HERE / "synthetic_consensus_predictions.json"
CARD = HERE / "synthetic_consensus_scorecard.md"
FLOOR = 0.05
COVARS = [f"x{i}" for i in range(8)]
TREAT, OUT = "got_feature", "outcome"
NCS = ["nc_strong", "nc_mid", "nc_weak"]
KS = {"nc_strong": 1.3, "nc_mid": 0.7, "nc_weak": 0.25}


def sigmoid(x): return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def base(rng, n):
    cols = {f"x{i}": rng.normal(0, 1, n) for i in range(8)}
    df = pd.DataFrame(cols)
    a = df["x0"].to_numpy() + 0.6 * df["x1"].to_numpy() + 0.4 * df["x2"].to_numpy()
    return df, (a - a.mean()) / a.std()


def add_ncs(df, rng, signal):
    s = (signal - signal.mean()) / signal.std()
    for nc in NCS:
        df[nc] = rng.binomial(1, sigmoid(-0.1 + KS[nc] * s)).astype(int)
    return df


def fin(df, rng, lin, tau, T, signal):
    p0, p1 = sigmoid(lin), sigmoid(lin + tau)
    df[TREAT] = T.astype(int)
    df[OUT] = rng.binomial(1, np.where(T == 1, p1, p0)).astype(int)
    df = add_ncs(df, rng, signal)
    return df, float((p1 - p0).mean())


def r_clean_rct(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, 0.5, n)
    df, ate = fin(df, rng, -0.2 + 0.7 * a, 0.6, T, a)
    return df, dict(regime="clean_rct", true_ate=ate, kind="specificity")

def r_confounded_observed(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.2 * a))
    df, ate = fin(df, rng, -0.2 + 0.9 * a, 0.5, T, a)
    return df, dict(regime="confounded_observed", true_ate=ate, kind="specificity")

def r_unobs_no_proxy(rng, n):
    df, a = base(rng, n); U = rng.normal(0, 1, n); T = rng.binomial(1, sigmoid(1.8 * U))
    df, ate = fin(df, rng, -0.1 + 1.4 * U, -0.3, T, U)   # NCs driven by hidden U
    # hide U: covariates x* are independent of U here (no proxy)
    return df, dict(regime="unobserved_no_proxy", true_ate=ate, kind="sensitivity")

def r_unobs_with_proxy(rng, n):
    df, a = base(rng, n); U = rng.normal(0, 1, n)
    df["x0"] = U + rng.normal(0, 0.8, n)                 # weak proxy leaks into covariates
    T = rng.binomial(1, sigmoid(1.6 * U))
    df, ate = fin(df, rng, -0.1 + 1.2 * U, -0.3, T, U)
    return df, dict(regime="unobserved_with_proxy", true_ate=ate, kind="sensitivity")

REGIMES = [r_clean_rct, r_confounded_observed, r_unobs_no_proxy, r_unobs_with_proxy,
           r_clean_rct, r_confounded_observed, r_unobs_no_proxy, r_unobs_with_proxy]


def genpredict():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    secret = int.from_bytes(os.urandom(16), "big")
    master = np.random.default_rng(secret)
    order = list(range(len(REGIMES))); master.shuffle(order)
    sizes = master.integers(9000, 24000, len(REGIMES))
    index, answers = [], []
    for file_no, (ri, n) in enumerate(zip(order, sizes), start=1):
        sub = np.random.default_rng(master.integers(0, 2**63))
        df, truth = REGIMES[ri](sub, int(n))
        df = df[COVARS + [TREAT, OUT] + NCS]
        fname = f"cset_{file_no:02d}.csv"; df.to_csv(OUTDIR / fname, index=False)
        index.append(dict(filename=fname, n_rows=int(n)))
        ts = "null" if abs(truth["true_ate"]) < 0.003 else ("positive" if truth["true_ate"] > 0 else "negative")
        answers.append(dict(filename=fname, true_sign=ts, **truth))
    INDEX.write_text(json.dumps({"datasets": index, "covars": COVARS, "treat": TREAT,
                                 "outcome": OUT, "ncs": NCS}, indent=2))
    payload = json.dumps({"generator": "claude-self-blind-consensus", "secret_seed": str(secret),
                          "datasets": answers}, indent=2)
    SEALED.write_text(payload); digest = hashlib.sha256(payload.encode()).hexdigest()
    SHA.write_text(f"{digest}  {SEALED.name}\n")

    # BLIND prediction: main sign + per-NC residual + single-weak vs consensus trip
    preds = []
    for d in index:
        df = pd.read_csv(OUTDIR / d["filename"])
        main = estimate(df, TREAT, OUT, COVARS).t_learner_ate
        nc_eff = {nc: float(estimate(df, TREAT, nc, COVARS).t_learner_ate) for nc in NCS}
        consensus_max = max(abs(v) for v in nc_eff.values())
        preds.append(dict(filename=d["filename"], main_ate=round(main, 4),
                          predicted_sign=("positive" if main > 0.005 else "negative" if main < -0.005 else "null"),
                          nc_effects={k: round(v, 4) for k, v in nc_eff.items()},
                          weak_trips=bool(abs(nc_eff["nc_weak"]) > FLOOR),
                          consensus_trips=bool(consensus_max > FLOOR),
                          consensus_max=round(consensus_max, 4)))
    PRED.write_text(json.dumps({"floor": FLOOR, "predictions": preds}, indent=2))
    print(f"genpredict: {len(preds)} datasets, sealed sha256={digest}")
    for p in preds:
        print(f"  {p['filename']}: main={p['main_ate']:+.4f} weak={'T' if p['weak_trips'] else '·'} "
              f"consensus={'T' if p['consensus_trips'] else '·'} (max={p['consensus_max']:.3f})")


def score():
    payload = SEALED.read_text(); digest = hashlib.sha256(payload.encode()).hexdigest()
    integ = "OK" if digest == SHA.read_text().split()[0] else "FAIL"
    ans = {d["filename"]: d for d in json.loads(payload)["datasets"]}
    preds = {p["filename"]: p for p in json.loads(PRED.read_text())["predictions"]}

    rows = []
    spec_total = spec_consensus_ok = 0
    weak_sens = consensus_sens = sens_total = 0
    for fn in sorted(ans):
        a, p = ans[fn], preds[fn]
        kind = a["kind"]
        if kind == "specificity":
            spec_total += 1
            spec_consensus_ok += int(not p["consensus_trips"])
        else:
            sens_total += 1
            weak_sens += int(p["weak_trips"])
            consensus_sens += int(p["consensus_trips"])
        rows.append((fn, a["regime"], kind, p["main_ate"], p["weak_trips"],
                     p["consensus_trips"], p["consensus_max"]))

    p1 = spec_consensus_ok == spec_total
    p2 = consensus_sens >= weak_sens and consensus_sens > 0
    p3 = consensus_sens >= weak_sens and p1
    verdict = ("LEAD (MECH-ONLY ceiling) — consensus recovers sensitivity, specificity preserved"
               if (p1 and p2 and p3) else
               "NULL — consensus false-alarms on specificity cases" if not p1 else
               "NULL — consensus did not improve sensitivity")
    md = [f"# Multi-NC consensus guard — Scorecard (iter4)", "",
          f"**Integrity:** sha256 `{digest[:16]}…` — {integ}", "",
          "> Self-blind synthetic ⇒ MECH-ONLY ceiling.", "",
          f"**P1 specificity (consensus does NOT trip where adjustment works):** "
          f"{spec_consensus_ok}/{spec_total} → {'PASS' if p1 else 'FAIL'}",
          f"**Sensitivity:** single-weak {weak_sens}/{sens_total} vs **consensus "
          f"{consensus_sens}/{sens_total}** → P2 {'PASS' if p2 else 'FAIL'}", "",
          "| File | Regime | Kind | main | weak trips | consensus trips | max|nc| |",
          "|---|---|---|---|---|---|---|"]
    for fn, reg, kind, m, w, c, mx in rows:
        md.append(f"| {fn} | {reg} | {kind} | {m:+.4f} | {'T' if w else '·'} | "
                  f"{'T' if c else '·'} | {mx:.3f} |")
    md += ["", "## Verdict", "", verdict,
           "", "Consensus over several negative controls trades a small added false-alarm risk "
           "(more controls = more chances to exceed the floor) for recovering the bias that a "
           "single WEAK control misses. Where it preserves specificity, it is the safer guard; "
           "the router should still prefer controls known to be strongly coupled."]
    CARD.write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nSUMMARY p1={p1} weak_sens={weak_sens}/{sens_total} consensus_sens={consensus_sens}/{sens_total} integ={integ}")


if __name__ == "__main__":
    {"genpredict": genpredict, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "genpredict"]()
