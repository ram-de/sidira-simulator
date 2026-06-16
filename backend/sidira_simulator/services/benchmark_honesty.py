"""Stratified honesty table — the Tier-0 reporting layer (ablation-protocol §4).

The blind-eval RUNNER (`services.benchmark_runner.run_blind_eval`) scores a
predictor GLOBALLY: one direction-accuracy, one rank-ρ, one null-integrity
certificate across all cases. That global number hides where the engine works
and where it doesn't. This module is the REPORTING layer that breaks the same
eval down per stratum and presents it HONESTLY.

The one rule it enforces (ablation-protocol §4 line 71, the silent-truncation
rule): **report every cell.** Every stratum the stratifier produces becomes a
row — including ones with poor or negative ρ, and ones with a handful of cases.
A stratum below the certification floor is FLAGGED `underpowered=True` with a
caveat; it is never dropped, never folded away to make the table look better.
"Report every cell — no dropping the ones that didn't help."

Confidence labelling (oec-scoring §6, weak behavioral regime). Pre-calibration
the trustworthy reads are RANK and DIRECTION; the #221 shrinkage layer is still
identity, so absolute magnitude is uncalibrated. Every stratum is therefore
labelled "rank/direction-only" — a bare effect size is never presented as truth.

Void propagation (§4). The whole table inherits the run's null-integrity gate:
if the run's certificate did not PASS (`BenchmarkRunResult.void`), the table is
marked `void` and the per-stratum scores are leakage-suspect — the table is
untrustworthy as a whole, not patched stratum-by-stratum.

Single-sourced math. The per-stratum direction-accuracy, Spearman ρ, and the
always-flat + random-rank baselines reuse the SAME helpers the runner uses
(`benchmark_runner._sign`, `_always_flat_baseline`, `_random_rank_baseline`,
`statistics.spearman_rho`) so a stratum's numbers are computed by the identical
code path as the global ones — no divergent re-derivation.

Stratifiers shipped: by `source` (the dataset label each case carries) and by
predicted/actual EFFECT-MAGNITUDE bucket. These are the only attributes a
`BenchmarkCase` actually carries today (case_id, source, capability, hypothesis,
ground_truth) — see `schemas/benchmark.py`. Richer stratifiers (modality,
domain) are a documented follow-up GATED on the #228 adapter carrying that
metadata on the case; this module does not fabricate fields the cases lack.

Deterministic + pure: no I/O, no live LLM. It operates on a `BenchmarkRunResult`
the runner already produced, consuming `run.case_results` — the EXACT per-case
predictions the run scored and the certificate was computed over. It never
re-runs the predictor, so the table matches the certified run byte-for-byte even
for a stochastic / LLM-backed predictor (a second blind pass could diverge).
"""

from __future__ import annotations

from typing import Callable, Sequence

from sidira_simulator.schemas.scoring import (
    BenchmarkCaseResult,
    BenchmarkRunResult,
    StratifiedHonestyTable,
    StratumResult,
)
from sidira_simulator.services.benchmark_runner import (
    _always_flat_baseline,
    _random_rank_baseline,
    _sign,
)
from sidira_simulator.services.null_integrity import _MIN_EXPERIMENTS
from sidira_simulator.services.statistics import spearman_rho

# A stratifier maps one case RESULT → its stratum key (a string label). EVERY
# case result (scored AND dropped) maps to exactly one stratum; the table reports
# one row per distinct key produced. Operating on the run's `case_results` — not
# on a re-run of the predictor — means the rows match the CERTIFIED predictions
# exactly (no second, possibly-divergent, stochastic pass).
Stratifier = Callable[[BenchmarkCaseResult], str]

# Default effect-magnitude bucket edges (absolute observed lift). The benchmark's
# native metric pre-calibration is the raw signed effect, so buckets are read on
# |observed_lift|; edges are deliberately coarse (the regime is rank/direction,
# not a fine magnitude claim) and documented as the default a caller can override.
_DEFAULT_MAGNITUDE_EDGES: tuple[float, ...] = (0.0, 0.005, 0.02)


