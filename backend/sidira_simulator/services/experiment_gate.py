"""Submit-time ADVISORY gate over the tenant's PRIOR PREDICTIONS (#38).

The run wizard fires this at submit to surface what Sidira has ALREADY PREDICTED
for a near-identical hypothesis — BEFORE the new run starts. Unlike
``experiment_similarity.search_similar`` (which ranks MEASURED, concluded A/B
experiments), this ranks the tenant's own PREDICTED simulations and never presents
them as measured results.

Honesty (DESIGN.md §8.3): every figure here is uncalibrated simulated-agent
agreement, never a measured winner/effect. The verdict trust-ordering
(already_tested / similar / novel) is REUSED from the measured dedup so the
thresholds stay in one place, but the matches it carries are predicted priors.

Grouping (#38c spread): the same hypothesis is often simulated more than once. We
group near-duplicate prior runs into ONE ``GateMatch`` and carry every run's
agreement so the UI can show the spread ("predicted 3×: agreement 65 / 78 / 82")
instead of listing near-identical priors as separate findings.

This is ADVISORY ONLY: the route returns it, the wizard renders it, and the run is
NEVER blocked on it.
"""

from __future__ import annotations

from sidira_simulator.schemas.experiment_memory import (
    GateMatch,
    SubmitGateResponse,
    Verdict,
)
from sidira_simulator.schemas.simulation_archive import SimulatedHypothesis
from sidira_simulator.services.experiment_similarity import (
    ExperimentIndex,
    _tokenize,
    classify,
)
from sidira_simulator.services.experiment_fusion import _sim_as_index_row

# Two prior runs are the "same hypothesis" when their tokenized change text is
# identical. Crude but deterministic and dependency-free: it collapses re-runs of
# a literally-identical claim (the common multi-run case) without falsely merging
# two genuinely different changes that merely rhyme.
_GROUP_KEY_SEP = "␟"

_GATE_CAVEAT = (
    "These are PRIOR SIDIRA PREDICTIONS, not measured results — the agreement "
    "figure is uncalibrated simulated-agent agreement, never a real effect. A "
    "similar prior rhymes with your hypothesis but is not the same test."
)


def _group_key(sim: SimulatedHypothesis) -> str:
    """A grouping key that collapses re-runs of the literally same hypothesis.

    Uses the content tokens of the change text (stopwords dropped, the SAME
    tokenizer retrieval uses) so trivial whitespace/case differences group, while
    a different change does not.
    """
    return _GROUP_KEY_SEP.join(_tokenize(sim.change_description))


def _direction_str(sim: SimulatedHypothesis) -> str:
    return sim.predicted_direction.value


def _to_gate_match(group: list[tuple[SimulatedHypothesis, float]]) -> GateMatch:
    """Fold one group of prior runs (sim, similarity) into a single GateMatch.

    The representative run is the most-recent one (it carries the id, metric, and
    direction shown); ``agreements`` carries EVERY run's agreement so the UI can
    render the spread. The similarity shown is the group's best (closest prior).
    """
    # Most-recent first for the representative; agreements oldest→newest for a
    # readable spread.
    by_date = sorted(group, key=lambda gs: gs[0].sim_date)
    rep = by_date[-1][0]
    best_sim = max(s for _, s in group)
    return GateMatch(
        id=rep.id,
        change_description=rep.change_description,
        # Metric consistency (#37.4): one hypothesis renders ONE metric — the
        # representative (most-recent) run's, not a mix of "browse" vs "retention"
        # across re-runs.
        primary_metric=rep.primary_metric,
        similarity=round(best_sim, 4),
        predicted_direction=_direction_str(rep),
        agreements=[round(s.confidence_score, 1) for s, _ in by_date],
        run_count=len(group),
        last_sim_date=rep.sim_date,
    )


def _gate_headline(verdict: Verdict, match: GateMatch | None) -> str:
    if verdict is Verdict.ALREADY_TESTED and match is not None:
        spread = " / ".join(f"{a:.0f}" for a in match.agreements)
        times = (
            f"{match.run_count}×: agreement {spread}/100"
            if match.run_count > 1
            else f"agreement {match.agreements[0]:.0f}/100"
        )
        return (
            f"Sidira has predicted effectively this change before ({match.id}, "
            f"predicted {times}). Here's what it predicted and how much it varied — "
            "a prediction, not a measured result."
        )
    if verdict is Verdict.SIMILAR and match is not None:
        return (
            "No identical prior prediction, but Sidira has simulated a related "
            "change. Showing it as an analogical prior — a prediction, not a "
            "measurement."
        )
    return (
        "No prior Sidira prediction matches this hypothesis — running it fresh."
    )


def gate_similar(
    hypothesis: str,
    simulations: list[SimulatedHypothesis],
    top_k: int,
) -> SubmitGateResponse:
    """Run the submit-time advisory gate over the tenant's PRIOR PREDICTIONS (#38).

    Ranks the simulations by TF-IDF cosine similarity to ``hypothesis`` (reusing
    the one ``ExperimentIndex`` implementation via the inert-outcome projection,
    so a prediction never drives its own retrieval — the firewall holds), groups
    re-runs of the same change, classifies the best-match similarity into the
    trust verdict, and returns an honest, source-aware, NON-BLOCKING response.
    """
    if not simulations:
        return SubmitGateResponse(
            hypothesis=hypothesis,
            verdict=Verdict.NOVEL,
            headline=_gate_headline(Verdict.NOVEL, None),
            caveat=None,
            matches=[],
        )

    by_id = {s.id: s for s in simulations}
    index = ExperimentIndex([_sim_as_index_row(s) for s in simulations])
    # Rank generously, then group, so re-runs of one hypothesis don't crowd out
    # other distinct priors from the top_k after grouping.
    ranked = index.rank(hypothesis, max(top_k * 4, top_k))
    scored = [(by_id[m.experiment.id], m.similarity) for m in ranked]

    best_similarity = scored[0][1] if scored else 0.0
    verdict = classify(best_similarity)

    # NOVEL surfaces no priors — a weak match must not masquerade as a prior
    # prediction (mirrors the measured dedup's "no prior to lean on").
    if verdict is Verdict.NOVEL:
        return SubmitGateResponse(
            hypothesis=hypothesis,
            verdict=verdict,
            headline=_gate_headline(verdict, None),
            caveat=None,
            matches=[],
        )

    # Group by the literally-same change, preserving best-similarity order.
    groups: dict[str, list[tuple[SimulatedHypothesis, float]]] = {}
    order: list[str] = []
    for sim, sim_score in scored:
        key = _group_key(sim)
        if key not in groups:
            groups[key] = []
            order.append(key)
        groups[key].append((sim, sim_score))

    matches = [_to_gate_match(groups[key]) for key in order][:top_k]
    best_match = matches[0] if matches else None

    return SubmitGateResponse(
        hypothesis=hypothesis,
        verdict=verdict,
        headline=_gate_headline(verdict, best_match),
        caveat=_GATE_CAVEAT if verdict is Verdict.SIMILAR else None,
        matches=matches,
    )
