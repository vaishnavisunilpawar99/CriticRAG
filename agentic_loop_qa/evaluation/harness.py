"""Evaluation harness for AgenticLoopQA.

Runs two conditions over a dataset of (question, gold_answers) pairs and
reports Exact Match / F1 for each, so the value of the Critic-driven
self-correction loop can be measured directly against a single-shot
baseline that uses the same Generator and the same retrieved evidence.

  - baseline: retrieve -> generate once, no critique/refinement.
  - loop:     retrieve -> generate -> critique -> refine (AgenticLoop).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from ..agents.generator import GeneratorAgent
from ..config import SETTINGS
from ..core.loop import AgenticLoop
from ..core.types import QAExample
from ..llm_client import LLMClient
from ..tools.retrieval import get_default_retriever
from .metrics import exact_match, f1_score


@dataclass
class ExampleResult:
    id: str
    question: str
    gold_answers: list[str]
    baseline_answer: str
    baseline_em: float
    baseline_f1: float
    loop_answer: str
    loop_em: float
    loop_f1: float
    loop_iterations: int
    loop_converged: bool


@dataclass
class EvalReport:
    n_examples: int
    baseline_em: float
    baseline_f1: float
    loop_em: float
    loop_f1: float
    avg_iterations: float
    correction_rate: float  # fraction of examples where the loop's final
                             # answer differed from the baseline's first-pass answer
    per_example: list[ExampleResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = self.__dict__.copy()
        d["per_example"] = [e.__dict__ for e in self.per_example]
        return d

    def summary(self) -> str:
        lines = [
            f"Examples evaluated : {self.n_examples}",
            "",
            f"{'Condition':<12}{'EM':>8}{'F1':>8}",
            f"{'baseline':<12}{self.baseline_em:>8.3f}{self.baseline_f1:>8.3f}",
            f"{'loop':<12}{self.loop_em:>8.3f}{self.loop_f1:>8.3f}",
            "",
            f"Avg. self-correction iterations used : {self.avg_iterations:.2f}",
            f"Fraction of answers changed by loop   : {self.correction_rate:.2%}",
        ]
        return "\n".join(lines)


def load_dataset(path: str) -> list[QAExample]:
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [QAExample(id=r["id"], question=r["question"], gold_answers=r["gold_answers"]) for r in raw]


def run_evaluation(dataset_path: str, max_iterations: int | None = None) -> EvalReport:
    examples = load_dataset(dataset_path)
    llm = LLMClient()
    retriever = get_default_retriever(SETTINGS.local_corpus_path)

    baseline_generator = GeneratorAgent(llm)
    loop = AgenticLoop(llm=llm, retriever=retriever, max_iterations=max_iterations)

    results: list[ExampleResult] = []
    for idx, ex in enumerate(examples):
        if idx > 0 and not llm.mock_mode:
            import time
            time.sleep(2.0)
        passages = retriever.retrieve(ex.question, top_k=SETTINGS.top_k_passages)
        baseline_out = baseline_generator.generate(ex.question, passages)
        if not llm.mock_mode:
            import time
            time.sleep(2.0)
        loop_result = loop.answer(ex.question)

        results.append(
            ExampleResult(
                id=ex.id,
                question=ex.question,
                gold_answers=ex.gold_answers,
                baseline_answer=baseline_out.answer,
                baseline_em=exact_match(baseline_out.answer, ex.gold_answers),
                baseline_f1=f1_score(baseline_out.answer, ex.gold_answers),
                loop_answer=loop_result.final_answer,
                loop_em=exact_match(loop_result.final_answer, ex.gold_answers),
                loop_f1=f1_score(loop_result.final_answer, ex.gold_answers),
                loop_iterations=loop_result.iterations_used,
                loop_converged=loop_result.converged,
            )
        )

    n = len(results) or 1
    changed = sum(1 for r in results if r.baseline_answer.strip() != r.loop_answer.strip())

    return EvalReport(
        n_examples=len(results),
        baseline_em=sum(r.baseline_em for r in results) / n,
        baseline_f1=sum(r.baseline_f1 for r in results) / n,
        loop_em=sum(r.loop_em for r in results) / n,
        loop_f1=sum(r.loop_f1 for r in results) / n,
        avg_iterations=sum(r.loop_iterations for r in results) / n,
        correction_rate=changed / n,
        per_example=results,
    )
