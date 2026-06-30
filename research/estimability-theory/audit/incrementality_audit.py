"""Incrementality / test-win generalization audit (deterministic, NO LLM).

This module automates ``research/estimability-theory/blind-tests/
TEST_WIN_GENERALIZATION_AUDIT.md``. It reads a *winning* experiment's OWN
internals and flags whether a positive headline is **net-new value** or
**redistributed / substituted activity that moved from somewhere else**.

It is NOT a blind forward prediction and NOT a persona simulation. It is the
audit the product runs on a test win *before* a broad rollout: a deterministic
data computation over numbers the experiment already produced. That makes it
the durable, **model-confound-free** version of the "mechanism read" — the
thing that beat the persona engine 3-for-3 on the counter-intuitive blind
tests (grocery trade-down, membership margin, storefront cannibalization)
while the engine went 0-for-3.

Core question, from the template: *incremental relative to what the customer
would otherwise have done?* A positive headline metric is necessary but never
sufficient. The single most important pull is the **sibling metric** — the
cheaper-to-serve state the same customer already occupied (pickup, organic,
full-price, membership) that may be falling while the treated metric rises.

The six tells (each a red flag even when the headline is positive):

1. mix-shift win        — share moved between merchants/SKUs/stores, not net-new
2. shrinking baskets    — basket / AOV down → customers trade *down*, not buy more
3. flat spend-per-cust  — lift is order/active-count only; no money growth
4. net business ≈ wash  — the winner's gain ≈ some loser's loss (someone paid for it)
5. cannibalization      — erodes a higher-value / higher-margin state (membership,
                          full-price, the cheaper-to-serve channel)
6. counterfactual subst — treated up while a sibling falls ≈ the same magnitude →
                          net-new ≈ 0; you paid to relabel volume you already had
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Optional

# --------------------------------------------------------------------------- #
# Thresholds (module constants — all documented; tune here, nowhere else).
# --------------------------------------------------------------------------- #

# A net / per-customer metric whose magnitude is within +/- this band of zero is
# treated as "flat" or "a wash" (2% — below this we do not credit a money win).
WASH_BAND = 0.02

# Net-components wash: gain ~ |loss| when |sum(components)| is within this
# fraction of the largest single component (e.g. +600k vs -750k -> ~wash).
NET_WASH_RATIO = 0.25

# Counterfactual substitution (tell 6): the sibling loss offsets the treated gain
# when the residual net (treated + sibling) is within this fraction of the
# treated gain (e.g. delivery +5% / pickup -5% -> residual 0 -> substitution).
SUBSTITUTION_NET_BAND = 0.5

# Tell 2 fires when basket / AOV is below this (strictly shrinking baskets).
BASKET_DOWN_THRESHOLD = 0.0

# Tell 5 also fires on margin erosion this deep even without a named cannibalized
# state — a >=5% contribution-margin drop signals a higher-value state eroding.
MARGIN_EROSION_THRESHOLD = -0.05

VERDICTS = ("SHIP-SAFE", "FRAGILE-WIN", "REDISTRIBUTION-TRAP")


# --------------------------------------------------------------------------- #
# Experiment internals.
# --------------------------------------------------------------------------- #


@dataclass
class ExperimentReadout:
    """A winning experiment's internals. All metric fields are Optional so a
    partial readout degrades gracefully — a tell never fires on missing data."""

    name: str

    # Headline (the surface "win").
    headline_metric_delta: Optional[float] = None  # e.g. +0.010 = orders +1.0%
    headline_sig: Optional[bool] = None

    # The substitution pair (tell 6): the treated state vs the cheaper sibling
    # state the same customer already occupied (e.g. delivery up / pickup down).
    treated_metric_delta: Optional[float] = None
    sibling_metric_delta: Optional[float] = None
    sibling_name: Optional[str] = None

    # Per-order / per-customer economics.
    basket_delta: Optional[float] = None  # subtotal change (currency or frac)
    aov_delta: Optional[float] = None
    spend_per_customer_delta: Optional[float] = None
    spend_per_customer_sig: Optional[bool] = None

    # Net (not gross) business metric and its decomposition.
    net_business_metric_delta: Optional[float] = None  # net GOV / revenue
    net_components: Optional[list[tuple[str, float]]] = None  # (label, value)

    # Mix / cannibalization.
    mix_shift: Optional[list[tuple[str, str]]] = None  # (segment, gained|lost)
    cannibalizes_higher_value_state: Optional[str] = None  # e.g. "membership"
    margin_delta: Optional[float] = None

    # Heterogeneity (captured for context; not itself a tell).
    segment_heterogeneity: Optional[dict[str, float]] = None


@dataclass
class AuditResult:
    name: str
    fired_tells: list[tuple[int, str]] = field(default_factory=list)
    verdict: str = "SHIP-SAFE"
    rationale: str = ""

    @property
    def fired_numbers(self) -> list[int]:
        return [n for n, _ in self.fired_tells]

    def summary(self) -> str:
        nums = ",".join(str(n) for n in self.fired_numbers) or "none"
        return f"{self.name}: {self.verdict} (tells: {nums}) — {self.rationale}"


# --------------------------------------------------------------------------- #
# The six tells. Each: (fired: bool, evidence: str).
# --------------------------------------------------------------------------- #


def tell_1(r: ExperimentReadout) -> tuple[bool, str]:
    """Mix-shift win: gains came from share moving between merchants / SKUs /
    destinations / segments rather than net-new demand."""
    if not r.mix_shift:
        return False, "no mix-shift data"
    moves = "; ".join(f"{seg} {dirn}" for seg, dirn in r.mix_shift)
    return True, f"share moved, not net-new demand: {moves}"


def tell_2(r: ExperimentReadout) -> tuple[bool, str]:
    """Shrinking baskets: subtotal / AOV down -> customers trade DOWN."""
    basket = r.basket_delta if r.basket_delta is not None else r.aov_delta
    if basket is None:
        return False, "no basket/AOV data"
    if basket < BASKET_DOWN_THRESHOLD:
        return True, f"basket/AOV down ({basket:+.4g}) — trading down, not buying more"
    return False, f"basket/AOV not shrinking ({basket:+.4g})"


def tell_3(r: ExperimentReadout) -> tuple[bool, str]:
    """Flat spend-per-customer: any lift is order/active-count only, no money
    growth. Strongest when not significant (and counts are up). We require only
    flat-or-down, not-significant spend: the headline is not matched by money."""
    spc = r.spend_per_customer_delta
    if spc is None:
        return False, "no spend-per-customer data"
    significant = r.spend_per_customer_sig is True
    if abs(spc) <= WASH_BAND and not significant:
        return True, (
            f"spend-per-customer flat/down ({spc:+.4g}), not significant — "
            "lift (if any) is not in money"
        )
    return False, f"spend-per-customer moved ({spc:+.4g}, sig={r.spend_per_customer_sig})"


def tell_4(r: ExperimentReadout) -> tuple[bool, str]:
    """Net business metric ~ a wash: the winner's gain ~ some loser's loss."""
    if r.net_business_metric_delta is not None and abs(
        r.net_business_metric_delta
    ) <= WASH_BAND:
        return True, (
            f"net business metric ~0 ({r.net_business_metric_delta:+.4g}) — a wash"
        )
    if r.net_components:
        total = sum(v for _, v in r.net_components)
        peak = max((abs(v) for _, v in r.net_components), default=0.0)
        if peak > 0 and abs(total) <= NET_WASH_RATIO * peak:
            parts = ", ".join(f"{lbl} {v:+.6g}" for lbl, v in r.net_components)
            return True, f"net components ~cancel (net {total:+.6g}): {parts}"
    return False, "net business metric not a wash"


def tell_5(r: ExperimentReadout) -> tuple[bool, str]:
    """Cannibalizes a higher-value / higher-margin state (membership,
    full-price, loyalty, or the cheaper-to-serve channel)."""
    if r.cannibalizes_higher_value_state:
        extra = ""
        if r.margin_delta is not None and r.margin_delta < 0:
            extra = f" (margin {r.margin_delta:+.4g})"
        return True, (
            f"erodes higher-value state: {r.cannibalizes_higher_value_state}{extra}"
        )
    if r.margin_delta is not None and r.margin_delta <= MARGIN_EROSION_THRESHOLD:
        return True, (
            f"margin erosion {r.margin_delta:+.4g} — a higher-margin state is paying"
        )
    return False, "no cannibalization of a higher-value state"


def tell_6(r: ExperimentReadout) -> tuple[bool, str]:
    """Counterfactual substitution: the treated metric rises while a sibling
    metric falls ~ the same magnitude -> net-new ~ 0. You paid to relabel volume
    you already had (pickup -> paid delivery, organic -> paid, full-price ->
    promo). The storefront tell."""
    t, s = r.treated_metric_delta, r.sibling_metric_delta
    if t is None or s is None:
        return False, "no treated/sibling substitution pair"
    if t > 0 and s < 0:
        net = t + s
        if abs(net) <= SUBSTITUTION_NET_BAND * abs(t):
            sib = r.sibling_name or "sibling"
            return True, (
                f"treated {t:+.4g} but {sib} {s:+.4g} (net {net:+.4g}) — "
                "substitution, not growth"
            )
    return False, "treated/sibling do not show offsetting substitution"


TELLS: list[Callable[[ExperimentReadout], tuple[bool, str]]] = [
    tell_1,
    tell_2,
    tell_3,
    tell_4,
    tell_5,
    tell_6,
]


# --------------------------------------------------------------------------- #
# Verdict.
# --------------------------------------------------------------------------- #


def _positive_headline(r: ExperimentReadout) -> bool:
    return r.headline_metric_delta is not None and r.headline_metric_delta > 0


def audit(r: ExperimentReadout) -> AuditResult:
    """Run all six tells and apply the verdict rubric from the template."""
    fired: list[tuple[int, str]] = []
    for i, tell in enumerate(TELLS, start=1):
        ok, evidence = tell(r)
        if ok:
            fired.append((i, evidence))
    nums = {n for n, _ in fired}

    # REDISTRIBUTION-TRAP: net-wash AND (mix-shift OR substitution) AND
    # (cannibalization OR shrinking baskets) — the gross-vs-net signature.
    is_trap = (4 in nums) and (nums & {1, 6}) and (nums & {2, 5})

    if is_trap:
        verdict = "REDISTRIBUTION-TRAP"
        rationale = (
            "net-wash with redistribution/substitution and "
            "cannibalization/shrinkage — gross activity moved, not net-new value; "
            "not a rollout candidate"
        )
    elif len(fired) >= 2:
        verdict = "FRAGILE-WIN"
        rationale = (
            f"{len(fired)} tells fire — the headline likely reflects redistributed "
            "or sign-fragile activity; broad-test on the real endpoint before rollout"
        )
    elif _positive_headline(r) and not fired:
        verdict = "SHIP-SAFE"
        rationale = "positive headline, zero tells — reads as net-new value"
    else:
        verdict = "SHIP-SAFE"
        rationale = (
            "no redistribution signature and fewer than two tells — "
            "no incrementality red flag"
        )

    return AuditResult(name=r.name, fired_tells=fired, verdict=verdict, rationale=rationale)


if __name__ == "__main__":  # pragma: no cover
    from cases import print_verdict_table

    print_verdict_table()
