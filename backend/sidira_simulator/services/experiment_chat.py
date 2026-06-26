"""RAG chat over the experiment archive (#28).

Pure retrieval-augmented generation: a question retrieves the most relevant PAST
experiments (same TF-IDF index as the dedup feature) and the model answers ONLY
from those retrieved rows. There is no prediction — every figure in an answer is
a real recorded outcome the model is told to cite.

Offline-safe: if no LLM provider key is configured the service degrades to an
extractive answer built directly from the retrieved experiments, so the suite
and a keyless local demo both produce a grounded, citation-bearing response. The
LLM path mirrors ``agent_chat.AgentChatService`` — it resolves a client via
``get_chat_client`` and keeps generation pinned to the retrieved context.
"""

from __future__ import annotations

from sidira_simulator.adapters.llm import ChatClient, get_chat_client
from sidira_simulator.schemas.experiment_memory import (
    ChatCitation,
    Experiment,
    ExperimentChatResponse,
    SimilarMatch,
)
from sidira_simulator.services.experiment_archive import seed_experiments
from sidira_simulator.services.experiment_similarity import ExperimentIndex

# Pinned as a system supplement so the model answers strictly from the archive
# and never invents a result. Mirrors the spirit of agent_chat._CHAT_GUARD_PREFIX.
_RAG_SYSTEM = (
    "You are the experiment-memory assistant for a product team. You answer "
    "questions ONLY from the past A/B experiments provided below as context. "
    "Every experiment listed is a REAL, already-concluded test with a recorded "
    "outcome — never a prediction. Rules:\n"
    "- Ground every claim in the provided experiments and cite them by id "
    "(e.g. exp-0008).\n"
    "- Report real effect sizes and sample sizes when relevant.\n"
    "- If the context does not contain enough to answer, say so plainly rather "
    "than guessing.\n"
    "- Surface counter-intuitive results honestly; do not smooth them over.\n"
    "- Be concise and concrete. Do not refer to yourself as an AI or request tools."
)


def _format_context(matches: list[SimilarMatch]) -> str:
    lines: list[str] = []
    for m in matches:
        e = m.experiment
        lines.append(
            f"[{e.id}] ({e.category.value}) {e.change_description}\n"
            f"    primary metric: {e.primary_metric}; variants: {', '.join(e.variants)}\n"
            f"    result: {e.result.value} (winner: {e.winner}); "
            f"effect: {e.effect_size_pct:+.1f}%; n={e.n}; concluded {e.date}"
        )
    return "\n".join(lines)


def _citations(matches: list[SimilarMatch]) -> list[ChatCitation]:
    return [
        ChatCitation(
            id=m.experiment.id,
            change_description=m.experiment.change_description,
            result=m.experiment.result,
            effect_size_pct=m.experiment.effect_size_pct,
            primary_metric=m.experiment.primary_metric,
        )
        for m in matches
    ]


def _extractive_answer(message: str, matches: list[SimilarMatch]) -> str:
    """Offline fallback: a grounded answer assembled from the retrieved rows.

    No LLM — just an honest readout of the most relevant past experiments, so a
    keyless deployment still returns something useful and never fabricated.
    """
    if not matches:
        return (
            "I couldn't find any past experiments in the archive related to that. "
            "There's nothing recorded to answer from."
        )
    head = (
        f'Here is what the archive has that relates to "{message.strip()}", '
        "most relevant first. Every figure below is a real recorded outcome:"
    )
    bullets: list[str] = []
    for m in matches:
        e = m.experiment
        verb = {"win": "won", "loss": "lost", "flat": "came out flat"}[e.result.value]
        bullets.append(
            f"- {e.id}: {e.change_description} — {verb} on {e.primary_metric} "
            f"({e.effect_size_pct:+.1f}%, n={e.n:,}, {e.date})."
        )
    return head + "\n" + "\n".join(bullets)


class ExperimentChatService:
    """Answers questions over the experiment archive.

    Pass ``chat_client`` to inject a stub (tests / offline). Leave it None and
    the service uses an LLM only when a provider key is configured; otherwise it
    falls back to the extractive answer so it never requires network access.
    """

    def __init__(
        self,
        experiments: list[Experiment] | None = None,
        chat_client: ChatClient | None = None,
    ) -> None:
        self._experiments = experiments if experiments is not None else seed_experiments()
        self._index = ExperimentIndex(self._experiments)
        self._chat = chat_client
        self._chat_explicit = chat_client is not None

    def _resolve_client(self) -> ChatClient | None:
        if self._chat_explicit:
            return self._chat
        try:
            return get_chat_client()
        except RuntimeError:
            # No provider key configured — degrade to the extractive fallback.
            return None

    def answer(self, message: str, top_k: int = 6) -> ExperimentChatResponse:
        matches = self._index.rank(message, top_k)
        citations = _citations(matches)
        client = self._resolve_client()

        if client is None:
            return ExperimentChatResponse(
                answer=_extractive_answer(message, matches),
                citations=citations,
                grounded=True,
                used_llm=False,
            )

        context = _format_context(matches) or "(no matching experiments found)"
        messages = [
            {"role": "system", "content": _RAG_SYSTEM},
            {
                "role": "user",
                "content": (f"Past experiments (context):\n{context}\n\n" f"Question: {message}"),
            },
        ]
        answer = client.chat(messages=messages)
        return ExperimentChatResponse(
            answer=answer.strip(),
            citations=citations,
            grounded=True,
            used_llm=True,
        )
