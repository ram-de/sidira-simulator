"""E1 Leg-A generator — self-blinded composition battery (PREREG_E1, sealed 2026-07-01).

Emits 24 cells (3 families x 8; 12 flip + 12 one-sign):
  F1 mix-flip (Simpson): mix shift between segments fights a within-segment move.
  F2 gross-vs-net: per-unit take moves against volume.
  F3 trade-down: a cheaper option draws from non-buyers (+) and premium buyers (-).

Public file  e1_cases.json   : per cell {id, family, flip, prose, tier1_tables}
Sealed file  e1_answers.json : per cell {id, true_sign, true_delta} + sha256 sidecar.
No predictor path may read e1_answers.json before all predictions are recorded.

The prose narrative carries NO decisive numbers (PM-style, deliberately leaning
the WRONG way on flip cells); every number needed for the sign lives in
tier1_tables, which follow the frozen tier-1 shape: segment sizes, per-segment
rates/takes, and pilot-observed shift shares (aggregates only — nothing
row-level). Truth = exact arithmetic on the same tables (the battery tests
extraction, not hidden information).
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 20260701
rng = random.Random(SEED)

cases: list[dict] = []
answers: list[dict] = []


def r2(x: float) -> float:
    return round(x, 6)


# --------------------------------------------------------------------------- F1
def gen_mix_flip(i: int, flip: bool) -> None:
    """Traffic moves from a high-rate segment to a low-rate segment while the
    destination's within-segment rate improves. Flip: the improvement narrative
    hides an aggregate decline (or, mirrored, a scary mix shift hides a gain)."""
    nA = rng.randint(40_000, 90_000)
    nB = rng.randint(40_000, 90_000)
    rA = rng.uniform(0.10, 0.16)          # high-converting surface
    rB = rng.uniform(0.03, 0.06)          # low-converting surface
    if flip:
        # big mix shift toward B, nice-sounding within-B lift -> aggregate falls
        p = rng.uniform(0.25, 0.40)       # share of A's traffic moved to B
        upliftB = rng.uniform(1.15, 1.35) # B's rate improves 15-35%
        upliftA = 1.0
    else:
        # small mix shift, strong within-segment lifts -> aggregate rises
        p = rng.uniform(0.03, 0.08)
        upliftB = rng.uniform(1.30, 1.50)
        upliftA = rng.uniform(1.02, 1.06)
    moved = nA * p
    base = nA * rA + nB * rB
    new = (nA - moved) * rA * upliftA + (nB + moved) * rB * upliftB
    delta = new - base
    prose = (
        "We are redesigning the app home to route more users into the new "
        "discovery feed. In the pilot the feed's own conversion rate improved "
        "meaningfully after the redesign, and qualitative feedback was strong. "
        "The classic browse surface is unchanged. Should we expect total "
        "conversions to go up or down?"
    )
    tables = {
        "schema": "tier1.segment_mediator_outcome.v1",
        "segments": [
            {"segment": "classic_browse", "users": nA, "baseline_conv_rate": r2(rA),
             "pilot_conv_rate": r2(rA * upliftA)},
            {"segment": "discovery_feed", "users": nB, "baseline_conv_rate": r2(rB),
             "pilot_conv_rate": r2(rB * upliftB)},
        ],
        "pilot_observed_shift": {
            "description": "share of classic_browse users routed to discovery_feed",
            "share_moved": r2(p),
        },
        "metric": "total_conversions",
    }
    cid = f"F1_{'flip' if flip else 'onesign'}_{i}"
    cases.append({"id": cid, "family": "mix_shift", "flip": flip,
                  "prose": prose, "tier1_tables": tables})
    answers.append({"id": cid, "true_sign": "+" if delta > 0 else "-",
                    "true_delta": r2(delta)})


# --------------------------------------------------------------------------- F2
def gen_gross_vs_net(i: int, flip: bool) -> None:
    """A per-unit take rises while volume falls (or the mirror). Flip: 'small
    volume dip' language hides that elasticity dominates the take gain."""
    units = rng.randint(100_000, 250_000)
    take = rng.uniform(1.8, 3.2)                     # revenue per unit
    if flip:
        take_up = rng.uniform(1.06, 1.12)            # take +6-12%
        vol_down = rng.uniform(0.82, 0.90)           # units -10-18% (dominates)
    else:
        take_up = rng.uniform(1.10, 1.18)
        vol_down = rng.uniform(0.97, 0.995)          # units barely move
    base = units * take
    new = units * vol_down * take * take_up
    delta = new - base
    prose = (
        "We want to raise the service fee on marketplace orders. A two-week "
        "pilot showed buyers largely accepted the new fee — repeat purchase "
        "sentiment was stable and support contacts did not spike — though "
        "order volume dipped somewhat. Should we expect net fee revenue to go "
        "up or down?"
    )
    tables = {
        "schema": "tier1.segment_mediator_outcome.v1",
        "segments": [
            {"segment": "all_orders", "baseline_units": units,
             "baseline_take_per_unit": r2(take),
             "pilot_units": int(units * vol_down),
             "pilot_take_per_unit": r2(take * take_up)},
        ],
        "pilot_observed_shift": {
            "description": "units and take per unit observed in the fee pilot",
            "unit_ratio": r2(vol_down), "take_ratio": r2(take_up),
        },
        "metric": "net_fee_revenue",
    }
    cid = f"F2_{'flip' if flip else 'onesign'}_{i}"
    cases.append({"id": cid, "family": "gross_vs_net", "flip": flip,
                  "prose": prose, "tier1_tables": tables})
    answers.append({"id": cid, "true_sign": "+" if delta > 0 else "-",
                    "true_delta": r2(delta)})


