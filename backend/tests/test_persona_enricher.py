"""#342 persona-description enricher: jargon-described clusters get a language
description; already-named packs are untouched (no-op, no LLM call)."""
from __future__ import annotations

from sidira_simulator.schemas.persona import Persona
from sidira_simulator.services.persona_enricher import (
    needs_enrichment, enrich_description, enrich_persona,
)


class _CannedChat:
    def __init__(self, text): self.text = text; self.calls = 0
    def chat(self, messages, max_tokens=4096, temperature=0.0, seed=None):
        self.calls += 1; return self.text
    def chat_json(self, *a, **k):  # pragma: no cover
        raise NotImplementedError


def _unnamed():
    return Persona(id="P01", name="Persona01",
                   description="Discovered cluster — LLM naming unavailable. Top distinctive "
                               "features vs. baseline: mens (+1.20σ); history (-0.60σ)",
                   centroid_features={"mens": 1.2, "womens": -0.8, "history": -0.6, "noise": 0.1})


def _named():
    return Persona(id="P9", name="Bargain hunters",
                   description="Price-sensitive shoppers who buy on promotion.",
                   centroid_features={"mens": 1.2})


def test_needs_enrichment_detects_unnamed_vs_named() -> None:
    assert needs_enrichment(_unnamed()) is True
    assert needs_enrichment(_named()) is False
    # no features → nothing to enrich
    assert needs_enrichment(Persona(id="x", name="x", description="Discovered cluster")) is False


def test_enrich_persona_replaces_unnamed_description() -> None:
    chat = _CannedChat("Men's-leaning shoppers with below-average prior spend.")
    out = enrich_persona(_unnamed(), chat)
    assert out.description == "Men's-leaning shoppers with below-average prior spend."
    assert "Discovered cluster" not in out.description
    assert chat.calls == 1
    # the salient features were sent (mens/history), the sub-threshold one dropped
    # (we can't read messages here, but the call happened and produced the canned text)


def test_enrich_persona_is_noop_for_named_pack() -> None:
    chat = _CannedChat("SHOULD NOT BE USED")
    out = enrich_persona(_named(), chat)
    assert out.description == "Price-sensitive shoppers who buy on promotion."
    assert chat.calls == 0  # no LLM call for an already-named persona


def test_enrich_description_returns_existing_when_no_salient_features() -> None:
    p = Persona(id="x", name="x", description="Discovered cluster placeholder",
                centroid_features={"a": 0.1, "b": -0.05})  # all |z| < 0.3
    chat = _CannedChat("unused")
    assert enrich_description(p, chat) == "Discovered cluster placeholder"
    assert chat.calls == 0
