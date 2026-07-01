"""Tests for the LLM-as-translator (Epic #538, ticket #539 / Phase-1a).

The translator NEVER hits a live LLM here — every test injects a stubbed
`ChatClient` that returns a canned `_TranslatorOutput` (mirroring the
`_StubJudgeChat` pattern in ``test_input_lint.py`` and the autouse stub in
``conftest.py``). The suite exercises: a clean mappable decomposition, the
referential-integrity catch (a column the data doesn't have), an ungrounded
anchor (null treatment/outcome), and a hard LLM/parse failure — all four of which
must return a spec, never raise.
"""

from __future__ import annotations

import pytest

from sidira_simulator.adapters.llm import JSONRepairError
from sidira_simulator.schemas.simulation import Hypothesis
from sidira_simulator.services.mechanism_translator import translate_hypothesis

_COLUMNS = ["version", "retention_7", "retention_1", "logeng", "sum_gamerounds"]


def _hyp() -> Hypothesis:
    return Hypothesis(
        capability_name="progression_gate",
        prose="Move the progression gate from level 30 to level 40 to see if it lifts retention.",
    )


class _StubTranslatorChat:
    """A stubbed ChatClient for the translator.

    Builds the canned response THROUGH the passed `schema` (`_TranslatorOutput`)
    so its parsing/defaults run exactly as in prod. `raise_exc` simulates the
    adapter's failure surface (e.g. a `JSONRepairError` on unparseable output).
    Records `calls` so a test can assert exactly one translator round-trip.
    """

    def __init__(self, payload: dict | None = None, *, raise_exc: Exception | None = None) -> None:
        self._payload = payload or {}
        self._raise = raise_exc
        self.calls = 0

    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):  # pragma: no cover
        raise NotImplementedError("translator uses chat_json only")

    def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
        self.calls += 1
        if self._raise is not None:
            raise self._raise
        return schema(**self._payload)


def test_clean_case_is_mappable() -> None:
    """Treatment + outcome + covariates + neg-controls all present and in-data."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate at level 30 vs gate at level 40",
            "outcome_column": "retention_7",
            "mediator": "sum_gamerounds",
            "covariates": ["logeng"],
            "negative_controls": ["retention_1"],
            "confidence": "high",
        }
    )
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert stub.calls == 1
    assert spec.mappable is True
    assert spec.unmapped_reason is None
    assert spec.capability_name == "progression_gate"
    assert spec.treatment_column == "version"
    assert spec.outcome_column == "retention_7"
    assert spec.mediator == "sum_gamerounds"
    assert spec.covariates == ["logeng"]
    assert spec.negative_controls == ["retention_1"]
    assert spec.confidence == "high"


def test_column_not_in_available_is_not_mappable() -> None:
    """Referential integrity: the LLM names an outcome the data doesn't have."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate 30 vs gate 40",
            "outcome_column": "churn_rate",  # not in _COLUMNS
            "covariates": ["logeng"],
        }
    )
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is False
    assert spec.unmapped_reason is not None
    assert "churn_rate" in spec.unmapped_reason


def test_dangling_covariate_is_not_mappable() -> None:
    """A covariate outside the available set also trips referential integrity."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate 30 vs gate 40",
            "outcome_column": "retention_7",
            "covariates": ["logeng", "made_up_feature"],
        }
    )
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is False
    assert "made_up_feature" in (spec.unmapped_reason or "")


def test_missing_treatment_is_not_mappable() -> None:
    """The LLM could not ground a treatment → null → not mappable."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": None,
            "treatment_contrast": "(none groundable)",
            "outcome_column": "retention_7",
        }
    )
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is False
    assert "treatment_column" in (spec.unmapped_reason or "")


def test_missing_outcome_is_not_mappable() -> None:
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate 30 vs gate 40",
            "outcome_column": None,
        }
    )
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is False
    assert "outcome_column" in (spec.unmapped_reason or "")


def test_malformed_llm_output_degrades_gracefully() -> None:
    """An unparseable LLM response (JSONRepairError) → mappable=False, no raise."""
    stub = _StubTranslatorChat(raise_exc=JSONRepairError("could not coerce output"))
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is False
    assert spec.treatment_column is None
    assert spec.outcome_column is None
    assert "translator call failed" in (spec.unmapped_reason or "")


def test_arbitrary_llm_exception_degrades_gracefully() -> None:
    """Any transport error is caught — the translator never raises into the caller."""
    stub = _StubTranslatorChat(raise_exc=RuntimeError("boom"))
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is False
    assert "translator call failed" in (spec.unmapped_reason or "")


def test_off_taxonomy_confidence_degrades_to_low() -> None:
    """A confidence value outside {high, low} is coerced to 'low', never raises."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate 30 vs gate 40",
            "outcome_column": "retention_7",
            "confidence": "medium",  # off-taxonomy
        }
    )
    spec = translate_hypothesis(_hyp(), _COLUMNS, chat_client=stub)

    assert spec.mappable is True
    assert spec.confidence == "low"


def test_empty_available_columns_yields_unmappable() -> None:
    """With no columns to ground to, any named column dangles → not mappable."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate 30 vs gate 40",
            "outcome_column": "retention_7",
        }
    )
    spec = translate_hypothesis(_hyp(), [], chat_client=stub)

    assert spec.mappable is False


def test_blank_columns_are_filtered_before_grounding() -> None:
    """Whitespace/empty entries in available_columns are ignored, not treated as valid."""
    stub = _StubTranslatorChat(
        {
            "treatment_column": "version",
            "treatment_contrast": "gate 30 vs gate 40",
            "outcome_column": "retention_7",
            "covariates": [],
        }
    )
    spec = translate_hypothesis(_hyp(), ["version", "  ", "", "retention_7"], chat_client=stub)

    assert spec.mappable is True


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
