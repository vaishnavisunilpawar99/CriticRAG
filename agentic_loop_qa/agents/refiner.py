from __future__ import annotations

import json

from ..core.parsing import extract_json
from ..core.types import CritiqueOutput, GeneratorOutput, Passage
from ..llm_client import LLMClient

SYSTEM_PROMPT = """You are the Refiner in a self-correction loop. You receive the \
original question, the evidence, a previous candidate answer, and a Critic's \
feedback explaining what was wrong with it. Produce a revised answer that \
directly addresses every issue the Critic raised, grounded strictly in the \
evidence.

Respond with a single JSON object and nothing else, in exactly this shape:
{"reasoning": "<how you addressed the critic's feedback>", "answer": "<revised concise final answer>"}
"""


def _format_evidence(passages: list[Passage]) -> str:
    if not passages:
        return "(no evidence retrieved)"
    return "\n".join(f"[{i+1}] {p.title}: {p.text}" for i, p in enumerate(passages))


class RefinerAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def refine(
        self,
        question: str,
        passages: list[Passage],
        previous: GeneratorOutput,
        critique: CritiqueOutput,
    ) -> GeneratorOutput:
        user_prompt = (
            f"Question: {question}\n"
            f"Evidence: {_format_evidence(passages)}\n"
            f"Previous answer: {previous.answer}\n"
            f"Previous reasoning: {previous.reasoning}\n"
            f"Critic issues: {'; '.join(critique.issues) or 'none listed'}\n"
            f"Critic suggested fix: {critique.suggested_fix or 'none'}\n\n"
            "Return only the JSON object described in the system prompt."
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt, temperature=0.4)
        return _parse_refiner_output(raw)


def _parse_refiner_output(raw: str) -> GeneratorOutput:
    try:
        data = json.loads(extract_json(raw))
        return GeneratorOutput(
            answer=str(data.get("answer", "")).strip(),
            reasoning=str(data.get("reasoning", "")).strip(),
            raw_text=raw,
        )
    except (json.JSONDecodeError, ValueError):
        return GeneratorOutput(answer=raw.strip(), reasoning="(unparsed response)", raw_text=raw)
