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

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# ── The screening action (pivot contract) ────────────────────────────────
# The customer's only actionable output: should they spend a test slot on this?
# KILL = don't run it (we're confident it won't produce a ship-worthy win).
# PASS = run the real A/B (a predicted winner, or a not-confident-enough loser).
# ABSTAIN = we couldn't confidently judge — run the real A/B.
# Only KILL saves a test; PASS and ABSTAIN both route to "run it". The split is
# informational (judged-not-killed vs could-not-judge).
ScreenAction = Literal["KILL", "PASS", "ABSTAIN"]


def screen_action_from_verdict(verdict: DirectionVerdict) -> ScreenAction:
    """Map the direction-only verdict onto the KILL / PASS / ABSTAIN screen action.

    Safety-first, per the northstar (FN ceiling before coverage): we KILL ONLY on
    a *grounded, high-confidence* negative sign. Raw/low-confidence signal never
    kills — the campaign proved raw LLM confidence unusable, so we would rather
    ABSTAIN/PASS (send it to a real A/B) than risk killing a winner.

    - ``ABSTAIN`` ⇔ ``direction is None`` — no confident sign (the canonical
      inconclusive shape; ``caution`` is ``hard`` by the model invariant).
    - ``KILL`` ⇔ ``direction == "negative"`` AND ``caution == "none"`` AND
      ``source == "grounded"`` — a trustworthy grounded loser, i.e. confident the
      treatment will NOT win. The explicit ``source`` guard is defense-in-depth:
      a hand-corrupted/model-valid sidecar could carry ``llm_fallback`` +
      ``caution == "none"`` (the validator does not forbid that pairing), and we
      must NOT kill on an ungrounded verdict (FN ceiling before coverage).
    - ``PASS`` otherwise — a predicted winner (``positive``), or a negative sign
      that is not grounded-confident (``caution`` moderate). Run the real test.

    NOTE (follow-up): the "obvious no-op / flat" half of the KILL definition
    ("won't produce a win" = losers OR no-ops) is not yet expressible — the
    verdict has no ``flat`` direction. A confident no-op therefore PASSes today;
    a ``flat`` sign from the grounded predictor is the enhancement that lets it
    KILL. Tracked as a Track-2 follow-up.
    """
    if verdict.direction is None:
        return "ABSTAIN"
    if (
        verdict.direction == "negative"
        and verdict.caution == "none"
        and verdict.source == "grounded"
    ):
        return "KILL"
    return "PASS"


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
      - ``grounding_gap_reason``: the #564 "why" for a grounding-incomplete
        lever — e.g. ``"grounding-incomplete: no_vouched_negative_control"``.
        Built EXCLUSIVELY from the producer's fixed gap-token vocabulary (the
        builder allowlists tokens; producer free text never crosses), so it is
        structurally not a magnitude channel. None on every non-#564 path and on
        sidecars persisted before the field existed (legacy parses unchanged).
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
    grounding_gap_reason: str | None = None
    unverified: bool = False
    guardrails: list[GuardrailMetric] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _drop_derived_screen_action(cls, data: object) -> object:
        """Tolerate the derived ``screen_action`` on input so the contract
        round-trips (``model_dump`` → ``model_validate``) without weakening
        ``extra="forbid"``. ``screen_action`` is an output-only computed field;
        a serialized sidecar/result carries it, but it is RECOMPUTED on load, so
        we drop it from the input dict. Every OTHER unexpected key (e.g. a stray
        ``magnitude``) still fails loudly — the point-estimate guard is intact.
        """
        if isinstance(data, dict) and "screen_action" in data:
            return {k: v for k, v in data.items() if k != "screen_action"}
        return data

    @model_validator(mode="after")
    def _enforce_confidence_derivation(self) -> DirectionVerdict:
        """Reject a self-inconsistent verdict (e.g. a hand-corrupted sidecar).

        ``confidence`` is DERIVED from ``caution`` — ``high`` iff ``caution`` is
        ``none`` (a trustworthy grounded verdict), else ``low``. A trustworthy
        verdict (``caution == "none"``) must also carry a direction — you cannot
        "verify" a change with no sign. :func:`verdict_from_decision` always
        satisfies both, so this only guards a corrupt persisted body (the GET
        handler treats any model-valid sidecar as safe to surface — this makes
        "model-valid" mean "internally consistent") — it never trips the builder.
        """
        expected = "high" if self.caution == "none" else "low"
        if self.confidence != expected:
            raise ValueError(
                f"confidence={self.confidence!r} is inconsistent with "
                f"caution={self.caution!r} (expected {expected!r})"
            )
        if self.caution == "none" and self.direction is None:
            raise ValueError(
                "a trustworthy verdict (caution='none') must carry a direction"
            )
        if self.direction is None and self.caution != "hard":
            raise ValueError(
                "a no-direction verdict is an abstain and must have caution='hard' "
                f"(got caution={self.caution!r})"
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def screen_action(self) -> ScreenAction:
        """KILL / PASS / ABSTAIN — the customer's screening action.

        Derived from ``direction`` + ``caution`` and serialized on the contract
        so the card and the frontend read ONE field instead of re-deriving the
        mapping. See :func:`screen_action_from_verdict` for the rule.
        """
        return screen_action_from_verdict(self)


__all__ = [
    "GuardrailMetric",
    "DirectionVerdict",
    "ScreenAction",
    "screen_action_from_verdict",
]
