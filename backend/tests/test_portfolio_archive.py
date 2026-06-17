"""Tests for the product-change portfolio archive loader.

Mirrors `test_cookiecats_archive`. Pins:
- parsing a well-formed payload into typed scored cases + held-out probe,
- the scored set and the held-out probe being exposed SEPARATELY,
- honest drop accounting (missing required field, bad winner) with no silent
  truncation,
- a malformed top-level payload failing LOUD,
- the committed PORTFOLIO_CASES.json loading with full coverage (8 scored + 2 probe).
"""

from __future__ import annotations

import pytest

from sidira_simulator.services.portfolio_archive import (
    load_portfolio_cases,
    parse_portfolio_archive,
)


def _good_case(**over):
    base = {
        "id": "case_a",
        "domain": "saas",
        "control": "Existing flow",
        "treatment": "New flow",
        "metric": "conversion",
        "real_winner": "treatment",
        "effect": "+10%",
        "counter_intuitive": "low",
        "contamination": "low",
        "credibility": "high",
        "source": "test",
        "raw_data": False,
    }
    base.update(over)
    return base


def _payload(**over):
    base = {
        "portfolio_id": "test-portfolio",
        "scored_cases": [_good_case()],
        "held_out_memorization_probe": [
            {
                "id": "probe_a",
                "change": "wall -> browse first",
                "real_winner": "control (won all 5)",
                "why_held_out": "famous",
            }
        ],
        "human_baseline_anchors": {"kohavi": "~2.3/8"},
        "balance_check": {"control_won_fraction": "5/8"},
    }
    base.update(over)
    return base


# ── BASIC PARSE ────────────────────────────────────────────────────────────────


def test_parse_well_formed_payload() -> None:
    arc, summary = parse_portfolio_archive(_payload())
    assert arc.portfolio_id == "test-portfolio"
    assert len(arc.scored_cases) == 1
    assert arc.scored_cases[0].id == "case_a"
    assert arc.scored_cases[0].real_winner == "treatment"
    assert summary.scored_kept == 1 and summary.scored_read == 1
    assert arc.human_baseline_anchors == {"kohavi": "~2.3/8"}


def test_scored_and_probe_are_separate() -> None:
    """The held-out probe is exposed SEPARATELY from the scored set (never folded
    into the scored cases — it is a contamination control)."""
    arc, summary = parse_portfolio_archive(_payload())
    assert len(arc.scored_cases) == 1
    assert len(arc.held_out_probe) == 1
    assert arc.held_out_probe[0].id == "probe_a"
    # No probe id leaks into the scored set.
    assert "probe_a" not in {c.id for c in arc.scored_cases}
    assert summary.probe_kept == 1


# ── HONEST DROP ACCOUNTING (no silent truncation) ───────────────────────────────


def test_missing_required_field_is_dropped_and_counted() -> None:
    payload = _payload(scored_cases=[_good_case(), _good_case(id="bad", control="")])
    arc, summary = parse_portfolio_archive(payload)
    assert summary.scored_read == 2
    assert summary.scored_kept == 1
    assert summary.scored_dropped_missing_field == 1
    assert {c.id for c in arc.scored_cases} == {"case_a"}
    assert summary.drop_reasons  # a human-readable reason was recorded


def test_bad_winner_is_dropped_and_counted() -> None:
    payload = _payload(scored_cases=[_good_case(), _good_case(id="tie", real_winner="tie")])
    arc, summary = parse_portfolio_archive(payload)
    assert summary.scored_kept == 1
    assert summary.scored_dropped_bad_winner == 1
    assert "tie" not in {c.id for c in arc.scored_cases}


def test_full_coverage_invariant() -> None:
    """read == kept + every drop (the no-silent-degradation conservation rule)."""
    payload = _payload(
        scored_cases=[
            _good_case(),
            _good_case(id="bad", metric=""),
            _good_case(id="badwin", real_winner="nope"),
        ]
    )
    _, s = parse_portfolio_archive(payload)
    assert (
        s.scored_read
        == s.scored_kept + s.scored_dropped_missing_field + s.scored_dropped_bad_winner
    )


# ── MALFORMED PAYLOAD FAILS LOUD ────────────────────────────────────────────────


def test_payload_missing_both_top_keys_raises() -> None:
    with pytest.raises(ValueError, match="neither 'scored_cases'"):
        parse_portfolio_archive({"portfolio_id": "x"})


def test_non_object_payload_raises() -> None:
    with pytest.raises(ValueError, match="must be a JSON object"):
        parse_portfolio_archive([])  # type: ignore[arg-type]


def test_scored_cases_not_a_list_raises() -> None:
    with pytest.raises(ValueError, match="'scored_cases' must be a JSON array"):
        parse_portfolio_archive({"scored_cases": {"id": "x"}})


# ── COMMITTED CURATED SET ───────────────────────────────────────────────────────


def test_committed_portfolio_loads_with_full_coverage() -> None:
    """The committed PORTFOLIO_CASES.json loads to the documented 8 scored + 2 probe."""
    arc, summary = load_portfolio_cases()
    assert summary.scored_kept == 8
    assert summary.scored_dropped_missing_field == 0
    assert summary.scored_dropped_bad_winner == 0
    assert summary.probe_kept == 2
    # Balance: the curated set keeps >= 40% control-won so a naive "change wins"
    # sim can't score well by default.
    control_won = sum(1 for c in arc.scored_cases if c.real_winner == "control")
    assert control_won == 5
    assert "kohavi_expert_survey" in arc.human_baseline_anchors
