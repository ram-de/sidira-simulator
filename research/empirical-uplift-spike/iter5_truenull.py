"""
iter5_truenull.py — true-null guard via effect-vs-residual ratio, self-blind (sealed a77c1996).

  phase 1:  python iter5_truenull.py genpredict   # data + blind predictions (commit these)
  phase 2:  python iter5_truenull.py score        # unseal + score (after commit)

Rule under test: trust the main sign iff |main| > RATIO * |nc_residual| (else abstain). The
negative control shares the OBSERVED confounder `a` (a NONLINEAR fn of covariates); the estimator
adjusts with RAW linear covariates, so leakage produces the true-null false positive this targets.
"""
from __future__ import annotations
import hashlib, json, os, sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from causal_estimator import estimate  # noqa: E402

OUTDIR = HERE / ".data" / "synthetic_truenull"
INDEX = HERE / "synthetic_truenull_index.json"
SHA = HERE / "SYNTHETIC_TRUENULL_ANSWERS.sha256"
SEALED = Path.home() / "truenull_challenge_SEALED.json"
PRED = HERE / "synthetic_truenull_predictions.json"
CARD = HERE / "synthetic_truenull_scorecard.md"
RATIO, FLOOR, NULL_BAND = 1.5, 0.05, 0.005
COVARS = [f"x{i}" for i in range(6)]
TREAT, OUT = "got_feature", "outcome"
NCS = ["nc_a", "nc_b"]


def sigmoid(x): return 1.0 / (1.0 + np.exp(-np.clip(x, -30, 30)))


def base(rng, n):
    df = pd.DataFrame({f"x{i}": rng.normal(0, 1, n) for i in range(6)})
    x = df.to_numpy()
    # MOSTLY-LINEAR observed confounder + a small nonlinear leak: linear adjustment removes most
    # of it, leaving a SMALL sub-floor residual (the regime where the true-null gap actually lives).
    a = 0.9 * x[:, 0] + 0.6 * x[:, 1] + 0.4 * x[:, 2] + 0.3 * (x[:, 3] ** 2 - 1)
    return df, (a - a.mean()) / a.std()


def ncs(df, rng, signal, k=1.0):
    s = (signal - signal.mean()) / signal.std()
    df["nc_a"] = rng.binomial(1, sigmoid(-0.1 + 1.2 * k * s)).astype(int)
    df["nc_b"] = rng.binomial(1, sigmoid(0.0 + 0.9 * k * s)).astype(int)
    return df


def fin(df, rng, lin, tau, T, signal):
    p0, p1 = sigmoid(lin), sigmoid(lin + tau)
    df[TREAT] = T.astype(int)
    df[OUT] = rng.binomial(1, np.where(T == 1, p1, p0)).astype(int)
    df = ncs(df, rng, signal)
    return df, float((p1 - p0).mean())


def r_null(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.3 * a))
    df, ate = fin(df, rng, -0.1 + 1.0 * a, 0.0, T, a)          # tau = 0
    return df, dict(regime="true_null_confounded", true_ate=ate, kind="null")

def r_clear_clean(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, 0.5, n)
    df, ate = fin(df, rng, -0.2 + 0.7 * a, 0.6, T, a)
    return df, dict(regime="clean_rct_large", true_ate=ate, kind="clear_real")

def r_clear_conf(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.2 * a))
    df, ate = fin(df, rng, -0.2 + 0.9 * a, 0.5, T, a)
    return df, dict(regime="confounded_large", true_ate=ate, kind="clear_real")

def r_borderline(rng, n):
    df, a = base(rng, n); T = rng.binomial(1, sigmoid(1.1 * a))
    df, ate = fin(df, rng, -0.1 + 0.8 * a, 0.04, T, a)         # small real effect ~ residual scale
    return df, dict(regime="borderline_small_real", true_ate=ate, kind="borderline")

REGIMES = [r_null, r_null, r_clear_clean, r_clear_conf, r_clear_conf,
           r_borderline, r_borderline, r_borderline]


def label(main, nc):
    if abs(nc) > FLOOR:                       # hidden confounding (existing guard)
        return "abstain"
    if abs(main) <= RATIO * abs(nc):          # indistinguishable from observed-confounding bias
        return "abstain"
    if abs(main) <= NULL_BAND:
        return "null"
    return "treatment" if main > 0 else "control"


