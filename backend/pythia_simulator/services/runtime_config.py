"""Runtime config helpers shared by API routes and UI config endpoints."""

from __future__ import annotations

import os

DEFAULT_MAX_AGENTS = 50


def resolve_max_agents_per_simulation() -> int:
    """Resolve the effective simulation cap used by POST /simulations.

    Malformed env values fail open to the default. Non-positive values clamp to
    one so a bad deployment env cannot create zero-agent simulations.
    """
    raw = os.environ.get("PYTHIA_MAX_AGENTS", str(DEFAULT_MAX_AGENTS))
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_MAX_AGENTS
    if parsed < 1:
        return 1
    return parsed
