"""Synthetic, illustrative scenarios that exercise the incrementality audit's
six tells and three verdicts. These are ABSTRACT archetypes — round, made-up
numbers chosen only to demonstrate the audit logic. No partner / customer data
is encoded here.

Each archetype maps to a common real-world failure (or success) shape:
  A  genuine modest win          -> SHIP-SAFE (the negative control: no wolf-cry)
  B  mix-shift trade-down        -> REDISTRIBUTION-TRAP
  C  premium-state cannibalization-> FRAGILE-WIN
  D  cross-channel substitution  -> REDISTRIBUTION-TRAP
"""

from __future__ import annotations

from incrementality_audit import ExperimentReadout, audit

# --------------------------------------------------------------------------- #
# A — a genuine, modest win. Positive significant headline, and NOTHING else:
# no mix-shift, no shrinking basket, no substitution sibling, no cannibalization.
# The audit must NOT cry wolf on a real win.
# --------------------------------------------------------------------------- #
CASE_A_GENUINE_WIN = ExperimentReadout(
    name="A: genuine modest win",
    headline_metric_delta=0.012,
    headline_sig=True,
    # everything else absent -> degrades gracefully, no tell fires.
)

# --------------------------------------------------------------------------- #
# B — mix-shift trade-down. Positive headline, but gains come from share moving
# to cheaper options while baskets shrink, spend-per-customer is flat, and the
# net business metric is ~a wash. High-value users do worse than low-value.
# --------------------------------------------------------------------------- #
CASE_B_MIXSHIFT_TRADEDOWN = ExperimentReadout(
    name="B: mix-shift trade-down",
    headline_metric_delta=0.010,
    headline_sig=True,
    basket_delta=-0.30,             # shrinking baskets
    spend_per_customer_delta=0.0,
    spend_per_customer_sig=False,   # flat spend / customer
    net_business_metric_delta=-0.01,  # ~ wash
    mix_shift=[
        ("lower-price options", "gained"),
        ("premium options", "lost"),
    ],
    segment_heterogeneity={"high_value": -0.09, "low_value": 0.04},
)

# --------------------------------------------------------------------------- #
# C — premium-state cannibalization. Moving customers OFF a higher-value state
# onto a cheaper one: headline flat-to-down, no money growth, margin erodes,
# and it cannibalizes the premium state.
# --------------------------------------------------------------------------- #
CASE_C_PREMIUM_CANNIBALIZATION = ExperimentReadout(
    name="C: premium-state cannibalization",
    headline_metric_delta=-0.007,
    headline_sig=False,
    spend_per_customer_delta=-0.007,
    spend_per_customer_sig=False,
    cannibalizes_higher_value_state="higher-value subscription state",
    margin_delta=-0.07,
)

# --------------------------------------------------------------------------- #
# D — cross-channel substitution. The treated channel rises, but a sibling
# (cheaper-to-serve, higher-margin) channel falls by ~the same amount, so total
# volume is flat and margin erodes: paid to relabel volume that already existed.
# --------------------------------------------------------------------------- #
CASE_D_CHANNEL_SUBSTITUTION = ExperimentReadout(
    name="D: cross-channel substitution",
    headline_metric_delta=0.05,        # treated channel up
    headline_sig=True,
    treated_metric_delta=0.05,
    sibling_metric_delta=-0.05,        # sibling channel down ~ same
    sibling_name="sibling channel",
    net_business_metric_delta=0.002,   # total volume ~ flat
    cannibalizes_higher_value_state="higher-margin sibling channel",
    margin_delta=-0.03,
)

CASES = [
    CASE_A_GENUINE_WIN,
    CASE_B_MIXSHIFT_TRADEDOWN,
    CASE_C_PREMIUM_CANNIBALIZATION,
    CASE_D_CHANNEL_SUBSTITUTION,
]


def print_verdict_table() -> None:
    """Print a (case | fired tells | verdict) table for the scenarios."""
    rows = [(r.name, audit(r)) for r in CASES]
    name_w = max(len(n) for n, _ in rows)
    tells_w = max(len("fired tells"), 11)
    print(f"{'case':<{name_w}}  {'fired tells':<{tells_w}}  verdict")
    print(f"{'-' * name_w}  {'-' * tells_w}  {'-' * 19}")
    for name, res in rows:
        nums = ",".join(str(n) for n in res.fired_numbers) or "-"
        print(f"{name:<{name_w}}  {nums:<{tells_w}}  {res.verdict}")


if __name__ == "__main__":  # pragma: no cover
    print_verdict_table()
