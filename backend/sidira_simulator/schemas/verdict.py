"""Direction-only output contract — the customer-facing verdict (Epic #538, #545).

The engine's disproven persona-sim role-play predicted a *calibrated magnitude*;
the rewire (Epic #538) replaced it with a grounded, **direction-only** pipeline
(translator → grounded predictor → watchdog → LLM fallback, wired by #542). This
schema is the CONTRACT at the FRONT of the customer surface: what a PM is allowed
to see is a **sign + a confidence/abstain**, never a point-estimate magnitude.

Why no magnitude, structurally? Our own Cookie Cats magnitude was ~40% off with
the RIGHT sign — the sign is the trustworthy signal, the number is not (yet). So
:class:`DirectionVerdict` carries NO float/magnitude field of any kind, and is
``extra="forbid"``: constructing it with ``magnitude=...`` / ``ate=...`` /
``lift=...`` raises a ``ValidationError``. The schema STRUCTURALLY forbids a
point-estimate — magnitude stays backstage (the grounded ``candidate`` carries the
raw estimates for later calibration; they never reach this contract).

**Confidence / abstain representation.** ``caution`` is the authoritative ordinal
(``none`` = trustworthy grounded verdict, ``moderate`` = unverified LLM take,
``hard`` = inconclusive). ``confidence`` is a coarse two-level derivation of it
(``high`` iff ``caution == "none"``, else ``low``) for a card that only wants a
binary trust chip. **Abstain ⇔ ``direction is None`` AND ``caution == "hard"``**
(no arrow, "inconclusive — test it") — the one canonical no-verdict shape.

**Guardrail breadth.** ``guardrails`` surfaces the sibling + negative-control
metric NAMES (and roles) the mechanism spec named, so the PM sees the *breadth* of
what was watched — not just the headline outcome. NAMES + roles only; a
:class:`GuardrailMetric` also carries no magnitude.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class GuardrailMetric(BaseModel):
    """One guardrail metric surfaced beside the headline (NAME + role, no number).

    ``role`` distinguishes a ``sibling`` / cannibalization metric (a co-moving
    outcome to watch for a lift that merely shifts volume) from a
    ``negative_control`` (an outcome the treatment should NOT cause but which
    shares the confounding — the watchdog's evidence). Carries no magnitude:
    ``extra="forbid"`` so a stray numeric field fails loudly.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    role: Literal["sibling", "negative_control"]
    note: str | None = None


class DirectionVerdict(BaseModel):
    """The customer-facing verdict: sign + confidence/abstain, NEVER a magnitude.

    ``extra="forbid"`` + the deliberate ABSENCE of any float/magnitude field is
    the structural guarantee: a caller cannot smuggle a point-estimate through
    this contract (``DirectionVerdict(magnitude=0.4)`` raises ``ValidationError``).

    Fields:
      - ``direction``: ``positive`` / ``negative``, or None = no arrow / abstain.
      - ``caution``: authoritative ordinal — ``none`` (trustworthy grounded),
        ``moderate`` (unverified LLM take), ``hard`` (inconclusive / abstain).
      - ``confidence``: coarse two-level chip derived from ``caution`` — ``high``
        iff ``caution == "none"``, else ``low``.
      - ``label``: the customer-facing framing string (from the decision router).
      - ``source``: ``grounded`` (authoritative empirical) or ``llm_fallback``.
      - ``watchdog_verdict``: CONFIRMS / CONTRADICTS / CANT_VALIDATE, or None when
        the watchdog never ran (defensive path).
      - ``unverified``: True on the ``llm_fallback`` branch (hypothesis, not
        verdict).
      - ``guardrails``: sibling + negative-control metric NAMES + roles (breadth).

    Abstain ⇔ ``direction is None`` AND ``caution == "hard"`` (and ``confidence``
    is then ``low``).
    """

    model_config = ConfigDict(extra="forbid")

    direction: Literal["positive", "negative"] | None
    caution: Literal["none", "moderate", "hard"]
    confidence: Literal["high", "low"]
    label: str
    source: Literal["grounded", "llm_fallback"]
    watchdog_verdict: str | None = None
    unverified: bool = False
    guardrails: list[GuardrailMetric] = Field(default_factory=list)


__all__ = ["GuardrailMetric", "DirectionVerdict"]
