from __future__ import annotations

import json

from ..core.parsing import extract_json
from ..core.types import CritiqueOutput, GeneratorOutput, Passage, Verdict
from ..llm_client import LLMClient

SYSTEM_PROMPT = """You are a rigorous fact-checking Critic agent. You receive a \
question, the evidence passages available, and a candidate answer with its \
reasoning. Your job is to catch errors: unsupported claims, hallucinated facts, \
logical gaps, or answers that contradict the evidence.

Judge strictly against the evidence provided, not your own outside knowledge.

Respond with a single JSON object and nothing else, in exactly this shape:
{
  "verdict": "approve" | "revise" | "reject_unanswerable",
  "confidence": <float 0.0-1.0, your confidence that the verdict is correct>,
  "issues": ["<short description of each problem found>", ...],
  "suggested_fix": "<concrete guidance for how to fix the answer, or null if approved>"
}

Use "reject_unanswerable" only if the evidence genuinely cannot support any answer.
"""


def _format_evidence(passages: list[Passage]) -> str:
    if not passages:
        return "(no evidence retrieved)"
    return "\n".join(f"[{i+1}] {p.title}: {p.text}" for i, p in enumerate(passages))


class CriticAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def critique(
        self,
        question: str,
        passages: list[Passage],
        candidate: GeneratorOutput,
        iteration: int,
    ) -> CritiqueOutput:
        user_prompt = (
            f"Question: {question}\n"
            f"Evidence: {_format_evidence(passages)}\n"
            f"Answer: {candidate.answer}\n"
            f"Reasoning: {candidate.reasoning}\n"
            f"Iteration: {iteration}\n\n"
            "Return only the JSON object described in the system prompt."
        )
        raw = self.llm.complete(SYSTEM_PROMPT, user_prompt, temperature=0.0)
        return _parse_critique_output(raw)


def _parse_critique_output(raw: str) -> CritiqueOutput:
    try:
        data = json.loads(extract_json(raw))
        verdict_str = str(data.get("verdict", "revise")).strip().lower()
        try:
            verdict = Verdict(verdict_str)
        except ValueError:
            verdict = Verdict.REVISE
        confidence = float(data.get("confidence", 0.5))
        confidence = min(max(confidence, 0.0), 1.0)
        issues = data.get("issues") or []
        if isinstance(issues, str):
            issues = [issues]
        return CritiqueOutput(
            verdict=verdict,
            confidence=confidence,
            issues=[str(i) for i in issues],
            suggested_fix=data.get("suggested_fix"),
            raw_text=raw,
        )
    except (json.JSONDecodeError, ValueError):
        # Fail safe: an unparsable critique should never silently approve
        # a bad answer, so default to REVISE with low confidence.
        return CritiqueOutput(
            verdict=Verdict.REVISE,
            confidence=0.0,
            issues=["Critic response could not be parsed."],
            suggested_fix="Re-answer more concisely, citing the evidence directly.",
            raw_text=raw,
        )
