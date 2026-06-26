"""Fused, multi-turn RAG over experiments + simulations (#31, #32).

Two extensions of the single-shot ``experiment_chat`` RAG:

#31 FUSION — retrieval draws on BOTH evidence sources:
  - real MEASURED A/B experiments (``experiment_archive``), and
  - Sidira-engine PREDICTED simulations (``simulation_archive``).
  When a simulation and an experiment tested the same change (a pairing in the
  seed), the composed answer tells the STORY across both — "we *predicted* X, the
  real A/B *measured* Y, learning Z" — and surfaces the prediction MISSES honestly
  rather than smoothing them (DESIGN.md §8.3). Every cited figure is labeled
  MEASURED or PREDICTED so a prediction is never read as a measurement.

#32 MULTI-TURN — the request carries prior (question, answer) turns. A follow-up
  ("why did that one lose?") is resolved against the prior turn by folding the
  recent thread text into the retrieval query, so the follow-up retrieves the same
  subject the prior turn discussed. Citations are recomputed per turn (never
  replayed stale), so provenance stays grounded in fresh retrieval.

Offline-safe, exactly like ``experiment_chat``: with no LLM provider key the
service degrades to an extractive answer assembled from the retrieved rows, so the
suite and a keyless local demo both produce a grounded, citation-bearing answer.
The LLM path keeps generation pinned to the retrieved fused context.
"""

from __future__ import annotations

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.schemas.experiment_memory import (
    CitationSource,
    ConversationResponse,
    ConversationTurn,
    Experiment,
    ExperimentResult,
    FusedCitation,
)
from sidira_simulator.schemas.simulation_archive import (
    PredictedDirection,
    SimulatedHypothesis,
)
from sidira_simulator.services.experiment_archive import seed_experiments
from sidira_simulator.services.experiment_similarity import (
    ExperimentIndex,
    _tokenize,
)
from sidira_simulator.services.simulation_archive import seed_simulations

# How many prior turns of thread text to fold into the retrieval query. Two is
# enough to resolve a follow-up against the immediately prior subject without
# letting an old turn dominate the vector (#32).
_HISTORY_WINDOW = 2

_FUSION_SYSTEM = (
    "You are the experiment-memory assistant for a product team. You answer ONLY "
    "from the evidence provided below. There are TWO kinds of evidence and you "
    "MUST keep them distinct in every sentence:\n"
    "- MEASURED: a real, already-concluded A/B experiment with a recorded outcome. "
    "Its effect is a real number.\n"
    "- PREDICTED: a Sidira simulation of a hypothesis. Its 'agreement' figure is "
    "UNCALIBRATED simulated-agent agreement, never a measured effect.\n"
    "Rules:\n"
    "- Cite every item by id (exp-#### for measured, sim-#### for predicted) and "
    "label it MEASURED or PREDICTED. Never present a prediction as a measurement.\n"
    "- When a simulation and an experiment tested the SAME change, tell the story: "
    "what Sidira PREDICTED, what the real A/B MEASURED, and the learning — "
    "especially when the prediction MISSED. Do not smooth over a miss.\n"
    "- If the evidence does not contain enough to answer, say so plainly.\n"
    "- Be concise and concrete. Do not refer to yourself as an AI or request tools."
)


# ── retrieval over the simulation archive (mirrors ExperimentIndex) ───────────


class _SimulationIndex:
    """A TF-IDF index over the simulation archive.

    Reuses ``ExperimentIndex`` so there is exactly ONE cosine/TF-IDF
    implementation to keep in sync. ``ExperimentIndex`` indexes on the INPUT side
    only (``_experiment_text`` reads change_description + primary_metric +
    variants) and never touches the outcome fields, so we project each simulation
    into a real ``Experiment`` carrying its real input fields and PLACEHOLDER
    outcome fields. The placeholders are never read: ranking ignores them
    (firewall), and we map every match back to the source ``SimulatedHypothesis``
    by id before any outcome is surfaced. This keeps the two-table firewall intact
    — a prediction never drives its own retrieval — without a second index.
    """

    def __init__(self, simulations: list[SimulatedHypothesis]) -> None:
        self._sims = simulations
        self._by_id = {s.id: s for s in simulations}
        self._index = ExperimentIndex([_sim_as_index_row(s) for s in simulations])

    def rank(self, query: str, top_k: int) -> list[tuple[SimulatedHypothesis, float]]:
        matches = self._index.rank(query, top_k)
        return [(self._by_id[m.experiment.id], m.similarity) for m in matches]