def _magnitude_bucket_label(magnitude: float, edges: Sequence[float]) -> str:
    """Half-open bucket label for `magnitude` against ascending `edges`.

    `edges = (0.0, 0.005, 0.02)` gives buckets [0.0,0.005), [0.005,0.02),
    [0.02,∞). A value exactly on an edge falls in the bucket the edge OPENS, so
    bucketing is deterministic and total (every magnitude lands in exactly one).

    When the first edge is ABOVE zero (a custom scheme that omits the low bucket),
    a magnitude below it lands in an explicit `< first-edge` underflow bucket
    rather than being mislabeled into the first half-open bucket — so bucketing
    stays total and correctly labelled for any ascending edges.
    """
    if magnitude < edges[0]:
        return f"|effect| <{edges[0]:g}"
    lo = edges[0]
    for hi in edges[1:]:
        if magnitude < hi:
            return f"|effect| [{lo:g},{hi:g})"
        lo = hi
    return f"|effect| >={lo:g}"


def by_source(case: BenchmarkCaseResult) -> str:
    """Stratify by the case's `source` dataset label (e.g. 'upworthy')."""
    return case.source


# Hillstrom case_ids are structured `hillstrom:<arm_slug>:<metric>[:<segment>]`
# (services.hillstrom_adapter.build_hillstrom_case). The two stratifiers below
# read that structure to report directional accuracy PER ARM (Mens vs Womens
# e-mail) and PER heterogeneity SEGMENT (the endpoint #3 "does the sim know who
# responds most" claim, PLAN §2). They are deliberately defensive: a case_id that
# does not carry the expected component falls into an explicit, REPORTED bucket
# rather than being mislabeled or dropped (the report-every-cell rule, §4).
_HILLSTROM_PREFIX = "hillstrom"
_BY_ARM_UNKNOWN = "arm unknown (no hillstrom arm in case_id)"
_BY_SEGMENT_UNKNOWN = "segment unknown (no heterogeneity stratum in case_id)"


def by_arm(case: BenchmarkCaseResult) -> str:
    """Stratify a Hillstrom case by its randomized treatment ARM.

    Reads the arm slug from the structured Hillstrom case_id
    (`hillstrom:<arm_slug>:<metric>[:<segment>]`) so directional accuracy /
    rank-ρ are reported separately for the Mens-E-Mail and Womens-E-Mail arms —
    the weakest scoring endpoint (PLAN §2 #1/#2), reported per arm so a result
    that holds for one arm but not the other is never averaged away.

    A non-Hillstrom or malformed case_id maps to a dedicated, still-REPORTED
    "arm unknown" bucket (never dropped, never mislabeled). The arm slug is
    surfaced verbatim (e.g. `arm=mens_email`) as the stratum key.
    """
    parts = case.case_id.split(":")
    if len(parts) >= 2 and parts[0] == _HILLSTROM_PREFIX and parts[1]:
        return f"arm={parts[1]}"
    return _BY_ARM_UNKNOWN


def by_segment(case: BenchmarkCaseResult) -> str:
    """Stratify a Hillstrom case by its heterogeneity SEGMENT (endpoint #3).

    Reads the optional 4th component of the structured Hillstrom case_id
    (`hillstrom:<arm_slug>:<metric>:<segment>`) — the pre-registered
    purchase-history stratum (e.g. `mens_history`, `womens_history`) the adapter
    encodes when it enumerates per-segment cases. This is the ONLY scoring
    endpoint that isn't trivially guessable: does the sim predict the men's e-mail
    moves men-history customers MORE than women-history ones?

    A case_id WITHOUT a segment component (an arm-level case, or a non-Hillstrom
    case) maps to a dedicated, still-REPORTED "segment unknown" bucket — so an
    arm-only run is reported honestly (one undifferentiated row) rather than
    fabricating a stratum the cases don't carry. The segment is surfaced verbatim
    (e.g. `segment=mens_history`) as the stratum key.
    """
    parts = case.case_id.split(":")
    if len(parts) >= 4 and parts[0] == _HILLSTROM_PREFIX and parts[3]:
        return f"segment={parts[3]}"
    return _BY_SEGMENT_UNKNOWN


# Label for a stratum where the actual lift is unknown (an unscorable / label-less
# dropped case): it cannot be magnitude-bucketed, but it is STILL reported (§4).
_UNKNOWN_MAGNITUDE_KEY = "|effect| unknown (no scorable label)"


