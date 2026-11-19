from __future__ import annotations


def extract_json(text: str) -> str:
    """Extracts the outermost {...} JSON object from a raw LLM response,
    tolerating stray prose, markdown fences, etc. Raises ValueError if
    no JSON object can be located."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("no JSON object found in LLM response")
    return text[start : end + 1]
