"""Retrieval tools for CriticRAG AI / AgenticLoopQA.

Four retrieval backends implementing the same `retrieve(query, top_k) -> list[Passage]` interface:
  1. VectorCorpusRetriever  : Dense TF-IDF Vector Space Model with Cosine Similarity scoring.
  2. LocalCorpusRetriever   : Fast keyword-overlap search with length normalization.
  3. WebSearchRetriever     : Live web retrieval via DuckDuckGo API or Tavily API.
  4. HybridRetriever        : Reciprocal Rank Fusion (RRF) combining vector & keyword ranks.
"""

from __future__ import annotations

import json
import math
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from typing import Protocol

from ..core.types import Passage


class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]: ...


_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "in", "on", "for",
    "to", "and", "or", "what", "who", "when", "where", "which", "how",
    "does", "do", "did", "that", "this", "with", "by", "as", "at", "it",
}


def _tokenize(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOPWORDS]


class LocalCorpusRetriever:
    """Bag-of-words overlap search over bundled local corpus."""

    def __init__(self, corpus_path: str):
        self.corpus_path = corpus_path
        with open(corpus_path, "r", encoding="utf-8") as f:
            self._docs: list[dict] = json.load(f)

    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]:
        query_terms = Counter(_tokenize(query))
        scored: list[Passage] = []
        for doc in self._docs:
            doc_terms = Counter(_tokenize(doc["text"]) + _tokenize(doc["title"]))
            overlap = sum((query_terms & doc_terms).values())
            if overlap == 0:
                continue
            score = overlap / (len(doc_terms) ** 0.3 + 1e-6)
            scored.append(Passage(title=doc["title"], text=doc["text"], score=round(score, 4)))
        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:top_k]


class VectorCorpusRetriever:
    """Vector Space Model using TF-IDF term weights and Cosine Similarity.

    Computes cosine similarity:
        Sim(q, d) = (q . d) / (||q|| * ||d||)
    """

    def __init__(self, corpus_path: str):
        self.corpus_path = corpus_path
        with open(corpus_path, "r", encoding="utf-8") as f:
            self._docs: list[dict] = json.load(f)

        self._num_docs = len(self._docs)
        self._doc_terms_list: list[Counter] = []
        self._df: Counter = Counter()

        for doc in self._docs:
            terms = Counter(_tokenize(doc["title"] + " " + doc["text"]))
            self._doc_terms_list.append(terms)
            for term in terms.keys():
                self._df[term] += 1

        # Precompute document vector magnitudes
        self._doc_norms: list[float] = []
        self._doc_tfidf: list[dict[str, float]] = []
        for terms in self._doc_terms_list:
            tfidf_vec: dict[str, float] = {}
            sq_sum = 0.0
            for term, count in terms.items():
                tf = 1.0 + math.log(count)
                idf = math.log((self._num_docs + 1.0) / (self._df[term] + 1.0)) + 1.0
                val = tf * idf
                tfidf_vec[term] = val
                sq_sum += val * val
            self._doc_tfidf.append(tfidf_vec)
            self._doc_norms.append(math.sqrt(sq_sum) + 1e-9)

    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]:
        query_terms = Counter(_tokenize(query))
        if not query_terms:
            return []

        # Compute query TF-IDF vector
        q_vec: dict[str, float] = {}
        q_sq_sum = 0.0
        for term, count in query_terms.items():
            tf = 1.0 + math.log(count)
            idf = math.log((self._num_docs + 1.0) / (self._df.get(term, 0) + 1.0)) + 1.0
            val = tf * idf
            q_vec[term] = val
            q_sq_sum += val * val
        q_norm = math.sqrt(q_sq_sum) + 1e-9

        # Cosine similarity scoring
        scored: list[Passage] = []
        for idx, doc in enumerate(self._docs):
            d_vec = self._doc_tfidf[idx]
            d_norm = self._doc_norms[idx]

            dot_product = sum(q_val * d_vec.get(term, 0.0) for term, q_val in q_vec.items())
            if dot_product <= 0:
                continue

            similarity = dot_product / (q_norm * d_norm)
            scored.append(Passage(title=doc["title"], text=doc["text"], score=round(similarity, 4)))

        scored.sort(key=lambda p: p.score, reverse=True)
        return scored[:top_k]