def _sim_as_index_row(sim: SimulatedHypothesis) -> Experiment:
    """Project a simulation into an ``Experiment`` for indexing ONLY.

    Real input fields drive retrieval; the outcome fields are inert placeholders
    (``ExperimentIndex`` reads only the input side — DESIGN/firewall). We never
    read these placeholders back: matches are resolved to the real
    ``SimulatedHypothesis`` by id.
    """
    return Experiment(
        id=sim.id,
        change_description=sim.change_description,
        variants=[],
        primary_metric=sim.primary_metric,
        category=sim.category,
        winner="n/a",  # placeholder — never read (firewall)
        result=ExperimentResult.FLAT,  # placeholder — never read
        effect_size_pct=0.0,  # placeholder — never read
        n=1,  # placeholder — never read
        date=sim.sim_date,
    )


# ── formatting helpers ────────────────────────────────────────────────────────


def _measured_effect_label(e: Experiment) -> str:
    verb = {"win": "WON", "loss": "LOST", "flat": "FLAT"}[e.result.value]
    return (
        f"MEASURED · {verb} {e.effect_size_pct:+.1f}% on {e.primary_metric} · n={e.n:,} · {e.date}"
    )


def _predicted_effect_label(s: SimulatedHypothesis) -> str:
    arrow = {
        PredictedDirection.UP: "UP",
        PredictedDirection.DOWN: "DOWN",
        PredictedDirection.FLAT: "FLAT",
    }[s.predicted_direction]
    # Magnitude is uncalibrated (DESIGN.md §8.3): lead with direction + agreement,
    # show the pp as a predicted, uncalibrated figure.
    return (
        f"PREDICTED · {arrow} (uncalibrated) · agreement {s.confidence_score:.0f}/100 · "
        f"~{s.predicted_metric_lift_pp:+.1f}pp on {s.primary_metric} · {s.sim_date}"
    )


def _experiment_citation(e: Experiment) -> FusedCitation:
    return FusedCitation(
        id=e.id,
        source=CitationSource.MEASURED,
        change_description=e.change_description,
        metric=e.primary_metric,
        effect_label=_measured_effect_label(e),
    )


def _simulation_citation(s: SimulatedHypothesis) -> FusedCitation:
    return FusedCitation(
        id=s.id,
        source=CitationSource.PREDICTED,
        change_description=s.change_description,
        metric=s.primary_metric,
        effect_label=_predicted_effect_label(s),
    )


# ── multi-turn query resolution (#32) ─────────────────────────────────────────


def _resolve_query(message: str, history: list[ConversationTurn]) -> str:
    """Fold recent thread text into the retrieval query so a follow-up resolves
    against the prior turn's subject.

    A bare follow-up ("why did that one lose?") carries almost no retrievable
    vocabulary on its own. We append the tokens from the last ``_HISTORY_WINDOW``
    turns' QUESTIONS + ANSWERS, so the retrieval vector inherits the subject the
    thread was already about. The current message stays first/whole so it still
    dominates when it is itself specific.
    """
    if not history:
        return message
    recent = history[-_HISTORY_WINDOW:]
    carried = " ".join(t.question + " " + t.answer for t in recent)
    # Re-tokenize the carried context through the SAME tokenizer the index uses,
    # so we contribute only content tokens (stopwords/outcome-words dropped) and
    # never let punctuation or filler skew the vector.
    carried_tokens = _tokenize(carried)
    return message + " " + " ".join(carried_tokens)


# ── fused retrieval ───────────────────────────────────────────────────────────


def _story_pairs(
    exp_matches: list[Experiment],
    sim_matches: list[SimulatedHypothesis],
    all_experiments: list[Experiment],
) -> list[tuple[SimulatedHypothesis, Experiment]]:
    """Find predicted↔measured pairs among the retrieved evidence.

    A pair exists when a retrieved simulation names a ``paired_experiment_id`` and
    that experiment is retrievable. We resolve the experiment from the FULL archive
    (not only the retrieved slice) so a strong simulation match can still tell its
    story even if its paired experiment ranked just outside top-k.
    """
    exp_by_id = {e.id: e for e in all_experiments}
    pairs: list[tuple[SimulatedHypothesis, Experiment]] = []
    for s in sim_matches:
        if s.paired_experiment_id and s.paired_experiment_id in exp_by_id:
            pairs.append((s, exp_by_id[s.paired_experiment_id]))
    return pairs


