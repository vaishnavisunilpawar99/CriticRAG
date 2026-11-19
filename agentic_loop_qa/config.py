"""Central configuration for AgenticLoopQA.

All knobs can be overridden via environment variables so the same code
runs in three modes:

  1. MOCK mode   - no API key needed, deterministic canned responses.
                   Used for tests / CI / offline demos.
  2. LIVE mode   - real calls to the Anthropic API.
  3. Hybrid      - live LLM calls + offline local-corpus retrieval
                   (default when no web-search API key is configured).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


def _load_env_file() -> None:
    env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    if os.path.isfile(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and val and key not in os.environ:
                        os.environ[key] = val


_load_env_file()


def _env_bool(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # --- LLM API Keys & Provider ---
    groq_api_key: str | None = os.environ.get("GROQ_API_KEY")  # FREE: 14,400 req/day
    gemini_api_key: str | None = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    anthropic_api_key: str | None = os.environ.get("ANTHROPIC_API_KEY")
    ollama_base_url: str | None = os.environ.get("OLLAMA_BASE_URL")  # e.g. http://localhost:11434

    # --- LLM settings ---
    model_name: str = os.environ.get(
        "AGENTICLOOPQA_MODEL",
        "gemini-3.6-flash" if (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")) else "claude-sonnet-5"
    )
    max_tokens: int = int(os.environ.get("AGENTICLOOPQA_MAX_TOKENS", "1024"))
    temperature_generate: float = float(os.environ.get("AGENTICLOOPQA_TEMP_GEN", "0.4"))
    temperature_critique: float = float(os.environ.get("AGENTICLOOPQA_TEMP_CRITIC", "0.0"))

    # Force mock mode explicitly, or auto-fallback to it if no API key present.
    mock_mode: bool = _env_bool(
        "AGENTICLOOPQA_MOCK",
        (
            os.environ.get("GROQ_API_KEY") is None
            and os.environ.get("GEMINI_API_KEY") is None
            and os.environ.get("GOOGLE_API_KEY") is None
            and os.environ.get("ANTHROPIC_API_KEY") is None
            and os.environ.get("OLLAMA_BASE_URL") is None
        )
    )

    # --- Self-correction loop ---
    max_iterations: int = int(os.environ.get("AGENTICLOOPQA_MAX_ITERS", "3"))
    confidence_stop_threshold: float = float(
        os.environ.get("AGENTICLOOPQA_STOP_CONF", "0.85")
    )

    # --- Retrieval ---
    retriever_type: str = os.environ.get("AGENTICLOOPQA_RETRIEVER_TYPE", "vector")
    tavily_api_key: str | None = os.environ.get("TAVILY_API_KEY") or os.environ.get("AGENTICLOOPQA_SEARCH_API_KEY")
    top_k_passages: int = int(os.environ.get("AGENTICLOOPQA_TOP_K", "3"))
    local_corpus_path: str = os.environ.get("AGENTICLOOPQA_CORPUS") or os.path.join(
        os.path.dirname(__file__), "data", "local_corpus.json"
    )

    # --- Misc ---
    verbose: bool = _env_bool("AGENTICLOOPQA_VERBOSE", True)


SETTINGS = Settings()