def by_effect_magnitude(
    edges: Sequence[float] = _DEFAULT_MAGNITUDE_EDGES,
) -> Stratifier:
    """Build a stratifier that buckets cases by |observed_lift| (the actual effect).

    Reading the ACTUAL magnitude (not the prediction) keeps the strata fixed for
    a given case set regardless of which predictor is scored, so two predictors
    are compared on the SAME partition — the paired-across-cases discipline (§4),
    one level up. `edges` must be ascending with at least two entries. A case with
    no scorable label (`observed_lift is None`) cannot be bucketed but is still
    reported in a dedicated "unknown" stratum rather than dropped.
    """
    if len(edges) < 2:
        raise ValueError("by_effect_magnitude requires at least two bucket edges")
    if any(b <= a for a, b in zip(edges, edges[1:])):
        raise ValueError(f"by_effect_magnitude edges must be strictly ascending, got {edges!r}")

    def _stratifier(case: BenchmarkCaseResult) -> str:
        if case.observed_lift is None:
            return _UNKNOWN_MAGNITUDE_KEY
        return _magnitude_bucket_label(abs(case.observed_lift), edges)

    return _stratifier


def _regime_label(*, underpowered: bool, n_cases: int) -> str:
    """The confidence/regime label for a stratum (oec-scoring §6).

    Always rank/direction-only pre-calibration (magnitude uncalibrated, #221
    shrinkage is identity); underpowered strata carry the small-N qualifier so a
    reader never mistakes a 2-case ρ for a measurement.
    """
    base = "rank/direction-only (magnitude uncalibrated, pre-#222)"
    if underpowered:
        return f"underpowered (n={n_cases} < {_MIN_EXPERIMENTS}) — {base}"
    return base


def _score_stratum(key: str, members: Sequence[BenchmarkCaseResult]) -> StratumResult:
    """Score ONE stratum's case results into a `StratumResult`.

    Reuses the runner's baseline helpers and `spearman_rho` so the per-stratum
    math is the identical code path as the global run. A member is SCORABLE only
    if it is not dropped AND carries BOTH a prediction and an observed lift; any
    other member (dropped, or the schema-permitted prediction-without-label /
    label-without-prediction shapes) does NOT enter the scored denominator but IS
    counted in `n_dropped`. So a stratum where every member is unscorable is still
    reported as a real row (n_cases=0, n_dropped>0) rather than silently vanishing
    (§4 line 71). A scored stratum below `_MIN_EXPERIMENTS` is flagged
    `underpowered` with a caveat — but still fully scored and returned.
    """
    scored = [
        m
        for m in members
        if not m.dropped and m.prediction is not None and m.observed_lift is not None
    ]
    n_dropped = len(members) - len(scored)
    predictions = [m.prediction for m in scored]
    actuals = [m.observed_lift for m in scored]
    n = len(scored)

    underpowered = n < _MIN_EXPERIMENTS
    caveats: list[str] = []
    if underpowered:
        caveats.append(
            f"underpowered: n={n} below the certification floor of {_MIN_EXPERIMENTS}; "
            "rank-ρ and direction-accuracy are too noisy to certify for this stratum"
        )

    if n == 0:
        # No SCORED case in this stratum — every member was dropped. Still a real,
        # reported row (the whole point of report-every-cell): the drop count and
        # caveat surface a source-/bucket-specific total failure honestly.
        return StratumResult(
            key=key,
            n_cases=0,
            n_dropped=n_dropped,
            underpowered=True,
            regime=_regime_label(underpowered=True, n_cases=0),
            caveat=(
                f"all {n_dropped} case(s) in this stratum were dropped (predictor "
                "failed / no scorable label) — no scored prediction to certify"
            ),
        )

    direction_accuracy = sum(1 for p, a in zip(predictions, actuals) if _sign(p) == _sign(a)) / n
    rank_rho = spearman_rho(predictions, actuals)
    baselines = [_always_flat_baseline(actuals), _random_rank_baseline(actuals)]

    if all(_sign(a) == _sign(actuals[0]) for a in actuals):
        caveats.append(
            "single-sign stratum: all actuals share one direction, so direction-"
            "accuracy is degenerate and rank-ρ may be 0 if predictions are too"
        )

    return StratumResult(
        key=key,
        n_cases=n,
        n_dropped=n_dropped,
        direction_accuracy=direction_accuracy,
        rank_rho=rank_rho,
        baselines=baselines,
        underpowered=underpowered,
        regime=_regime_label(underpowered=underpowered, n_cases=n),
        caveat="; ".join(caveats) if caveats else None,
    )