def _pair_story_line(sim: SimulatedHypothesis, exp: Experiment) -> str:
    """One 'predicted X, measured Y, learning Z' sentence for a pair."""
    pred_dir = {
        PredictedDirection.UP: "would lift",
        PredictedDirection.DOWN: "would hurt",
        PredictedDirection.FLAT: "would be flat on",
    }[sim.predicted_direction]
    measured_verb = {"win": "won", "loss": "lost", "flat": "came out flat on"}[exp.result.value]

    # Did the direction call match the measured outcome?
    measured_up = exp.result.value == "win"
    measured_down = exp.result.value == "loss"
    predicted_up = sim.predicted_direction is PredictedDirection.UP
    predicted_down = sim.predicted_direction is PredictedDirection.DOWN
    predicted_flat = sim.predicted_direction is PredictedDirection.FLAT
    measured_flat = exp.result.value == "flat"

    if (
        (predicted_up and measured_up)
        or (predicted_down and measured_down)
        or (predicted_flat and measured_flat)
    ):
        learning = "the simulation called the direction correctly"
    elif predicted_flat or measured_flat:
        learning = "the simulation and the real test disagreed on whether there was any effect"
    else:
        learning = (
            "the simulation got the DIRECTION WRONG — trust the measured result, "
            "treat the prediction as a miss to learn from"
        )

    return (
        f"- {sim.change_description}: Sidira PREDICTED ({sim.id}) it {pred_dir} "
        f"{sim.primary_metric} (uncalibrated, agreement {sim.confidence_score:.0f}/100); "
        f"the real A/B MEASURED ({exp.id}) the change {measured_verb} "
        f"{exp.primary_metric} ({exp.effect_size_pct:+.1f}%, n={exp.n:,}). "
        f"Learning: {learning}."
    )


def _extractive_fused_answer(
    message: str,
    exp_matches: list[Experiment],
    sim_matches: list[SimulatedHypothesis],
    pairs: list[tuple[SimulatedHypothesis, Experiment]],
) -> str:
    """Offline fallback: an honest readout fusing both sources, no LLM."""
    if not exp_matches and not sim_matches:
        return (
            "I couldn't find any past experiments or simulations related to that. "
            "There's nothing recorded to answer from."
        )

    blocks: list[str] = []
    if pairs:
        blocks.append(
            "Where Sidira simulated a change AND the real A/B later ran it, predicted vs measured:"
        )
        # De-dup paired experiments out of the standalone lists below.
        blocks.append("\n".join(_pair_story_line(s, e) for s, e in pairs))

    paired_exp_ids = {e.id for _, e in pairs}
    standalone_exp = [e for e in exp_matches if e.id not in paired_exp_ids]
    if standalone_exp:
        blocks.append("Real MEASURED experiments (recorded outcomes):")
        blocks.append(
            "\n".join(
                f"- {e.id}: {e.change_description} — {_measured_effect_label(e)}"
                for e in standalone_exp
            )
        )

    paired_sim_ids = {s.id for s, _ in pairs}
    standalone_sim = [s for s in sim_matches if s.id not in paired_sim_ids]
    if standalone_sim:
        blocks.append(
            "Sidira PREDICTED (simulated, uncalibrated — direction/rank, not a measured effect):"
        )
        blocks.append(
            "\n".join(
                f"- {s.id}: {s.change_description} — {_predicted_effect_label(s)}"
                for s in standalone_sim
            )
        )

    head = f'Here is what the archive has on "{message.strip()}":'
    return head + "\n" + "\n\n".join(blocks)


def _format_fused_context(
    exp_matches: list[Experiment],
    sim_matches: list[SimulatedHypothesis],
    pairs: list[tuple[SimulatedHypothesis, Experiment]],
) -> str:
    lines: list[str] = []
    for s, e in pairs:
        lines.append(
            f"[PAIR] change: {s.change_description}\n"
            f"  PREDICTED {s.id}: {_predicted_effect_label(s)}\n"
            f"  MEASURED {e.id}: {_measured_effect_label(e)}"
        )
    paired_exp = {e.id for _, e in pairs}
    paired_sim = {s.id for s, _ in pairs}
    for e in exp_matches:
        if e.id in paired_exp:
            continue
        lines.append(f"[MEASURED {e.id}] {e.change_description}\n  {_measured_effect_label(e)}")
    for s in sim_matches:
        if s.id in paired_sim:
            continue
        lines.append(f"[PREDICTED {s.id}] {s.change_description}\n  {_predicted_effect_label(s)}")
    return "\n".join(lines)


