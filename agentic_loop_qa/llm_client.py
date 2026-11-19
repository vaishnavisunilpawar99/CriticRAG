"""Thin LLM client wrapper.

Supports multiple backends:
  - "gemini": Google Gemini API via GEMINI_API_KEY / GOOGLE_API_KEY.
  - "anthropic": Anthropic Messages API via ANTHROPIC_API_KEY.
  - "mock": deterministic, rule-based stand-ins for the LLM so that the
            self-correction loop, evaluation harness, and tests can run
            with zero network access and zero API cost.

The mock backend is intentionally simple pattern-matching logic — it
exists to exercise the *control flow* of the agentic loop (generate ->
critique -> refine -> stop), not to demonstrate real reasoning quality.
Configure GEMINI_API_KEY or ANTHROPIC_API_KEY to see the real agents in action.
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from typing import Optional

from .config import SETTINGS


class LLMClient:
    def __init__(self, mock_mode: Optional[bool] = None):
        self.mock_mode = SETTINGS.mock_mode if mock_mode is None else mock_mode
        self._backend = "mock"
        self._anthropic_client = None

        if not self.mock_mode:
            # Priority: Groq (free) > Gemini > Anthropic > Ollama > fail
            if SETTINGS.groq_api_key:
                self._backend = "groq"
                if SETTINGS.verbose:
                    print(f"[AgenticLoopQA] Running in LIVE mode via Groq API (FREE tier).")
            elif SETTINGS.gemini_api_key:
                self._backend = "gemini"
            elif SETTINGS.anthropic_api_key:
                self._backend = "anthropic"
                try:
                    import anthropic  # imported lazily so mock mode has no hard dependency
                    self._anthropic_client = anthropic.Anthropic()
                except Exception as exc:  # pragma: no cover
                    raise RuntimeError(
                        "Live mode with Anthropic requires the `anthropic` package and a valid "
                        "ANTHROPIC_API_KEY environment variable. "
                        f"Original error: {exc}"
                    ) from exc
            elif SETTINGS.ollama_base_url:
                self._backend = "ollama"
                if SETTINGS.verbose:
                    print(f"[AgenticLoopQA] Running in LIVE mode via Ollama (local, {SETTINGS.ollama_base_url}).")
            else:
                raise RuntimeError(
                    "Live mode requested, but no API key or local backend is configured.\n"
                    "Options:\n"
                    "  FREE:    Set GROQ_API_KEY in .env (14,400 free req/day — https://console.groq.com)\n"
                    "  LOCAL:   Set OLLAMA_BASE_URL=http://localhost:11434 after installing Ollama\n"
                    "  OFFLINE: Set AGENTICLOOPQA_MOCK=1 for mock mode (no API needed)"
                )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def complete(self, system: str, user: str, temperature: float = 0.0) -> str:
        if self.mock_mode or self._backend == "mock":
            return self._mock_complete(system, user)
        if self._backend == "groq":
            return self._groq_complete(system, user, temperature)
        if self._backend == "gemini":
            return self._gemini_complete(system, user, temperature)
        if self._backend == "ollama":
            return self._ollama_complete(system, user, temperature)
        return self._anthropic_complete(system, user, temperature)

    # ------------------------------------------------------------------
    # Live backends
    # ------------------------------------------------------------------
    def _gemini_complete(self, system: str, user: str, temperature: float) -> str:
        model = SETTINGS.model_name
        if model.startswith("models/"):
            model = model[len("models/"):]

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            f"?key={SETTINGS.gemini_api_key}"
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}],
                }
            ],
            "systemInstruction": {
                "parts": [{"text": system}]
            },
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": SETTINGS.max_tokens,
            },
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )

        max_retries = 8
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=90) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    candidates = result.get("candidates", [])
                    if not candidates:
                        raise RuntimeError(f"Gemini returned empty response: {result}")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    return "".join(part.get("text", "") for part in parts)
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8")
                if exc.code in {429, 500, 502, 503, 504} and attempt < max_retries - 1:
                    import time
                    import re
                    retry_match = re.search(r"retry (?:in|after)\s*(\d+(?:\.\d+)?)s?", error_body, re.IGNORECASE)
                    if retry_match:
                        sleep_time = float(retry_match.group(1)) + 1.5
                    else:
                        sleep_time = min(60.0, 5.0 * (2 ** attempt))
                    
                    if SETTINGS.verbose:
                        print(f"[Gemini API] Rate limited (HTTP {exc.code}). Waiting {sleep_time:.1f}s before retry (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
                raise RuntimeError(f"Gemini API request failed ({exc.code}): {error_body}") from exc
            except Exception as exc:
                if attempt < max_retries - 1:
                    import time
                    sleep_time = 2.0 * (attempt + 1)
                    if SETTINGS.verbose:
                        print(f"[Gemini API] Request error: {exc}. Retrying in {sleep_time:.1f}s...")
                    time.sleep(sleep_time)
                    continue
                raise RuntimeError(f"Gemini API request failed: {exc}") from exc

    def _groq_complete(self, system: str, user: str, temperature: float) -> str:
        """Groq Cloud — free tier, 14,400 requests/day, 30 RPM."""
        model = SETTINGS.model_name if SETTINGS.model_name not in (
            "gemini-3.6-flash", "gemini-3.5-flash", "claude-sonnet-5",
            "llama-3.3-70b-versatile", "llama-3.1-8b-instant",
        ) else "openai/gpt-oss-120b"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": SETTINGS.max_tokens,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SETTINGS.groq_api_key}",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            },
        )
        max_retries = 5
        for attempt in range(max_retries):
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    return result["choices"][0]["message"]["content"]
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8")
                if exc.code in {429, 500, 503} and attempt < max_retries - 1:
                    import time
                    sleep_time = min(30.0, 3.0 * (2 ** attempt))
                    if SETTINGS.verbose:
                        print(f"[Groq API] Rate limited (HTTP {exc.code}). Waiting {sleep_time:.1f}s (attempt {attempt + 1}/{max_retries})...")
                    time.sleep(sleep_time)
                    continue
                raise RuntimeError(f"Groq API request failed ({exc.code}): {error_body}") from exc
            except Exception as exc:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2.0 * (attempt + 1))
                    continue
                raise RuntimeError(f"Groq API request failed: {exc}") from exc

    def _ollama_complete(self, system: str, user: str, temperature: float) -> str:
        """Local Ollama server — fully offline, unlimited, free."""
        base_url = (SETTINGS.ollama_base_url or "http://localhost:11434").rstrip("/")
        model = SETTINGS.model_name if SETTINGS.model_name not in (
            "gemini-3.6-flash", "gemini-3.5-flash", "claude-sonnet-5"
        ) else "llama3.2"

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": {"temperature": temperature, "num_predict": SETTINGS.max_tokens},
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result["message"]["content"]
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot connect to Ollama at {base_url}.\n"
                "Make sure Ollama is running: `ollama serve`\n"
                f"Error: {exc}"
            ) from exc
        except Exception as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

    def _anthropic_complete(self, system: str, user: str, temperature: float) -> str:
        response = self._anthropic_client.messages.create(
            model=SETTINGS.model_name,
            max_tokens=SETTINGS.max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )

    # ------------------------------------------------------------------
    # Mock backend
    # ------------------------------------------------------------------
    def _mock_complete(self, system: str, user: str) -> str:
        role = "critic" if "You are a rigorous fact-checking Critic" in system else (
            "refiner" if "You are the Refiner" in system else "generator"
        )
        if role == "generator":
            return self._mock_generate(user)
        if role == "critic":
            return self._mock_critique(user)
        return self._mock_refine(user)

    def _mock_generate(self, user: str) -> str:
        question = _extract_field(user, "Question")
        context = _extract_field(user, "Evidence")
        # Very naive heuristic "answering": look for a capitalized phrase
        # near a keyword overlap between question and context.
        guess = _naive_extractive_guess(question, context)
        return json.dumps(
            {
                "reasoning": (
                    f"The evidence mentions '{guess}', which overlaps with the "
                    f"entities asked about in the question, so I will answer with it."
                ),
                "answer": guess,
            }
        )

    def _mock_critique(self, user: str) -> str:
        answer = _extract_field(user, "Answer")
        context = _extract_field(user, "Evidence")
        iteration = _extract_field(user, "Iteration")
        try:
            iter_n = int(iteration)
        except (TypeError, ValueError):
            iter_n = 1

        supported = bool(answer) and answer.lower() in context.lower()
        if supported:
            return json.dumps(
                {
                    "verdict": "approve",
                    "confidence": 0.9,
                    "issues": [],
                    "suggested_fix": None,
                }
            )
        # Simulate the critic catching an unsupported claim on iteration 1,
        # then approving after one refinement — this is what demonstrates
        # the *self-correction* behavior in mock mode.
        if iter_n < 2:
            return json.dumps(
                {
                    "verdict": "revise",
                    "confidence": 0.4,
                    "issues": [
                        "The answer is not directly supported by the retrieved evidence."
                    ],
                    "suggested_fix": "Re-read the evidence and quote the exact entity it names.",
                }
            )
        return json.dumps(
            {
                "verdict": "approve",
                "confidence": 0.75,
                "issues": [],
                "suggested_fix": None,
            }
        )

    def _mock_refine(self, user: str) -> str:
        context = _extract_field(user, "Evidence")
        question = _extract_field(user, "Question")
        guess = _naive_extractive_guess(question, context, prefer_second_pass=True)
        return json.dumps(
            {
                "reasoning": "Incorporating the critic's feedback, re-grounding the answer in the evidence text.",
                "answer": guess,
            }
        )


# ----------------------------------------------------------------------
# Small text-processing helpers used only by the mock backend
# ----------------------------------------------------------------------
def _extract_field(text: str, field: str) -> str:
    match = re.search(rf"{field}:\s*(.+)", text)
    return match.group(1).strip() if match else ""


def _naive_extractive_guess(question: str, context: str, prefer_second_pass: bool = False) -> str:
    if not context:
        return "unknown"
    candidates = re.findall(r"\b([A-Z][a-zA-Z0-9.'-]*(?:\s+[A-Z][a-zA-Z0-9.'-]*)*)\b", context)
    candidates = [c for c in candidates if c.lower() not in {"the", "a", "an"}]
    if not candidates:
        return context.split(".")[0][:60]
    if prefer_second_pass and len(candidates) > 1:
        return candidates[1]
    return candidates[0]