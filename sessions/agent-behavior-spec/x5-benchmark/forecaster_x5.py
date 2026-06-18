"""X5 RetailHero generalization test — Step 4+5: blinded expert-forecaster ranking.

Mirrors sessions/agent-behavior-spec/hillstrom-benchmark/forecaster_powered.py:
expert-forecaster system prompt, per-segment numeric forecast, 3-attempt JSON
parse, Spearman rho + Kendall tau + label-permutation p. BLIND — the real
per-segment uplift is NEVER shown to the model; each audience description is
built from pre-treatment covariates (gender / age / tenure) ONLY.

    set -a; . backend/.env; set +a
    PYTHONPATH=backend <venv>/bin/python forecaster_x5.py

Reads x5_ground_truth.json (the pre-registered, SHA-pinned segments) and writes
x5_audience_descriptions.json, x5_predictions.json, forecaster_x5_result.json.
"""
from __future__ import annotations

import json
import random
import re
from pathlib import Path

from scipy.stats import kendalltau

from sidira_simulator.adapters.llm import get_chat_client, model_is_available
from sidira_simulator.services.statistics import spearman_rho

HERE = Path(__file__).resolve().parent
MODEL_ID = "claude-sonnet-4-6"
_OBJ = re.compile(r"\{[^{}]*\}")

AGE_LABEL = {"under35": "under 35 years old", "35to54": "aged 35 to 54",
             "55plus": "aged 55 or older"}
TEN_LABEL = {
    "longtenure": "joined the supermarket loyalty program back in 2017 (long-standing members)",
    "midtenure": "joined the loyalty program in 2018",
    "newtenure": "joined the loyalty program in 2019 (relatively new members)",
}
GENDER_LABEL = {"F": "Women", "M": "Men"}


def describe(seg: dict) -> str:
    """Plain-language audience description from covariates ONLY (no uplift)."""
    return (f"{GENDER_LABEL[seg['gender']]} {AGE_LABEL[seg['age_bucket']]} who "
            f"{TEN_LABEL[seg['tenure_bucket']]}")


def _json(raw: str):
    for c in reversed(_OBJ.findall(raw)):
        try:
            o = json.loads(c)
            if isinstance(o, dict):
                return o
        except Exception:
            continue
    return None


def forecast(client, desc: str, seed: int):
    msgs = [
        {"role": "system", "content":
            "You are an expert in retail loyalty-marketing causal effects. You predict how a "
            "promotional SMS from a large grocery retailer changes a customer's likelihood of "
            "making a purchase, versus sending no SMS, grounded in how real randomized loyalty "
            "campaigns actually move behavior across different customer segments."},
        {"role": "user", "content":
            f"Audience: {desc}.\n"
            "Campaign: the retailer sends this audience a promotional SMS offer; a randomized "
            "holdout receives NO SMS. Both arms are otherwise identical loyalty-program members.\n"
            "Predict how strongly THIS audience responds to the SMS — the increase in purchase "
            "rate versus the no-SMS holdout, in percentage points (uplift can be near zero or "
            'slightly negative for unresponsive segments). Respond ONLY with JSON: '
            '{"uplift_pp": <float>}'}]
    for attempt in range(3):
        try:
            raw = client.chat(msgs, max_tokens=200,
                              temperature=0.0 if attempt == 0 else 0.3, seed=seed)
        except Exception:
            continue
        o = _json(raw)
        if o and "uplift_pp" in o:
            try:
                return float(o["uplift_pp"])
            except (TypeError, ValueError):
                continue
    return None


def perm_p(pred, real, obs_rho, trials=5000, seed=42):
    rng = random.Random(seed)
    r = list(real)
    hits = 0
    for _ in range(trials):
        rng.shuffle(r)
        if abs(spearman_rho(pred, r)) >= abs(obs_rho):
            hits += 1
    return (hits + 1) / (trials + 1)


def main() -> int:
    gt = json.loads((HERE / "x5_ground_truth.json").read_text())
    segments = gt["segments"]
    if not model_is_available(MODEL_ID):
        print(f"MODEL {MODEL_ID} not available — load backend/.env. ABORT.")
        return 2

    # Build + persist blinded audience descriptions.
    descriptions = [{"segment": s["segment"], "description": describe(s)} for s in segments]
    (HERE / "x5_audience_descriptions.json").write_text(json.dumps(descriptions, indent=2))

    client = get_chat_client(MODEL_ID)
    preds, reals, used_segs, dropped = [], [], [], []
    pred_records = []
    for i, s in enumerate(segments):
        desc = describe(s)
        f = forecast(client, desc, seed=3000 + i)
        if f is None:
            dropped.append(s["segment"])
            print(f"  DROP {s['segment']}")
            continue
        preds.append(f)
        reals.append(s["uplift"])
        used_segs.append(s["segment"])
        pred_records.append({"segment": s["segment"], "description": desc,
                             "predicted_uplift_pp": f, "real_uplift": s["uplift"]})
        print(f"  {s['segment']:24s} pred_pp={f:+7.3f}  real={s['uplift']:+.4f}")
    (HERE / "x5_predictions.json").write_text(json.dumps(pred_records, indent=2))

    rho = spearman_rho(preds, reals)
    tau = kendalltau(preds, reals).correlation
    p = perm_p(preds, reals, rho)
    # Sign/direction accuracy: predicted points the same direction as real uplift.
    dir_hits = sum(1 for pr, rl in zip(preds, reals)
                   if (pr > 0) == (rl > 0)) / len(preds)
    bar_pass = (rho > 0.30) and (p < 0.05)

    result = {
        "model": MODEL_ID,
        "n_segments_scored": len(preds),
        "n_dropped": len(dropped),
        "dropped_segments": dropped,
        "ground_truth_sha256": gt["ground_truth_sha256"],
        "spearman_rho": rho,
        "kendall_tau_b": tau,
        "permutation_p": p,
        "permutation_trials": 5000,
        "direction_accuracy_vs_zero": dir_hits,
        "pre_registered_bar": "rho > 0.30 AND perm_p < 0.05",
        "bar_passed": bar_pass,
        "hillstrom_reference_rho": 0.42,
        "predictions": pred_records,
    }
    (HERE / "forecaster_x5_result.json").write_text(json.dumps(result, indent=2, default=float))

    print(f"\n=== X5 heterogeneity blinded forecaster (Sonnet, n={len(preds)}) ===")
    print(f"  Spearman rho = {rho:+.3f}   (perm p = {p:.4f}, 5000 shuffles)")
    print(f"  Kendall tau_b = {tau:+.3f}   direction_acc = {dir_hits:.3f}")
    print(f"  pre-registered bar (rho>0.30 AND p<0.05): {'PASS' if bar_pass else 'FAIL'}")
    print(f"  Hillstrom reference rho = +0.42")
    print(f"\nwrote forecaster_x5_result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
