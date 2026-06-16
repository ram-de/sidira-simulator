"""Shared test fixtures.

#312 / T3: the pre-flight input-lint LLM judge runs on every POST /simulations.
The judge MUST never hit a live LLM in the suite (hard constraint). The
`get_input_lint_chat_client` FastAPI dependency returns ``None`` in production,
in which case ``assess_input_lint`` resolves the real client lazily inside the
judge via ``sidira_simulator.services.input_lint.get_chat_client``. Tests that
exercise the lint explicitly (``test_input_lint.py``,
``test_simulations_api.py``) inject their own stub. But many *other* API tests
(``test_arm_split.py``, ``test_agents_api.py``, ``test_persona_groups_api.py``,
...) POST /simulations only to exercise unrelated behavior and do NOT override
the dependency — without a global guard they would either make a live judge
call (if credentials are present) or silently exercise the judge-failed
degrade path.

This autouse fixture patches the lazily-resolved ``get_chat_client`` binding in
``input_lint`` to a green-returning stub for the whole suite, so the default
lint verdict is a deterministic, cost-free ``green`` (no flags). Tests that want
a specific verdict still override ``get_input_lint_chat_client`` (which takes
precedence — the explicit client short-circuits the lazy resolution) or call
``assess_input_lint`` with an explicit ``chat_client``.
"""

from __future__ import annotations

import pytest


class _GreenJudgeChat:
    """Minimal ChatClient stub: every judge call returns a clean green verdict."""

    def chat_json(self, messages, schema, *args, **kwargs):  # noqa: ANN001, ANN002, ANN003
        # Build through the schema so its field_validator runs, mirroring a real
        # judge response. Green carries no reasons.
        return schema(verdict="green", reasons=[])


@pytest.fixture(autouse=True)
def _stub_input_lint_judge(monkeypatch: pytest.MonkeyPatch) -> None:
    """Force the lazily-resolved input-lint judge client to a green stub.

    Patches the name as bound inside ``input_lint`` so the lazy
    ``InputLintJudge._chat`` path can never construct a real LLM client during
    the suite. Tests that need a non-green verdict inject their own stub.
    """
    import sidira_simulator.services.input_lint as input_lint

    monkeypatch.setattr(
        input_lint, "get_chat_client", lambda *a, **k: _GreenJudgeChat()
    )
