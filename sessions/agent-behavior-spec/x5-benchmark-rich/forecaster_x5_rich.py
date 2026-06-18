"""X5 RetailHero RICH-covariate follow-up — Step 4+5: blinded expert-forecaster
ranking over BEHAVIORAL (RFM) segments.

Mirrors x5-benchmark/forecaster_x5.py and hillstrom-benchmark/forecaster_powered.py:
expert-forecaster system prompt, per-segment numeric forecast, 3-attempt JSON
parse, Spearman rho + Kendall tau + label-permutation p. BLIND — the real
per-segment uplift is NEVER shown. Each audience description is built from the
segment's PRE-TREATMENT behavioral features (recency / frequency / monetary /
basket / breadth / redeem) ONLY.

    set -a; . backend/.env; set +a
    PYTHONPATH=backend <venv>/bin/python forecaster_x5_rich.py

Reads x5_rich_ground_truth.json; writes x5_rich_audience_descriptions.json,
x5_rich_predictions.json, forecaster_x5_rich_result.json.
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

REC_LABEL = {  # low recency_days = shopped most recently
    "low": "shopped very recently (their last purchase was just days before the campaign)",
    "mid": "shopped a few weeks before the campaign",
    "high": "had not shopped in a relatively long time before the campaign",
}
FREQ_LABEL = {
    "low": "are light, infrequent shoppers (few transactions in the prior months)",
    "mid": "are moderately frequent shoppers",
    "high": "are heavy, very frequent shoppers (many transactions in the prior months)",
}
MON_LABEL = {
    "low": "with low total prior spend",
    "mid": "with moderate total prior spend",
    "high": "with high total prior spend",
}


def describe(seg: dict) -> str:
    """Plain-language audience description from pre-treatment behavior ONLY."""
    return (
        f"Loyalty-program grocery customers who {REC_LABEL[seg['recency_tier']]}, "
        f"{FREQ_LABEL[seg['frequency_tier']]}, {MON_LABEL[seg['monetary_tier']]}. "
        f"On average this group made about {seg['mean_frequency_txns']:.0f} transactions "
        f"totalling roughly {seg['mean_monetary_total']:.0f} (local currency) before the "
        f"campaign, with a typical basket of about {seg['mean_basket_lines']:.0f} items, "
        f"buying across roughly {seg['mean_category_breadth']:.0f} distinct products, and "
        f"redeemed loyalty points in about {seg['mean_redeem_share']*100:.0f}% of their visits."
    )


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
            f"Audience: {desc}\n"
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
    gt = json.loads((HERE / "x5_rich_ground_truth.json").read_text())
    segments = gt["segments"]
    if not model_is_available(MODEL_ID):
        print(f"MODEL {MODEL_ID} not available — load backend/.env. ABORT.")
        return 2

    descriptions = [{"segment": s["segment"], "description": describe(s)} for s in segments]
    (HERE / "x5_rich_audience_descriptions.json").write_text(json.dumps(descriptions, indent=2))

    client = get_chat_client(MODEL_ID)
    preds, reals, used_segs, dropped = [], [], [], []
    pred_records = []
    for i, s in enumerate(segments):
        desc = describe(s)
        f = forecast(client, desc, seed=4000 + i)
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
    (HERE / "x5_rich_predictions.json").write_text(json.dumps(pred_records, indent=2))

    rho = spearman_rho(preds, reals)
    tau = kendalltau(preds, reals).correlation
    p = perm_p(preds, reals, rho)
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
        "x5_thin_reference_rho": 0.163,
        "predictions": pred_records,
    }
    (HERE / "forecaster_x5_rich_result.json").write_text(
        json.dumps(result, indent=2, default=float))

    print(f"\n=== X5 RICH heterogeneity blinded forecaster (Sonnet, n={len(preds)}) ===")
    print(f"  Spearman rho = {rho:+.3f}   (perm p = {p:.4f}, 5000 shuffles)")
    print(f"  Kendall tau_b = {tau:+.3f}   direction_acc = {dir_hits:.3f}")
    print(f"  pre-registered bar (rho>0.30 AND p<0.05): {'PASS' if bar_pass else 'FAIL'}")
    print(f"  references: Hillstrom rho=+0.42 | X5-thin rho=+0.163")
    print(f"\nwrote forecaster_x5_rich_result.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
