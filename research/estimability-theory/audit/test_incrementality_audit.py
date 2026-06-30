"""Deterministic tests for the incrementality audit.

Asserts each encoded case lands in its expected verdict set AND that the six
tells fire / don't-fire exactly as expected, plus a synthetic genuinely-
incremental negative control that must read SHIP-SAFE.
"""

from __future__ import annotations

from cases import (
    CASE_A_GENUINE_WIN,
    CASE_B_MIXSHIFT_TRADEDOWN,
    CASE_C_PREMIUM_CANNIBALIZATION,
    CASE_D_CHANNEL_SUBSTITUTION,
)
from incrementality_audit import (
    ExperimentReadout,
    TELLS,
    audit,
)


def fired_set(r: ExperimentReadout) -> set[int]:
    return {i for i, tell in enumerate(TELLS, start=1) if tell(r)[0]}


# --------------------------------------------------------------------------- #
# Verdicts.
# --------------------------------------------------------------------------- #


def test_case_a_ship_safe() -> None:
    # negative control: a real, modest win — audit must NOT cry wolf.
    assert audit(CASE_A_GENUINE_WIN).verdict == "SHIP-SAFE"


def test_case_b_fragile_or_trap() -> None:
    assert audit(CASE_B_MIXSHIFT_TRADEDOWN).verdict in {"FRAGILE-WIN", "REDISTRIBUTION-TRAP"}


def test_case_c_trap_or_fragile() -> None:
    assert audit(CASE_C_PREMIUM_CANNIBALIZATION).verdict in {"REDISTRIBUTION-TRAP", "FRAGILE-WIN"}


def test_case_d_redistribution_trap() -> None:
    assert audit(CASE_D_CHANNEL_SUBSTITUTION).verdict == "REDISTRIBUTION-TRAP"


# --------------------------------------------------------------------------- #
# Exact tell firing per case.
# --------------------------------------------------------------------------- #


def test_case_a_no_tells() -> None:
    assert fired_set(CASE_A_GENUINE_WIN) == set()


def test_case_b_tells() -> None:
    # mix-shift(1), shrinking basket(2), flat spend/cx(3), net wash(4);
    # no cannibalization(5), no substitution sibling(6).
    assert fired_set(CASE_B_MIXSHIFT_TRADEDOWN) == {1, 2, 3, 4}


def test_case_c_tells() -> None:
    # flat spend/cx(3) + cannibalization(5); no mix/basket/net/substitution.
    assert fired_set(CASE_C_PREMIUM_CANNIBALIZATION) == {3, 5}


def test_case_d_tells() -> None:
    # net wash(4) + cannibalized higher-margin sibling(5) + substitution(6).
    assert fired_set(CASE_D_CHANNEL_SUBSTITUTION) == {4, 5, 6}


# --------------------------------------------------------------------------- #
# Synthetic negative control: genuinely incremental win -> SHIP-SAFE.
# --------------------------------------------------------------------------- #

GENUINE_INCREMENTAL = ExperimentReadout(
    name="synthetic-genuine-incremental",
    headline_metric_delta=0.05,
    headline_sig=True,
    treated_metric_delta=0.05,  # treated up
    sibling_metric_delta=0.001,  # sibling FLAT (not falling) -> no substitution
    sibling_name="sibling channel",
    basket_delta=0.50,  # basket UP -> not trading down
    spend_per_customer_delta=0.04,  # real money growth
    spend_per_customer_sig=True,
    net_business_metric_delta=0.04,  # net UP, not a wash
    # no mix_shift, no cannibalization, margin not eroding.
)


def test_synthetic_incremental_ship_safe() -> None:
    assert fired_set(GENUINE_INCREMENTAL) == set()
    assert audit(GENUINE_INCREMENTAL).verdict == "SHIP-SAFE"


# --------------------------------------------------------------------------- #
# Graceful degradation + determinism.
# --------------------------------------------------------------------------- #


def test_empty_readout_degrades_to_no_tells() -> None:
    bare = ExperimentReadout(name="bare")
    assert fired_set(bare) == set()
    assert audit(bare).verdict == "SHIP-SAFE"


def test_audit_is_deterministic() -> None:
    first = audit(CASE_B_MIXSHIFT_TRADEDOWN)
    second = audit(CASE_B_MIXSHIFT_TRADEDOWN)
    assert first.verdict == second.verdict
    assert first.fired_numbers == second.fired_numbers


def test_summary_is_one_line() -> None:
    line = audit(CASE_D_CHANNEL_SUBSTITUTION).summary()
    assert "\n" not in line
    assert "REDISTRIBUTION-TRAP" in line
