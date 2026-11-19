from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Verdict(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT_UNANSWERABLE = "reject_unanswerable"


@dataclass
class Passage:
    title: str
    text: str
    score: float = 0.0


@dataclass
class GeneratorOutput:
    answer: str
    reasoning: str
    raw_text: str = ""


@dataclass
class CritiqueOutput:
    verdict: Verdict
    confidence: float
    issues: list[str] = field(default_factory=list)
    suggested_fix: Optional[str] = None
    raw_text: str = ""


@dataclass
class IterationTrace:
    iteration: int
    generator_output: GeneratorOutput
    critique: CritiqueOutput


@dataclass
class LoopResult:
    question: str
    final_answer: str
    iterations_used: int
    converged: bool
    trace: list[IterationTrace] = field(default_factory=list)
    passages_used: list[Passage] = field(default_factory=list)
    retrieval_warning: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "final_answer": self.final_answer,
            "iterations_used": self.iterations_used,
            "converged": self.converged,
            "retrieval_warning": self.retrieval_warning,
            "trace": [
                {
                    "iteration": t.iteration,
                    "answer": t.generator_output.answer,
                    "reasoning": t.generator_output.reasoning,
                    "verdict": t.critique.verdict.value,
                    "confidence": t.critique.confidence,
                    "issues": t.critique.issues,
                    "suggested_fix": t.critique.suggested_fix,
                }
                for t in self.trace
            ],
            "passages_used": [
                {"title": p.title, "score": p.score} for p in self.passages_used
            ],
        }


@dataclass
class QAExample:
    question: str
    gold_answers: list[str]
    id: str = ""