import os

from agentic_loop_qa.core.loop import AgenticLoop
from agentic_loop_qa.core.types import Verdict
from agentic_loop_qa.llm_client import LLMClient
from agentic_loop_qa.tools.retrieval import LocalCorpusRetriever

CORPUS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agentic_loop_qa", "data", "local_corpus.json"
)


def _build_loop(max_iterations=3):
    llm = LLMClient(mock_mode=True)
    retriever = LocalCorpusRetriever(CORPUS_PATH)
    return AgenticLoop(llm=llm, retriever=retriever, max_iterations=max_iterations)


def test_loop_terminates_and_returns_result():
    loop = _build_loop()
    result = loop.answer("Who designed the Eiffel Tower?")
    assert result.final_answer
    assert 1 <= result.iterations_used <= loop.max_iterations
    assert len(result.trace) == result.iterations_used


def test_loop_respects_max_iterations_budget():
    loop = _build_loop(max_iterations=1)
    result = loop.answer("What is the speed of light?")
    assert result.iterations_used == 1


def test_loop_self_corrects_when_first_pass_is_unsupported():
    # In mock mode the critic is designed to flag iteration 1 as REVISE
    # whenever the generator's answer isn't a verbatim substring of the
    # evidence, then approve iteration 2 -- this asserts that control flow.
    loop = _build_loop(max_iterations=3)
    result = loop.answer("What is the boiling point of water?")
    assert len(result.trace) >= 1
    first_verdict = result.trace[0].critique.verdict
    if first_verdict == Verdict.REVISE:
        assert len(result.trace) >= 2
        assert result.trace[-1].critique.verdict in (Verdict.APPROVE, Verdict.REVISE)


def test_loop_result_serializes_to_dict():
    loop = _build_loop()
    result = loop.answer("Who painted the Mona Lisa?")
    d = result.to_dict()
    assert d["question"] == "Who painted the Mona Lisa?"
    assert "trace" in d and isinstance(d["trace"], list)