def genpredict():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    secret = int.from_bytes(os.urandom(16), "big")
    master = np.random.default_rng(secret)
    order = list(range(len(REGIMES))); master.shuffle(order)
    sizes = master.integers(9000, 22000, len(REGIMES))
    index, answers = [], []
    for file_no, (ri, n) in enumerate(zip(order, sizes), start=1):
        sub = np.random.default_rng(master.integers(0, 2**63))
        df, truth = REGIMES[ri](sub, int(n))
        df = df[COVARS + [TREAT, OUT] + NCS]
        fname = f"tn_{file_no:02d}.csv"; df.to_csv(OUTDIR / fname, index=False)
        index.append(dict(filename=fname, n_rows=int(n)))
        ts = "null" if abs(truth["true_ate"]) < 0.003 else ("positive" if truth["true_ate"] > 0 else "negative")
        answers.append(dict(filename=fname, true_sign=ts, **truth))
    INDEX.write_text(json.dumps({"datasets": index}, indent=2))
    payload = json.dumps({"generator": "claude-self-blind-truenull", "secret_seed": str(secret),
                          "datasets": answers}, indent=2)
    SEALED.write_text(payload); digest = hashlib.sha256(payload.encode()).hexdigest()
    SHA.write_text(f"{digest}  {SEALED.name}\n")

    preds = []
    for d in index:
        df = pd.read_csv(OUTDIR / d["filename"])
        main = estimate(df, TREAT, OUT, COVARS).t_learner_ate
        nc_eff = {nc: float(estimate(df, TREAT, nc, COVARS).t_learner_ate) for nc in NCS}
        nc_dec = max(nc_eff.values(), key=abs)
        # baseline = old guard (sign by null band, no ratio rule)
        baseline = ("treatment" if main > NULL_BAND else "control" if main < -NULL_BAND else "null")
        preds.append(dict(filename=d["filename"], main_ate=round(main, 4),
                          nc_decisive=round(nc_dec, 4), nc_effects={k: round(v, 4) for k, v in nc_eff.items()},
                          baseline_label=baseline, guarded_label=label(main, nc_dec)))
    PRED.write_text(json.dumps({"ratio": RATIO, "floor": FLOOR, "null_band": NULL_BAND,
                                "predictions": preds}, indent=2))
    print(f"genpredict: {len(preds)} datasets, sealed sha256={digest}")
    for p in preds:
        print(f"  {p['filename']}: main={p['main_ate']:+.4f} nc={p['nc_decisive']:+.4f} "
              f"baseline={p['baseline_label']:9} guarded={p['guarded_label']}")


def score():
    payload = SEALED.read_text(); digest = hashlib.sha256(payload.encode()).hexdigest()
    integ = "OK" if digest == SHA.read_text().split()[0] else "FAIL"
    ans = {d["filename"]: d for d in json.loads(payload)["datasets"]}
    preds = {p["filename"]: p for p in json.loads(PRED.read_text())["predictions"]}
    W = {"positive": "treatment", "negative": "control", "null": "null"}

    rows = []
    null_total = null_caught = null_baseline_wrong = 0
    clear_total = clear_ok = 0
    border_total = border_defer = border_trust_right = border_trust_wrong = 0
    for fn in sorted(ans):
        a, p = ans[fn], preds[fn]
        kind, want = a["kind"], W[a["true_sign"]]
        g, b = p["guarded_label"], p["baseline_label"]
        if kind == "null":
            null_total += 1
            null_caught += int(g == "abstain")
            null_baseline_wrong += int(b != "null")
        elif kind == "clear_real":
            clear_total += 1
            clear_ok += int(g == want)
        else:
            border_total += 1
            border_defer += int(g == "abstain")
            border_trust_right += int(g == want)
            border_trust_wrong += int(g not in ("abstain", want))
        rows.append((fn, a["regime"], kind, p["main_ate"], p["nc_decisive"], b, g, want))

    p1 = null_caught == null_total
    p2 = clear_ok == clear_total
    verdict = ("LEAD (MECH-ONLY ceiling) — ratio rule closes the true-null gap for decidable cases; "
               "borderline effects honestly deferred to LLM"
               if (p1 and p2) else
               "NULL — true-null still slips through" if not p1 else
               "NULL — ratio rule over-abstains on clear real effects")
    md = [f"# True-null guard (effect-vs-residual ratio {RATIO}) — Scorecard (iter5)", "",
          f"**Integrity:** sha256 `{digest[:16]}…` — {integ}", "",
          "> Self-blind synthetic ⇒ MECH-ONLY ceiling.", "",
          f"**P1 true-null caught (abstain):** {null_caught}/{null_total} "
          f"(old guard called {null_baseline_wrong}/{null_total} of them a real effect) → {'PASS' if p1 else 'FAIL'}",
          f"**P2 clear real effects still trusted (no over-abstention):** {clear_ok}/{clear_total} → {'PASS' if p2 else 'FAIL'}",
          f"**P3 borderline small-real (honest defer):** {border_defer}/{border_total} deferred, "
          f"{border_trust_right} trusted-correct, {border_trust_wrong} trusted-wrong (cost = deferred-to-LLM)", "",
          "| File | Regime | Kind | main | nc | old guard | ratio guard | true |",
          "|---|---|---|---|---|---|---|---|"]
    for fn, reg, kind, m, nc, b, g, want in rows:
        md.append(f"| {fn} | {reg} | {kind} | {m:+.4f} | {nc:+.4f} | {b} | **{g}** | {want} |")
    md += ["", "## Verdict", "", verdict,
           "", "The negative control measures the confounding BIAS; trusting the main sign only when "
           "it clearly exceeds that bias converts confident-wrong true-null calls into honest "
           "abstentions. The unavoidable cost: a real effect SMALLER than the bias is genuinely "
           "unidentifiable and gets routed to the LLM — which is the correct, honest fallback."]
    CARD.write_text("\n".join(md))
    print("\n".join(md))
    print(f"\nSUMMARY p1={p1} p2={p2} null={null_caught}/{null_total} clear={clear_ok}/{clear_total} "
          f"border_defer={border_defer}/{border_total} integ={integ}")


if __name__ == "__main__":
    {"genpredict": genpredict, "score": score}[sys.argv[1] if len(sys.argv) > 1 else "genpredict"]()