# --------------------------------------------------------------------------- F3
def gen_trade_down(i: int, flip: bool) -> None:
    """A cheaper plan draws alpha from non-buyers (+) and beta from premium (-).
    Flip: 'lots of new signups' narrative hides premium cannibalization."""
    n_free = rng.randint(200_000, 400_000)
    n_prem = rng.randint(20_000, 45_000)
    price_low = rng.uniform(4.0, 6.0)
    price_high = rng.uniform(11.0, 15.0)
    if flip:
        alpha = rng.uniform(0.004, 0.009)   # small share of free convert
        beta = rng.uniform(0.18, 0.30)      # big premium trade-down
    else:
        alpha = rng.uniform(0.02, 0.04)
        beta = rng.uniform(0.02, 0.06)
    gain = n_free * alpha * price_low
    loss = n_prem * beta * (price_high - price_low)
    delta = gain - loss
    prose = (
        "We are introducing a cheaper Lite subscription tier below Premium. "
        "In the pilot the Lite tier signed up a visible stream of previously "
        "free users, and some existing Premium subscribers switched down to "
        "Lite. Should we expect total subscription revenue to go up or down?"
    )
    tables = {
        "schema": "tier1.segment_mediator_outcome.v1",
        "segments": [
            {"segment": "free_users", "users": n_free, "price": 0.0},
            {"segment": "premium_subscribers", "users": n_prem,
             "price": r2(price_high)},
        ],
        "new_option": {"name": "lite_tier", "price": r2(price_low)},
        "pilot_observed_shift": {
            "description": "monthly adoption shares observed in the Lite pilot",
            "share_of_free_users_adopting_lite": r2(alpha),
            "share_of_premium_switching_to_lite": r2(beta),
        },
        "metric": "total_subscription_revenue",
    }
    cid = f"F3_{'flip' if flip else 'onesign'}_{i}"
    cases.append({"id": cid, "family": "trade_down_cannibalization", "flip": flip,
                  "prose": prose, "tier1_tables": tables})
    answers.append({"id": cid, "true_sign": "+" if delta > 0 else "-",
                    "true_delta": r2(delta)})


def main() -> None:
    for i in range(4):
        gen_mix_flip(i, flip=True)
        gen_gross_vs_net(i, flip=True)
        gen_trade_down(i, flip=True)
    for i in range(4):
        gen_mix_flip(i, flip=False)
        gen_gross_vs_net(i, flip=False)
        gen_trade_down(i, flip=False)

    # Sanity: flips must actually flip (truth opposite the narrative lean).
    # Narrative lean: F1 flip leans + (improvement story), truth should be -;
    # F2 flip leans + (fee accepted), truth -; F3 flip leans + (new signups), truth -.
    lean_violations = [a["id"] for a, c in zip(answers, cases)
                       if c["flip"] and a["true_sign"] == "+"]
    onesign_violations = [a["id"] for a, c in zip(answers, cases)
                          if not c["flip"] and a["true_sign"] == "-"]
    (HERE / "e1_cases.json").write_text(json.dumps(cases, indent=1))
    (HERE / "e1_answers.json").write_text(json.dumps(
        {"seed": SEED, "answers": answers,
         "generator_sanity": {"flip_lean_violations": lean_violations,
                              "onesign_violations": onesign_violations}}, indent=1))
    digest = hashlib.sha256((HERE / "e1_answers.json").read_bytes()).hexdigest()
    (HERE / "e1_answers.sha256").write_text(digest + "  e1_answers.json\n")
    print(f"cells={len(cases)} flips={sum(c['flip'] for c in cases)}")
    print(f"flip_lean_violations={lean_violations}")
    print(f"onesign_violations={onesign_violations}")
    print(f"answers sha256={digest}")


if __name__ == "__main__":
    main()
