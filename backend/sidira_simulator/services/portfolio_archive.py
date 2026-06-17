"""Product-change directional-portfolio archive loader (in-scope positive campaign).

The Cookie Cats / Hillstrom harnesses each score ONE external A/B. A single
experiment cannot be CERTIFIED — the null-integrity certificate needs >= 8
INDEPENDENT directional bits. This module is the ingestion edge for the
"product-change directional portfolio": a curated set of ~8 DIFFERENT real
product-change A/B tests, each a WHOLE-EXPERIMENT directional bit (one published
control-vs-treatment narrative with a known `real_winner`).

Unlike Cookie Cats (raw per-user rows) the portfolio cases are PUBLISHED
NARRATIVES: a described control, a described treatment, a metric, and the
REPORTED winner / effect. There is no per-user data to re-analyze, so the harness
scores the sim against the reported direction, not by re-computing rates (the
`structural_reality` note in PORTFOLIO_CASES.json — no public source carries
named treatments + raw rows + an in-scope product change together).

This loader is the portfolio mirror of `services.cookiecats_archive` /
`services.hillstrom_archive`: it parses the committed
`PORTFOLIO_CASES.json` into typed `PortfolioCase` objects the
`services.portfolio_adapter` turns into `BenchmarkCase`s. Two halves, same
discipline as the sibling loaders:

  - `load_portfolio_cases(json_path)` / `parse_portfolio_archive(payload)` — a
    pure-ish stdlib `json` parse of an ALREADY-PRESENT local file into typed
    `PortfolioCase`s, with a `PortfolioLoadSummary` accounting for every dropped
    case (no silent truncation). The parsing core takes an already-decoded dict
    so it is testable on an in-memory payload with ZERO file I/O.

  - the SCORED set (`scored_cases`) and the HELD-OUT memorization probe
    (`held_out_memorization_probe`) are exposed SEPARATELY: the probe is a
    contamination control (famous results an LLM may have memorized), never
    scored by default. A harness that aces the famous ones but flunks the obscure
    scored ones is reciting, not reasoning.

No ground-truth / winner-sign math lives here — that is the adapter's
(`portfolio_adapter`) job. The loader only carries the typed per-case
control / treatment / metric / real_winner narrative + the methodology anchors
(human baselines, balance check) a run reports for context.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# The default committed data path: the curated portfolio cases live in the
# agent-behavior-spec session dir, NOT under backend/, because the JSON is a
# research artifact (committed narratives), not application data. The CLI binds
# this as its --cases-path default; tests pass an in-memory payload.
DEFAULT_CASES_PATH = (
    Path(__file__).resolve().parents[3]
    / "sessions"
    / "agent-behavior-spec"
    / "portfolio-benchmark"
    / "PORTFOLIO_CASES.json"
)

# The two valid winners. A case whose `real_winner` is neither is a malformed
# row (it cannot anchor a directional bit) and is dropped + counted, never
# coerced.
WINNER_CONTROL = "control"
WINNER_TREATMENT = "treatment"
VALID_WINNERS = frozenset({WINNER_CONTROL, WINNER_TREATMENT})

# The required narrative fields on a scored case. A case missing any of these
# carries no directional bit and is dropped (with a counted reason), exactly as
# the sibling loaders drop a row with a blank required cell.
_REQUIRED_SCORED_FIELDS = ("id", "control", "treatment", "metric", "real_winner")


@dataclass(frozen=True)
class PortfolioCase:
    """One typed product-change directional case (a whole experiment = one bit).

    `control` / `treatment` are the PUBLISHED narrative descriptions of the two
    states; `metric` is the reported outcome name; `real_winner` is the REPORTED
    winning arm ("control" or "treatment") the harness scores the sim's
    prediction against. The remaining fields are metadata carried for the honesty
    table / report context (domain, effect string, contamination, credibility,
    source); `effect` is the human-readable effect string and is NEVER shown to
    the engine (it leaks magnitude) — it rides along only for reporting.
    """

    id: str
    domain: str
    control: str
    treatment: str
    metric: str
    real_winner: str
    effect: str
    counter_intuitive: str
    contamination: str
    credibility: str
    source: str
    raw_data: bool
    caveat: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class HeldOutProbe:
    """One held-out memorization-probe case (contamination control).

    These are famous results an LLM may have memorized, kept OUT of the scored
    set. They carry a compact `change` description (not a split control/treatment
    pair) and `real_winner` text, plus the `why_held_out` rationale. Exposed so a
    run can OPTIONALLY score them as a SEPARATE, clearly-labelled, NON-scored
    section — if the sim aces the famous ones but flunks the obscure scored ones,
    it is reciting, not reasoning.
    """

    id: str
    change: str
    real_winner: str
    why_held_out: str


@dataclass(frozen=True)
class PortfolioArchive:
    """The parsed portfolio: scored cases + held-out probe + reporting anchors.

    `human_baseline_anchors` carries the Kohavi expert-survey (~2.3/8) and MSN
    Real-Estate (3/21 experts) baselines the report prints next to the sim's
    score for context. `balance_check` carries the control-won fraction so a
    naive "the change always wins" sim cannot score well by default.
    """

    portfolio_id: str
    scored_cases: list[PortfolioCase]
    held_out_probe: list[HeldOutProbe]
    human_baseline_anchors: dict[str, str]
    balance_check: dict[str, Any]
    methodology: dict[str, Any]


@dataclass
class PortfolioLoadSummary:
    """Honest accounting of one load: what became a case, what was dropped, why.

    Every input case is conserved: ``scored_read`` equals ``scored_kept`` plus
    every drop. Nothing is silently truncated — a caller can assert full coverage
    from these counts (the no-silent-degradation rule shared with the Cookie Cats
    / Hillstrom loaders).
    """

    scored_read: int = 0
    scored_kept: int = 0
    scored_dropped_missing_field: int = 0
    scored_dropped_bad_winner: int = 0
    probe_read: int = 0
    probe_kept: int = 0
    drop_reasons: list[str] = field(default_factory=list)

    def note(self, reason: str) -> None:
        # Bounded human-readable trail (mirrors the sibling summaries' cap).
        if len(self.drop_reasons) < 50:
            self.drop_reasons.append(reason)


def _clean(raw: Any) -> str:
    """Stringify + strip a JSON cell. None becomes the empty string."""
    if raw is None:
        return ""
    return str(raw).strip()


def _opt(raw: Any) -> str | None:
    """An optional string cell: stripped, or None if absent/blank."""
    text = _clean(raw)
    return text or None


def _parse_scored_case(
    row: Mapping[str, Any], summary: PortfolioLoadSummary
) -> PortfolioCase | None:
    """Parse one `scored_cases` entry into a `PortfolioCase`, or drop+count it.

    A missing required narrative field (id / control / treatment / metric /
    real_winner) or a `real_winner` outside {control, treatment} drops the case
    with a counted reason rather than fabricating a directional bit.
    """
    missing = [f for f in _REQUIRED_SCORED_FIELDS if not _clean(row.get(f))]
    if missing:
        summary.scored_dropped_missing_field += 1
        summary.note(f"case {row.get('id', '<no id>')!r} missing required field(s) {missing}")
        return None

    winner = _clean(row.get("real_winner")).lower()
    if winner not in VALID_WINNERS:
        summary.scored_dropped_bad_winner += 1
        summary.note(f"case {row.get('id')!r} has unrecognized real_winner {winner!r}")
        return None

    return PortfolioCase(
        id=_clean(row.get("id")),
        domain=_clean(row.get("domain")) or "unspecified",
        control=_clean(row.get("control")),
        treatment=_clean(row.get("treatment")),
        metric=_clean(row.get("metric")),
        real_winner=winner,
        effect=_clean(row.get("effect")),
        counter_intuitive=_clean(row.get("counter_intuitive")) or "unspecified",
        contamination=_clean(row.get("contamination")) or "unspecified",
        credibility=_clean(row.get("credibility")) or "unspecified",
        source=_clean(row.get("source")) or "unspecified",
        raw_data=bool(row.get("raw_data", False)),
        caveat=_opt(row.get("caveat")),
        note=_opt(row.get("note")),
    )


def _parse_probe(row: Mapping[str, Any], summary: PortfolioLoadSummary) -> HeldOutProbe | None:
    """Parse one `held_out_memorization_probe` entry, or drop+count it.

    The probe carries a different shape than a scored case (a compact `change`
    description, not a control/treatment split). A probe missing id / change /
    real_winner is dropped + counted, never half-built.
    """
    if not (_clean(row.get("id")) and _clean(row.get("change")) and _clean(row.get("real_winner"))):
        summary.note(f"probe {row.get('id', '<no id>')!r} missing id/change/real_winner — dropped")
        return None
    return HeldOutProbe(
        id=_clean(row.get("id")),
        change=_clean(row.get("change")),
        real_winner=_clean(row.get("real_winner")),
        why_held_out=_clean(row.get("why_held_out")) or "unspecified",
    )


def parse_portfolio_archive(
    payload: Mapping[str, Any],
) -> tuple[PortfolioArchive, PortfolioLoadSummary]:
    """Parse a decoded PORTFOLIO_CASES.json payload into a typed archive. The
    pure, I/O-free core.

    Takes an already-decoded mapping (e.g. from `json.loads`, or a hand-built
    dict in tests) so the typing / validation / drop accounting is exercised
    without touching the filesystem.

    A payload that carries NEITHER a `scored_cases` list NOR a
    `held_out_memorization_probe` list is a structural ingestion error and raises
    `ValueError` (a renamed/absent top-level key must fail loud, not silently
    yield an empty archive). Per-case drops are counted + surfaced.
    """
    if not isinstance(payload, Mapping):
        raise ValueError(f"portfolio payload must be a JSON object, got {type(payload).__name__}")
    if "scored_cases" not in payload and "held_out_memorization_probe" not in payload:
        raise ValueError(
            "portfolio payload carries neither 'scored_cases' nor "
            "'held_out_memorization_probe'; the file may be malformed or a "
            "different schema. Present keys: " + str(sorted(payload.keys()))
        )

    summary = PortfolioLoadSummary()

    raw_scored = payload.get("scored_cases") or []
    if not isinstance(raw_scored, list):
        raise ValueError("portfolio 'scored_cases' must be a JSON array")
    scored: list[PortfolioCase] = []
    for row in raw_scored:
        summary.scored_read += 1
        if not isinstance(row, Mapping):
            summary.note("scored_cases entry is not an object — dropped")
            summary.scored_dropped_missing_field += 1
            continue
        case = _parse_scored_case(row, summary)
        if case is not None:
            scored.append(case)
            summary.scored_kept += 1

    raw_probe = payload.get("held_out_memorization_probe") or []
    if not isinstance(raw_probe, list):
        raise ValueError("portfolio 'held_out_memorization_probe' must be a JSON array")
    probe: list[HeldOutProbe] = []
    for row in raw_probe:
        summary.probe_read += 1
        if not isinstance(row, Mapping):
            summary.note("held_out probe entry is not an object — dropped")
            continue
        parsed = _parse_probe(row, summary)
        if parsed is not None:
            probe.append(parsed)
            summary.probe_kept += 1

    archive = PortfolioArchive(
        portfolio_id=_clean(payload.get("portfolio_id")) or "portfolio",
        scored_cases=scored,
        held_out_probe=probe,
        human_baseline_anchors=dict(payload.get("human_baseline_anchors") or {}),
        balance_check=dict(payload.get("balance_check") or {}),
        methodology=dict(payload.get("methodology") or {}),
    )
    return archive, summary


def load_portfolio_cases(
    json_path: str | Path = DEFAULT_CASES_PATH,
    *,
    encoding: str = "utf-8",
) -> tuple[PortfolioArchive, PortfolioLoadSummary]:
    """Load a LOCAL PORTFOLIO_CASES.json into a typed `PortfolioArchive`.

    Thin file-I/O wrapper over `parse_portfolio_archive`: reads + JSON-decodes
    `json_path` and delegates all typing / validation / drop accounting to the
    pure core. Returns the archive and a `PortfolioLoadSummary`.

    This never downloads anything — the file must already be present (the curated
    cases are committed in the agent-behavior-spec session dir).
    """
    path = Path(json_path)
    payload = json.loads(path.read_text(encoding=encoding))
    archive, summary = parse_portfolio_archive(payload)
    logger.info(
        "Loaded portfolio %s: %d scored case(s) kept from %d read (dropped: %d "
        "missing-field, %d bad-winner); %d held-out probe(s) kept from %d read",
        path.name,
        summary.scored_kept,
        summary.scored_read,
        summary.scored_dropped_missing_field,
        summary.scored_dropped_bad_winner,
        summary.probe_kept,
        summary.probe_read,
    )
    return archive, summary