def _global_caveat(run: BenchmarkRunResult, *, stratifier_name: str) -> str:
    """The table's global honesty frame (carried through from the run)."""
    parts = [
        "Primary endpoint is rank-ρ (ablation-protocol §5).",
        "Magnitude is UNCALIBRATED (read rank/direction, not effect size) until the "
        "#222 shrinkage layer; the #221 calibrator is still identity.",
        f"Total cases scored: {run.n_cases}.",
        f"Cases dropped at the runner level: {run.n_dropped}.",
        f"Stratified by: {stratifier_name}.",
        "Every stratum is reported, including poor/negative-ρ and underpowered "
        "ones — no silent truncation (§4 line 71).",
    ]
    if run.void:
        reason = run.void_reason or "null-integrity certificate did not pass"
        parts.insert(
            0,
            f"VOID: the run's null-integrity certificate did not PASS ({reason}); the "
            "ENTIRE table is leakage-suspect and must not be trusted.",
        )
    return " ".join(parts)


def stratify(
    run: BenchmarkRunResult,
    stratifier: Stratifier,
    *,
    stratifier_name: str,
) -> StratifiedHonestyTable:
    """Build a `StratifiedHonestyTable` from a run's per-case results (§4 reporting).

    `run` is the `BenchmarkRunResult` from `run_blind_eval`. The table is built
    from `run.case_results` — the EXACT per-case predictions the run scored and
    the certificate was computed over — so the rows match the certified run with
    no second, possibly-divergent, predictor pass (important for stochastic /
    LLM-backed predictors). The global null-integrity gate (void propagation) and
    the runner-level drop counters are carried through onto the table.

    Both SCORED and DROPPED cases are partitioned, so a stratum where every case
    was dropped is still reported (n_cases=0, n_dropped>0) — a source-/bucket-
    specific total failure is never hidden behind only the global drop list (§4).
    Every distinct stratifier key becomes a row in `strata`, in first-seen order
    (deterministic for a given case ordering). Poor-ρ and tiny-n strata are
    reported and flagged, never dropped (§4 line 71). If `run.void`, the table is
    marked void as a whole.

    Raises ValueError if the run carries no per-case results (nothing to stratify
    — e.g. a result produced before this field existed, or an empty run).
    """
    if not run.case_results:
        raise ValueError("stratify requires a run with case_results (nothing to stratify)")

    # Partition by key, preserving first-seen key order for deterministic rows.
    groups: dict[str, list[BenchmarkCaseResult]] = {}
    for case in run.case_results:
        groups.setdefault(stratifier(case), []).append(case)

    strata = [_score_stratum(key, members) for key, members in groups.items()]

    return StratifiedHonestyTable(
        stratifier_name=stratifier_name,
        strata=strata,
        void=run.void,
        void_reason=run.void_reason,
        total_n_scored=run.n_cases,
        n_dropped_at_runner=run.n_dropped,
        dropped_case_ids=list(run.dropped_case_ids),
        caveat=_global_caveat(run, stratifier_name=stratifier_name),
    )


def render(table: StratifiedHonestyTable) -> str:
    """Pure human-readable rendering of the table (no printing side effect).

    Returns a fixed-width text table: one line per stratum (key, n, direction-
    accuracy, rank-ρ, the always-flat + random-rank direction floors, and the
    underpowered flag), a VOID banner if the table is void, and the global
    honesty caveat footer. Every stratum row is emitted — the rendering cannot
    hide a cell the table reports.
    """
    lines: list[str] = []
    if table.void:
        lines.append("*** VOID — null-integrity certificate did not pass; do not trust ***")
    lines.append(f"Stratified honesty table — by {table.stratifier_name}")
    header = (
        f"{'stratum':<28} {'n':>4} {'dir_acc':>8} {'rank_rho':>9} "
        f"{'flat':>6} {'rand':>6}  flags"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for s in table.strata:
        by_name = {b.name: b for b in s.baselines}
        flat = by_name.get("always_flat")
        rand = by_name.get("random_rank")
        da = "—" if s.direction_accuracy is None else f"{s.direction_accuracy:.3f}"
        rr = "—" if s.rank_rho is None else f"{s.rank_rho:+.3f}"
        fb = "—" if flat is None else f"{flat.direction_accuracy:.3f}"
        rb = "—" if rand is None else f"{rand.direction_accuracy:.3f}"
        flags = "underpowered" if s.underpowered else ""
        lines.append(f"{s.key:<28} {s.n_cases:>4} {da:>8} {rr:>9} {fb:>6} {rb:>6}  {flags}")
    lines.append("")
    lines.append(f"caveat: {table.caveat}")
    return "\n".join(lines)
