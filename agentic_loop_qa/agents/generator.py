from __future__ import annotations

import json

from ..core.parsing import extract_json
from ..core.types import GeneratorOutput, Passage
from ..llm_client import LLMClient

SYSTEM_PROMPT = """You are the Generator agent in a multi-agent question-answering \
system. You are given a question and a set of retrieved evidence passages. \
Answer using ONLY the evidence provided; if the evidence is insufficient, say so \
explicitly in your reasoning rather than guessing.

Respond with a single JSON object and nothing else, in exactly this shape:
{"reasoning": "<step-by-step reasoning citing the evidence>", "answer": "<concise final answer>"}
"""


def _format_evidence(passages: list[Passage]) -> str:
    if not passages:
        return "(no evidence retrieved)"
    return "\n".join(f"[{i+1}] {p.title}: {p.text}" for i, p in enumerate(passages))


class GeneratorAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate(self, question: str, passages: list[Passage]) -> GeneratorOutput:
        user_prompt = (
            f"Question: {question}\n"
            f"Evidence: {_format_evidence(passages)}\n\n"
            "Return only the JSON object described in the system prompt."
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt, temperature=0.4)
        return _parse_generator_output(raw)


def _parse_generator_output(raw: str) -> GeneratorOutput:
    try:
        data = json.loads(extract_json(raw))
        return GeneratorOutput(
            answer=str(data.get("answer", "")).strip(),
            reasoning=str(data.get("reasoning", "")).strip(),
            raw_text=raw,
        )
    except (json.JSONDecodeError, ValueError):
        # Degrade gracefully: treat the whole response as the answer so a
        # malformed LLM response never crashes the loop.
        return GeneratorOutput(answer=raw.strip(), reasoning="(unparsed response)", raw_text=raw)
