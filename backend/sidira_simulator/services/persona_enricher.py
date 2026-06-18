"""Persona-description enricher (#342).

A persona's `centroid_features` (the cluster's z-scored deviations from the average
customer — e.g. `mens: +1.2`, `history: -0.6`) carry the segment signal, but packs
built without the upstream LLM cluster-naming step describe them only as raw-stat
jargon ("Discovered cluster — LLM naming unavailable. … value_sensitivity.history
(-0.60σ)"). The comparative metric pass recovers the who-responds-more heterogeneity
only when the audience is described in *language* (validated: enricher-generated
descriptions ρ +0.457 vs raw-jargon ~0). This module turns the z-scored features
into a plain-language description.

Upstream (sidira-personas) should run LLM naming at pack-build time; this is the
in-repo enricher + the seam to apply it to a loaded pack whose descriptions were
not LLM-named. Default is a no-op for already-named packs, so it is safe to apply
unconditionally.
"""
from __future__ import annotations

import json

from sidira_simulator.adapters.llm import ChatClient
from sidira_simulator.schemas.persona import Persona

# Markers an upstream build leaves when the LLM cluster-naming step did not run.
_UNNAMED_MARKERS = (
    "LLM naming unavailable",
    "Discovered cluster",
    "not generated",
)
# Render only features whose |z| clears this — mirrors behavioral_profile's
# salience floor so the description names the distinctive features, not noise.
_SALIENCE = 0.3


def needs_enrichment(persona: Persona) -> bool:
    """True when the persona carries feature signal but its description is the
    upstream un-named placeholder (raw-stat jargon), so language enrichment helps."""
    desc = persona.description or ""
    return bool(persona.centroid_features) and any(m in desc for m in _UNNAMED_MARKERS)


def enrich_description(persona: Persona, chat_client: ChatClient, *, salience: float = _SALIENCE) -> str:
    """Z-scored centroid features → a plain-language audience description (1–2
    sentences). Returns the existing description unchanged if there is no salient
    signal to describe."""
    salient = {
        k: round(v, 2)
        for k, v in (persona.centroid_features or {}).items()
        if abs(v) >= salience
    }
    if not salient:
        return persona.description or ""
    messages = [
        {"role": "system", "content":
            "You translate a customer segment's z-scored feature deviations (vs the "
            "average customer; positive = above average, negative = below) into a "
            "plain-language audience description for a marketing analyst. No jargon, no "
            "z-scores, no raw feature names — describe who these customers ARE in 1–2 "
            "sentences a human can reason about."},
        {"role": "user", "content":
            "Segment feature deviations (z-scores vs the average customer):\n"
            + json.dumps(salient, indent=2)
            + "\n\nWrite a 1–2 sentence plain-language description of who these customers "
            "are (what they buy, recency, spend, tenure, channel — whatever the features "
            "imply). Output only the description."},
    ]
    return chat_client.chat(messages, max_tokens=160, temperature=0.0).strip()


def enrich_persona(persona: Persona, chat_client: ChatClient) -> Persona:
    """Return a copy of `persona` with an enriched description when it needs one;
    otherwise the persona unchanged (no-op for already-named packs)."""
    if not needs_enrichment(persona):
        return persona
    return persona.model_copy(update={"description": enrich_description(persona, chat_client)})