def _suggest_follow_ups(
    pairs: list[tuple[SimulatedHypothesis, Experiment]],
    exp_matches: list[Experiment],
    sim_matches: list[SimulatedHypothesis],
) -> list[str]:
    """Suggested next-question chips (#32), grounded in what was retrieved.

    Deterministic and zero-LLM so the chips work offline and never hallucinate a
    subject not in the evidence.
    """
    chips: list[str] = []
    # A pair where the prediction missed is the richest follow-up.
    for s, e in pairs:
        miss = not (
            (s.predicted_direction is PredictedDirection.UP and e.result.value == "win")
            or (s.predicted_direction is PredictedDirection.DOWN and e.result.value == "loss")
            or (s.predicted_direction is PredictedDirection.FLAT and e.result.value == "flat")
        )
        if miss:
            chips.append(f"Why did the prediction miss on {e.id}?")
            break
    if pairs:
        chips.append("Where else did a Sidira prediction match the real result?")
    if exp_matches:
        first_loss = next((e for e in exp_matches if e.result.value == "loss"), None)
        if first_loss is not None:
            chips.append(f"Why did {first_loss.id} lose?")
    if sim_matches and not chips:
        chips.append("What has Sidira only predicted but not measured yet?")
    # Always offer a category-broadening chip last.
    chips.append("What else have we learned in this area?")
    # De-dup, cap at 3 (DESIGN: a small, glanceable chip row).
    seen: set[str] = set()
    out: list[str] = []
    for c in chips:
        if c not in seen:
            seen.add(c)
            out.append(c)
        if len(out) == 3:
            break
    return out


class FusedConversationService:
    """Answers a conversation turn over the FUSED experiment + simulation archives.

    Pass ``chat_client`` to inject a stub (tests / offline). Leave it None and the
    service uses an LLM only when a provider key is configured; otherwise it falls
    back to the extractive fused answer so it never requires network access —
    mirrors ``ExperimentChatService``.
    """

    def __init__(
        self,
        experiments: list[Experiment] | None = None,
        simulations: list[SimulatedHypothesis] | None = None,
        chat_client: ChatClient | None = None,
    ) -> None:
        self._experiments = experiments if experiments is not None else seed_experiments()
        self._simulations = simulations if simulations is not None else seed_simulations()
        self._exp_index = ExperimentIndex(self._experiments)
        self._sim_index = _SimulationIndex(self._simulations)
        self._chat = chat_client
        self._chat_explicit = chat_client is not None

    def _resolve_client(self) -> ChatClient | None:
        if self._chat_explicit:
            return self._chat
        try:
            return get_chat_client()
        except RuntimeError:
            return None

    def answer(
        self,
        message: str,
        history: list[ConversationTurn] | None = None,
        top_k: int = 6,
    ) -> ConversationResponse:
        history = history or []
        query = _resolve_query(message, history)

        exp_matches = [m.experiment for m in self._exp_index.rank(query, top_k)]
        sim_matches = [s for s, _ in self._sim_index.rank(query, top_k)]
        pairs = _story_pairs(exp_matches, sim_matches, self._experiments)

        citations: list[FusedCitation] = []
        # Pairs first (the story), then standalone — preserving retrieval order.
        cited_ids: set[str] = set()
        for s, e in pairs:
            citations.append(_simulation_citation(s))
            citations.append(_experiment_citation(e))
            cited_ids.add(s.id)
            cited_ids.add(e.id)
        for e in exp_matches:
            if e.id not in cited_ids:
                citations.append(_experiment_citation(e))
                cited_ids.add(e.id)
        for s in sim_matches:
            if s.id not in cited_ids:
                citations.append(_simulation_citation(s))
                cited_ids.add(s.id)

        follow_ups = _suggest_follow_ups(pairs, exp_matches, sim_matches)
        client = self._resolve_client()

        if client is None:
            return ConversationResponse(
                answer=_extractive_fused_answer(message, exp_matches, sim_matches, pairs),
                citations=citations,
                follow_ups=follow_ups,
                grounded=True,
                used_llm=False,
            )

        context = _format_fused_context(exp_matches, sim_matches, pairs) or "(no matching evidence)"
        history_block = ""
        if history:
            history_block = (
                "Conversation so far:\n"
                + "\n".join(f"Q: {t.question}\nA: {t.answer}" for t in history[-_HISTORY_WINDOW:])
                + "\n\n"
            )
        messages = [
            {"role": "system", "content": _FUSION_SYSTEM},
            {
                "role": "user",
                "content": (
                    f"{history_block}Evidence (context):\n{context}\n\nQuestion: {message}"
                ),
            },
        ]
        answer = client.chat(messages=messages)
        return ConversationResponse(
            answer=answer.strip(),
            citations=citations,
            follow_ups=follow_ups,
            grounded=True,
            used_llm=True,
        )
