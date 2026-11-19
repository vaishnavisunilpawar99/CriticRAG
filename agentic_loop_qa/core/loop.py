from __future__ import annotations

from ..agents.critic import CriticAgent
from ..agents.generator import GeneratorAgent
from ..agents.refiner import RefinerAgent
from ..config import SETTINGS
from ..llm_client import LLMClient
from ..tools.retrieval import (
    Retriever,
    WebSearchRetriever,
    get_default_retriever,
)
from .types import IterationTrace, LoopResult, Passage, Verdict


class AgenticLoop:
    """Coordinates the Generator -> Critic -> Refiner cycle.

    Termination conditions (checked in order, any one stops the loop):
      1. Critic verdict is APPROVE.
      2. Critic verdict is REJECT_UNANSWERABLE (no point iterating further).
      3. Critic confidence has crossed the configured stop threshold.
      4. `max_iterations` has been used up (budget exhausted -> return the
         best-so-far answer rather than looping forever).
    """

    def __init__(
        self,
        llm: LLMClient | None = None,
        retriever: Retriever | None = None,
        max_iterations: int | None = None,
        retriever_type: str | None = None,
    ):
        self.llm = llm or LLMClient()
        self.retriever = retriever or get_default_retriever(SETTINGS.local_corpus_path, retriever_type=retriever_type)
        self.max_iterations = max_iterations or SETTINGS.max_iterations

        self.generator = GeneratorAgent(self.llm)
        self.critic = CriticAgent(self.llm)
        self.refiner = RefinerAgent(self.llm)

    def _build_retrieval_warning(self, passages: list[Passage]) -> str | None:
        """Explain *why* no evidence was found, instead of failing silently.

        A question outside the local corpus's ~12 topics, with web search
        disabled, will always retrieve zero passages. Surfacing that here
        turns a confusing "unanswerable" result into an actionable message.
        """
        if passages:
            return None

        if isinstance(self.retriever, WebSearchRetriever):
            return (
                "No web search results were found for this question. "
                "Try rephrasing it, or check that TAVILY_API_KEY / network "
                "access is working."
            )

        has_web_key = bool(SETTINGS.tavily_api_key)
        if has_web_key:
            return (
                "No matching passages were found in the local corpus, and "
                "the web retriever also returned nothing for this question."
            )

        return (
            "No matching passages were found. This question is outside the "
            f"{len(self.retriever._docs) if hasattr(self.retriever, '_docs') else 'small'} "
            "built-in local corpus, and web search is disabled. "
            "Set TAVILY_API_KEY in .env (or AGENTICLOOPQA_RETRIEVER_TYPE=web/hybrid) "
            "to let this system answer general questions."
        )

    def answer(self, question: str) -> LoopResult:
        passages = self.retriever.retrieve(question, top_k=SETTINGS.top_k_passages)
        retrieval_warning = self._build_retrieval_warning(passages)

        trace: list[IterationTrace] = []
        current = self.generator.generate(question, passages)

        for iteration in range(1, self.max_iterations + 1):
            critique = self.critic.critique(question, passages, current, iteration)
            trace.append(IterationTrace(iteration=iteration, generator_output=current, critique=critique))

            stop = (
                critique.verdict in (Verdict.APPROVE, Verdict.REJECT_UNANSWERABLE)
                or critique.confidence >= SETTINGS.confidence_stop_threshold
            )
            if stop or iteration == self.max_iterations:
                return LoopResult(
                    question=question,
                    final_answer=current.answer,
                    iterations_used=iteration,
                    converged=critique.verdict == Verdict.APPROVE,
                    trace=trace,
                    passages_used=passages,
                    retrieval_warning=retrieval_warning,
                )

            current = self.refiner.refine(question, passages, current, critique)

        # Unreachable in practice (loop always returns inside the for-loop
        # once max_iterations is hit), kept as a defensive fallback.
        return LoopResult(
            question=question,
            final_answer=current.answer,
            iterations_used=self.max_iterations,
            converged=False,
            trace=trace,
            passages_used=passages,
            retrieval_warning=retrieval_warning,
        )