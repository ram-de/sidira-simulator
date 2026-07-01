"""Backlog triage ranker tests (Epic #538, ticket #545).

Pure: no R2, no live LLM. `decide` is monkeypatched per-hypothesis to inject the
DecisionResult (so we test the RANKER, not the router — which has its own suite).
Covers the three buckets, ranked order, and the never-raises-on-exploding-decide
contract.
"""

from __future__ import annotations

from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services import triage as triage_mod
from sidira_simulator.services.decision_flow import DecisionResult
from sidira_simulator.services.triage import TriageReport, triage_backlog


def _spec() -> MechanismSpec:
    return MechanismSpec(
        capability_name="cap",
        treatment_column="t",
        treatment_contrast="a vs b",
        outcome_column="y",
        sibling_metric="sib",
        negative_controls=["nc1"],
    )


def _hyp(name: str) -> Hypothesis:
    return Hypothesis(capability_name=name, prose=f"change {name}")


def _grounded_positive() -> DecisionResult:
    return DecisionResult(
        source="grounded", direction="positive", caution="none",
        label="verified verdict", watchdog_verdict="CONFIRMS",
        mechanism_spec=_spec(), grounded=None, reason="t",
    )


def _grounded_negative() -> DecisionResult:
    return DecisionResult(
        source="grounded", direction="negative", caution="none",
        label="verified — data overrides intuition", watchdog_verdict="CONTRADICTS",
        mechanism_spec=_spec(), grounded=None, reason="t",
    )


def _abstain() -> DecisionResult:
    return DecisionResult(
        source="llm_fallback", direction=None, caution="hard",
        label="inconclusive — test it", watchdog_verdict="CANT_VALIDATE",
        mechanism_spec=_spec(), grounded=None, reason="t",
    )


def _defensive_error() -> DecisionResult:
    """The decide() exception path shape: watchdog_verdict None + no direction."""
    return DecisionResult(
        source="llm_fallback", direction=None, caution="hard",
        label="inconclusive — test it", watchdog_verdict=None,
        mechanism_spec=_spec(), grounded=None, reason="errored",
    )


def _install_decides(monkeypatch, mapping):
    """Monkeypatch decide to return mapping[capability_name] per hypothesis."""

    def fake_decide(hypothesis, *a, **k):
        return mapping[hypothesis.capability_name]

    monkeypatch.setattr(triage_mod, "decide", fake_decide)


def test_triage_buckets_mixed_backlog(monkeypatch):
    mapping = {
        "win": _grounded_positive(),
        "loser": _grounded_negative(),
        "unknown": _abstain(),
    }
    _install_decides(monkeypatch, mapping)

    report = triage_backlog(
        [_hyp("loser"), _hyp("unknown"), _hyp("win")],
        available_columns=["t", "y"],
        customer_id="c",
        pack_version="v",
        manifest=None,  # known-absent → skip the R2 read
    )
    assert isinstance(report, TriageReport)

    by_cap = {it.hypothesis.capability_name: it for it in report.items}
    assert by_cap["loser"].bucket == "this-one-loses"
    assert by_cap["win"].bucket == "test"
    assert by_cap["unknown"].bucket == "test"

    # The confident WIN outranks the abstain, which outranks the predicted loser.
    order = [it.hypothesis.capability_name for it in report.items]
    assert order.index("win") < order.index("unknown") < order.index("loser")


def test_triage_this_one_loses_is_the_cost_saver(monkeypatch):
    _install_decides(monkeypatch, {"loser": _grounded_negative()})
    report = triage_backlog([_hyp("loser")], ["t", "y"], "c", "v", manifest=None)
    item = report.items[0]
    assert item.bucket == "this-one-loses"
    assert item.verdict.direction == "negative"
    assert item.verdict.confidence == "high"
    assert "don't build" in item.rank_reason


def test_triage_positive_is_test_high_priority(monkeypatch):
    _install_decides(monkeypatch, {"win": _grounded_positive()})
    report = triage_backlog([_hyp("win")], ["t", "y"], "c", "v", manifest=None)
    item = report.items[0]
    assert item.bucket == "test"
    assert item.verdict.direction == "positive"
    assert item.verdict.unverified is False


def test_triage_defensive_no_watchdog_is_skip(monkeypatch):
    _install_decides(monkeypatch, {"broke": _defensive_error()})
    report = triage_backlog([_hyp("broke")], ["t", "y"], "c", "v", manifest=None)
    assert report.items[0].bucket == "skip"


def test_triage_never_raises_on_exploding_decide(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("decide exploded")

    monkeypatch.setattr(triage_mod, "decide", boom)

    # Must not raise; the exploded hypothesis lands in `skip` with an abstain verdict.
    report = triage_backlog([_hyp("x"), _hyp("y")], ["t"], "c", "v", manifest=None)
    assert len(report.items) == 2
    assert all(it.bucket == "skip" for it in report.items)
    assert all(it.verdict.direction is None for it in report.items)


def test_triage_by_bucket_helper(monkeypatch):
    _install_decides(
        monkeypatch,
        {"a": _grounded_positive(), "b": _grounded_negative(), "c": _abstain()},
    )
    report = triage_backlog(
        [_hyp("a"), _hyp("b"), _hyp("c")], ["t", "y"], "c", "v", manifest=None
    )
    assert len(report.by_bucket("test")) == 2
    assert len(report.by_bucket("this-one-loses")) == 1
    assert report.by_bucket("skip") == []


def test_triage_empty_backlog(monkeypatch):
    _install_decides(monkeypatch, {})
    report = triage_backlog([], ["t"], "c", "v", manifest=None)
    assert report.items == []
