"""RefinementService tests — prompt rendering + cap-at-3 + graceful failure."""

from __future__ import annotations

import pytest

from sidira_simulator.adapters.llm import JSONRepairError
from sidira_simulator.schemas.scoring import RefinementInput, RefinementOutput
from sidira_simulator.schemas.simulation import Weakness
from sidira_simulator.services.refinement import RefinementService


def _payload(**overrides) -> RefinementInput:
    base = dict(
        hypothesis_prose="Add a reorder button to the home tab.",
        capability_name="reorder",
        confidence_score=52.0,
        top_weaknesses=[
            Weakness(category="wrong_cohort", summary="3/5 agents flagged this — wrong cohort."),
            Weakness(category="wrong_metric", summary="2/5 agents flagged this — wrong metric."),
        ],
        sample_reactions=["I would tap it.", "Not relevant to me.", "Maybe."],
    )
    base.update(overrides)
    return RefinementInput(**base)


def test_render_includes_all_inputs() -> None:
    rendered = RefinementService._render(_payload())
    assert "reorder button" in rendered
    assert "52.0/100" in rendered
    assert "wrong_cohort" in rendered
    assert "wrong_metric" in rendered
    # sample reactions appear in numbered list
    assert "1." in rendered and "2." in rendered


def test_render_handles_empty_weaknesses() -> None:
    rendered = RefinementService._render(_payload(top_weaknesses=[], sample_reactions=[]))
    assert "none diagnosed" in rendered


@pytest.mark.asyncio
async def test_suggest_caps_at_3() -> None:
    class _Verbose:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            return RefinementOutput(
                suggestions=[
                    "Suggestion 1",
                    "Suggestion 2",
                    "Suggestion 3",
                    "Suggestion 4",
                    "Suggestion 5",
                ]
            )

        def chat(self, *a, **k):  # pragma: no cover
            raise NotImplementedError

    svc = RefinementService(chat_client=_Verbose())
    suggestions = await svc.suggest(_payload())
    assert len(suggestions) == 3


@pytest.mark.asyncio
async def test_suggest_returns_empty_on_llm_failure() -> None:
    class _Broken:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            raise JSONRepairError("LLM returned garbage")

        def chat(self, *a, **k):  # pragma: no cover
            raise NotImplementedError

    svc = RefinementService(chat_client=_Broken())
    suggestions = await svc.suggest(_payload())
    assert suggestions == []


@pytest.mark.asyncio
async def test_suggest_warns_via_structlog_on_failure() -> None:
    """#70: refinement.py previously used stdlib logging.getLogger with no
    handler attached, so failure WARNs were silently swallowed. Switched to
    structlog; pin the visibility here."""
    import structlog

    class _Broken:
        def chat_json(self, messages, schema, max_tokens=4096, temperature=0.0, seed=None):
            raise JSONRepairError("LLM returned garbage")

        def chat(self, *a, **k):  # pragma: no cover
            raise NotImplementedError

    svc = RefinementService(chat_client=_Broken())
    with structlog.testing.capture_logs() as captured:
        suggestions = await svc.suggest(_payload())
    assert suggestions == []
    warn_events = [
        e
        for e in captured
        if e.get("log_level") == "warning" and e.get("event") == "refinement.failed"
    ]
    assert len(warn_events) == 1, f"expected 1 refinement.failed WARN, got {warn_events!r}"
    assert "LLM returned garbage" in warn_events[0]["error"]
    assert warn_events[0]["exc_type"] == "JSONRepairError"