class WebSearchRetriever:
    """Live web search retriever supporting Tavily API or DuckDuckGo Instant Answers."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("TAVILY_API_KEY") or os.environ.get("AGENTICLOOPQA_SEARCH_API_KEY")

    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]:
        if self.api_key:
            try:
                return self._search_tavily(query, top_k)
            except Exception:
                pass
        return self._search_duckduckgo(query, top_k)

    def _search_tavily(self, query: str, top_k: int) -> list[Passage]:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": top_k,
            "search_depth": "basic",
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            results = res.get("results", [])
            passages: list[Passage] = []
            for r in results:
                passages.append(
                    Passage(
                        title=r.get("title", "Web Result"),
                        text=r.get("content", ""),
                        score=round(r.get("score", 0.95), 4),
                    )
                )
            return passages[:top_k]

    def _search_duckduckgo(self, query: str, top_k: int) -> list[Passage]:
        encoded = urllib.parse.quote(query)
        url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_html=1&no_redirect=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        passages: list[Passage] = []
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                res = json.loads(resp.read().decode("utf-8"))
                abstract = res.get("AbstractText")
                heading = res.get("Heading")
                if abstract and heading:
                    passages.append(Passage(title=heading, text=abstract, score=0.95))

                related = res.get("RelatedTopics", [])
                for topic in related:
                    if isinstance(topic, dict) and "Text" in topic:
                        t_text = topic["Text"]
                        t_title = t_text.split(" - ")[0] if " - " in t_text else query
                        passages.append(Passage(title=t_title[:60], text=t_text, score=0.85))
                        if len(passages) >= top_k:
                            break
        except Exception:
            pass

        return passages[:top_k]


class HybridRetriever:
    """Reciprocal Rank Fusion (RRF) combining Dense Vector and Sparse Keyword search.

    Score(d) = sum( 1 / (k + rank_m(d)) )
    """

    def __init__(self, vector_retriever: Retriever, keyword_retriever: Retriever, rrf_k: int = 60):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.rrf_k = rrf_k

    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]:
        vec_results = self.vector_retriever.retrieve(query, top_k=top_k * 2)
        kw_results = self.keyword_retriever.retrieve(query, top_k=top_k * 2)

        rrf_scores: dict[str, float] = {}
        passage_map: dict[str, Passage] = {}

        for rank, p in enumerate(vec_results, start=1):
            key = p.title + "::" + p.text
            passage_map[key] = p
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (self.rrf_k + rank))

        for rank, p in enumerate(kw_results, start=1):
            key = p.title + "::" + p.text
            passage_map[key] = p
            rrf_scores[key] = rrf_scores.get(key, 0.0) + (1.0 / (self.rrf_k + rank))

        combined: list[Passage] = []
        for key, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
            orig_p = passage_map[key]
            combined.append(Passage(title=orig_p.title, text=orig_p.text, score=round(score, 4)))

        return combined[:top_k]


def get_default_retriever(corpus_path: str, retriever_type: str | None = None) -> Retriever:
    """Factory creating appropriate retriever based on configuration or argument."""
    r_type = (retriever_type or os.environ.get("AGENTICLOOPQA_RETRIEVER_TYPE") or "vector").lower().strip()

    if r_type == "web" or os.environ.get("TAVILY_API_KEY") or os.environ.get("AGENTICLOOPQA_SEARCH_API_KEY"):
        return WebSearchRetriever()
    elif r_type == "hybrid":
        v_ret = VectorCorpusRetriever(corpus_path)
        k_ret = LocalCorpusRetriever(corpus_path)
        return HybridRetriever(vector_retriever=v_ret, keyword_retriever=k_ret)
    elif r_type == "local":
        return LocalCorpusRetriever(corpus_path)
    else:
        return VectorCorpusRetriever(corpus_path)

