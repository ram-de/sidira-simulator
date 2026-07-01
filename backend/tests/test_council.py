"""3-model heterogeneous-bias council tests (Epic #538, ticket #543).

Pure: no live LLM, no network. Fake ``ChatClient``s inject the per-model vote
JSON via a client factory, and ``model_is_available`` is monkeypatched so the
suite controls which providers are "up". These tests reproduce the AGGREGATION
logic (the abstain-siren / caution-dial) with fixtures.

NOTE: reproducing the campaign's REAL-model flip-cell result end-to-end (three
live models actually disagreeing on a counter-intuitive case) is a FOUNDER-GATED
/ offline step — it costs money and is non-deterministic. The unit tests here
pin the deterministic aggregation policy, not the live-model behaviour.
"""

from __future__ import annotations

import pytest

from sidira_simulator.schemas.mechanism import MechanismSpec
from sidira_simulator.services import council as council_mod
from sidira_simulator.services.council import (
    DEFAULT_PANEL,
    CouncilDiversityError,
    CouncilVote,
    HeterogeneousCouncil,
    assert_bias_diversity,
    build_default_council,
)
from sidira_simulator.services.decision_flow import CouncilAssessment

SPEC = MechanismSpec(
    capability_name="gate_move",
    treatment_column="gate_level",
    treatment_contrast="gate at 30 vs gate at 40",
    outcome_column="day7_retention",
)


# ── fakes ─────────────────────────────────────────────────────────────────────


class _FakeChat:
    """A fake ChatClient whose ``chat_json`` returns a preset ``CouncilVote``."""

    def __init__(self, direction: str, rationale: str = "mechanism") -> None:
        self._vote = CouncilVote(direction=direction, rationale=rationale)

    def chat_json(self, messages, schema, max_tokens=256, temperature=0.0, seed=None):  # noqa: ANN001
        return self._vote


class _ExplodingChat:
    """A fake ChatClient whose ``chat_json`` always raises."""

    def chat_json(self, messages, schema, max_tokens=256, temperature=0.0, seed=None):  # noqa: ANN001
        raise RuntimeError("boom")


def _factory(mapping: dict[str, object]):
    """Build a client_factory over a per-model-id → fake-client mapping."""

    def _make(model_id: str):
        client = mapping.get(model_id)
        if client is None:
            raise RuntimeError(f"no client for {model_id}")
        return client

    return _make


@pytest.fixture
def all_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """Every panel model reports available."""
    monkeypatch.setattr(council_mod, "model_is_available", lambda model_id: True)


@pytest.fixture
def none_available(monkeypatch: pytest.MonkeyPatch) -> None:
    """No provider is configured."""
    monkeypatch.setattr(council_mod, "model_is_available", lambda model_id: False)


def _council(mapping: dict[str, object]) -> HeterogeneousCouncil:
    return HeterogeneousCouncil(
        DEFAULT_PANEL,
        client_factory=_factory(mapping),
        per_model_timeout=5.0,
    )


# ── aggregation branches ───────────────────────────────────────────────────────


def test_unanimous_positive_agreement(all_available: None) -> None:
    council = _council({m: _FakeChat("positive") for m in DEFAULT_PANEL})
    result = council.assess("prose", SPEC)
    assert isinstance(result, CouncilAssessment)
    assert result.agreement is True
    assert result.llm_direction == "positive"
    assert sum(1 for v in result.votes if v.status == "voted") == 3


def test_unanimous_negative_agreement(all_available: None) -> None:
    council = _council({m: _FakeChat("negative") for m in DEFAULT_PANEL})
    result = council.assess("prose", SPEC)
    assert result.agreement is True
    assert result.llm_direction == "negative"


def test_split_votes_disagreement_hard_caution(all_available: None) -> None:
    # The "flip cell": models disagree on the sign → any-of-N disagree → no arrow.
    a, b, c = DEFAULT_PANEL
    council = _council(
        {a: _FakeChat("positive"), b: _FakeChat("negative"), c: _FakeChat("positive")}
    )
    result = council.assess("prose", SPEC)
    assert result.agreement is False
    assert result.llm_direction is None


def test_one_model_errors_other_two_agree_still_agreement(all_available: None) -> None:
    # Graceful degradation: a dropped member still leaves 2 agreeing directional votes.
    a, b, c = DEFAULT_PANEL
    council = _council(
        {a: _FakeChat("positive"), b: _ExplodingChat(), c: _FakeChat("positive")}
    )
    result = council.assess("prose", SPEC)
    assert result.agreement is True
    assert result.llm_direction == "positive"
    assert any(v.status == "error" for v in result.votes)


def test_only_one_usable_model_is_conservative(all_available: None) -> None:
    # < 2 usable directional votes → cannot certify a consensus → agreement False.
    a, b, c = DEFAULT_PANEL
    council = _council(
        {a: _FakeChat("positive"), b: _ExplodingChat(), c: _ExplodingChat()}
    )
    result = council.assess("prose", SPEC)
    assert result.agreement is False
    assert result.llm_direction is None


def test_abstains_do_not_count(all_available: None) -> None:
    # Two abstain, one positive → only 1 usable directional → conservative.
    a, b, c = DEFAULT_PANEL
    council = _council(
        {a: _FakeChat("abstain"), b: _FakeChat("abstain"), c: _FakeChat("positive")}
    )
    result = council.assess("prose", SPEC)
    assert result.agreement is False
    assert result.llm_direction is None
    assert sum(1 for v in result.votes if v.status == "abstained") == 2


def test_all_providers_down_never_raises(none_available: None) -> None:
    council = _council({m: _FakeChat("positive") for m in DEFAULT_PANEL})
    result = council.assess("prose", SPEC)
    assert result.agreement is False
    assert result.llm_direction is None
    assert all(v.status == "unavailable" for v in result.votes)


def test_assess_never_raises_on_exploding_client(all_available: None) -> None:
    # Even if every member explodes, assess returns a safe assessment.
    council = _council({m: _ExplodingChat() for m in DEFAULT_PANEL})
    result = council.assess("prose", SPEC)
    assert isinstance(result, CouncilAssessment)
    assert result.agreement is False
    assert result.llm_direction is None


# ── bias-diversity guard ───────────────────────────────────────────────────────


def test_assert_bias_diversity_passes_on_default_panel() -> None:
    assert_bias_diversity(DEFAULT_PANEL)  # does not raise


def test_assert_bias_diversity_fails_on_all_same_profile() -> None:
    # A degenerate all-optimist panel (shared prior → agree-and-are-wrong).
    with pytest.raises(CouncilDiversityError):
        assert_bias_diversity(["llama-3.1-8b-instant", "llama-3.1-8b-instant"])


def test_assert_bias_diversity_fails_on_single_member() -> None:
    with pytest.raises(CouncilDiversityError):
        assert_bias_diversity(["llama-3.1-8b-instant"])


def test_assert_bias_diversity_fails_on_all_unknown() -> None:
    # Undocumented models have unmeasured bias → cannot certify diversity.
    with pytest.raises(CouncilDiversityError):
        assert_bias_diversity(["mystery-model-a", "mystery-model-b"])


def test_constructor_rejects_degenerate_panel() -> None:
    with pytest.raises(CouncilDiversityError):
        HeterogeneousCouncil(["llama-3.1-8b-instant", "llama-3.1-8b-instant"])


def test_build_default_council_is_diverse() -> None:
    council = build_default_council()
    assert isinstance(council, HeterogeneousCouncil)


def test_council_satisfies_protocol() -> None:
    from sidira_simulator.services.decision_flow import Council

    assert isinstance(build_default_council(), Council)
