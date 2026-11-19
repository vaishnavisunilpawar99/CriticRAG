import os
from agentic_loop_qa.tools.retrieval import (
    LocalCorpusRetriever,
    VectorCorpusRetriever,
    WebSearchRetriever,
    HybridRetriever,
    get_default_retriever,
)

CORPUS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "agentic_loop_qa", "data", "local_corpus.json"
)


def test_local_retriever_retrieves_relevant_passage():
    retriever = LocalCorpusRetriever(CORPUS_PATH)
    results = retriever.retrieve("Who designed the Eiffel Tower?", top_k=3)
    assert results, "expected at least one passage"
    assert results[0].title == "Eiffel Tower"


def test_vector_retriever_cosine_similarity():
    retriever = VectorCorpusRetriever(CORPUS_PATH)
    results = retriever.retrieve("Who designed the Eiffel Tower?", top_k=3)
    assert results, "expected vector search results"
    assert results[0].title == "Eiffel Tower"
    assert results[0].score > 0.0


def test_hybrid_retriever_rrf():
    vec_ret = VectorCorpusRetriever(CORPUS_PATH)
    kw_ret = LocalCorpusRetriever(CORPUS_PATH)
    hybrid = HybridRetriever(vector_retriever=vec_ret, keyword_retriever=kw_ret)
    results = hybrid.retrieve("boiling point of water", top_k=3)
    assert results
    assert "water" in results[0].title.lower() or "water" in results[0].text.lower()


def test_web_retriever_duckduckgo_fallback():
    retriever = WebSearchRetriever()
    results = retriever.retrieve("Python programming language", top_k=2)
    assert isinstance(results, list)


def test_get_default_retriever_factory():
    ret_vector = get_default_retriever(CORPUS_PATH, retriever_type="vector")
    assert isinstance(ret_vector, VectorCorpusRetriever)

    ret_local = get_default_retriever(CORPUS_PATH, retriever_type="local")
    assert isinstance(ret_local, LocalCorpusRetriever)

    ret_hybrid = get_default_retriever(CORPUS_PATH, retriever_type="hybrid")
    assert isinstance(ret_hybrid, HybridRetriever)
