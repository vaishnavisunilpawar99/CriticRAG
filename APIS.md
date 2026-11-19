# CriticRAG AI — API Specification Reference

> Comprehensive reference covering internal Python Class APIs, LLM prompt & response JSON contracts, CLI interface arguments, REST API endpoints, and WebSocket real-time event protocols.

---

## 1. Internal Python Class APIs

The core Python package `agentic_loop_qa` exposes clean class interfaces for agentic reasoning, retrieval, evaluation, and LLM interaction.

### 1. `AgenticLoop` (`agentic_loop_qa.core.loop`)

Main orchestrator class coordinating the multi-agent reasoning loop.

```python
class AgenticLoop:
    def __init__(
        self,
        llm: LLMClient | None = None,
        retriever: Retriever | None = None,
        max_iterations: int | None = None,
    ) -> None: ...

    def answer(self, question: str) -> LoopResult: ...
```

#### `answer(question: str) -> LoopResult`
- **Parameters**: `question` (str) — User query string.
- **Returns**: `LoopResult` dataclass object containing:
  - `question`: str
  - `final_answer`: str
  - `iterations_used`: int
  - `converged`: bool
  - `trace`: list[`IterationTrace`]
  - `passages_used`: list[`Passage`]
- **Exceptions**: Raises `RuntimeError` if LLM client fails in live mode without valid Anthropic key.

---

### 2. `Retriever` Protocol (`agentic_loop_qa.tools.retrieval`)

Interface implemented by `LocalCorpusRetriever` and `WebSearchRetriever`.

```python
class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]: ...
```

#### `retrieve(query: str, top_k: int = 3) -> list[Passage]`
- **Parameters**:
  - `query` (str) — Search query text.
  - `top_k` (int) — Maximum number of passages to return (default 3).
- **Returns**: `list[Passage]` — Sorted list of passage dataclasses containing `title`, `text`, and `score`.

---

### 3. Agent APIs (`agentic_loop_qa.agents`)

#### `GeneratorAgent`
```python
class GeneratorAgent:
    def __init__(self, llm: LLMClient) -> None: ...
    def generate(self, question: str, passages: list[Passage]) -> GeneratorOutput: ...
```

#### `CriticAgent`
```python
class CriticAgent:
    def __init__(self, llm: LLMClient) -> None: ...
    def critique(
        self,
        question: str,
        passages: list[Passage],
        candidate: GeneratorOutput,
        iteration: int,
    ) -> CritiqueOutput: ...
```

#### `RefinerAgent`
```python
class RefinerAgent:
    def __init__(self, llm: LLMClient) -> None: ...
    def refine(
        self,
        question: str,
        passages: list[Passage],
        candidate: GeneratorOutput,
        critique: CritiqueOutput,
    ) -> GeneratorOutput: ...
```

---

### 4. `LLMClient` (`agentic_loop_qa.llm_client`)

Unified client abstraction wrapping Anthropic Claude API and local Mock heuristics.

```python
class LLMClient:
    def __init__(self, mock_mode: Optional[bool] = None) -> None: ...
    def complete(self, system: str, user: str, temperature: float = 0.0) -> str: ...
```

---

## 2. LLM Prompt & Response JSON Contracts

All agents communicate using structured JSON contracts enforced via system prompts.

### 1. Generator Output JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "GeneratorOutput",
  "type": "object",
  "properties": {
    "reasoning": {
      "type": "string",
      "description": "Chain-of-thought step-by-step reasoning referencing evidence passages."
    },
    "answer": {
      "type": "string",
      "description": "Concise candidate answer phrase or sentence."
    }
  },
  "required": ["reasoning", "answer"]
}
```

### 2. Critic Audit JSON Schema
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "CritiqueOutput",
  "type": "object",
  "properties": {
    "verdict": {
      "type": "string",
      "enum": ["approve", "revise", "reject_unanswerable"],
      "description": "Evaluation decision."
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Confidence score in verdict correctness."
    },
    "issues": {
      "type": "array",
      "items": { "type": "string" },
      "description": "List of factual or logical flaws discovered."
    },
    "suggested_fix": {
      "type": ["string", "null"],
      "description": "Actionable guidance for revising the answer, or null if approved."
    }
  },
  "required": ["verdict", "confidence", "issues", "suggested_fix"]
}
```

---

## 3. CLI Subcommand Specifications (`agentic_loop_qa/cli.py`)

CriticRAG AI provides a CLI interface accessible via `python -m agentic_loop_qa.cli`.

### Subcommand: `ask`

Asks a single question and displays the step-by-step trace.

```bash
python -m agentic_loop_qa.cli ask "<question_string>" [--max-iterations N] [--top-k N] [--json]
```

- **Arguments**:
  - `question` (Position 1, required): Query string to answer.
  - `--max-iterations` / `-m` (Optional int): Custom iteration limit.
  - `--top-k` / `-k` (Optional int): Number of retrieved passages.
  - `--json` (Optional flag): Outputs raw `LoopResult.to_dict()` JSON instead of formatted text.

### Subcommand: `eval`

Runs the evaluation harness across a benchmark dataset.

```bash
python -m agentic_loop_qa.cli eval [--out OUTPUT_FILE] [--dataset DATASET_FILE]
```

- **Arguments**:
  - `--out` / `-o` (Optional str, default `report.json`): File path to export json evaluation results.
  - `--dataset` / `-d` (Optional str): Path to alternate JSON dataset file.

---

## 4. REST API Endpoint Specifications

For web service integration, CriticRAG AI defines the following HTTP REST API contract:

### 1. `POST /api/v1/ask`

Executes the multi-agent question answering loop.

#### Request Headers
`Content-Type: application/json`

#### Request Body
```json
{
  "question": "Who designed the Eiffel Tower?",
  "max_iterations": 3,
  "top_k": 3,
  "confidence_threshold": 0.85
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "data": {
    "question": "Who designed the Eiffel Tower?",
    "final_answer": "Alexandre Gustave Eiffel",
    "iterations_used": 1,
    "converged": true,
    "passages_used": [
      {
        "title": "Eiffel Tower",
        "score": 1.412
      }
    ],
    "trace": [
      {
        "iteration": 1,
        "answer": "Alexandre Gustave Eiffel",
        "reasoning": "Passage mentions Alexandre Gustave Eiffel as the engineer.",
        "verdict": "approve",
        "confidence": 0.95,
        "issues": [],
        "suggested_fix": null
      }
    ]
  }
}
```

---

### 2. `POST /api/v1/eval`

Runs benchmark evaluation over the dataset.

#### Request Body
```json
{
  "dataset_path": "agentic_loop_qa/data/sample_dataset.json",
  "export_report": true
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "summary": {
    "total_examples": 5,
    "baseline_em": 0.40,
    "baseline_f1": 0.583,
    "agentic_loop_em": 0.80,
    "agentic_loop_f1": 0.917,
    "change_rate": 0.40,
    "average_iterations": 1.60
  }
}
```

---

### 3. `GET /api/v1/health`

System health & operational mode check.

#### Response `200 OK`
```json
{
  "status": "healthy",
  "mode": "live",
  "model": "claude-3-5-sonnet-20241022",
  "retriever": "LocalCorpusRetriever"
}
```

---

## 5. WebSockets Real-Time Event Protocol

`WS /ws/reasoning-trace`

Provides a bi-directional streaming connection for real-time visualization of agent reasoning steps.

### Event Message Flows

```
Client                                  Server
  │                                       │
  ├─── {"event": "start_question", ──────▶│
  │     "question": "..."}                │
  │                                       │
  │◀── {"event": "passages_retrieved", ───┤
  │     "passages": [...]}                │
  │                                       │
  │◀── {"event": "iteration_start", ──────┤
  │     "iteration": 1}                   │
  │                                       │
  │◀── {"event": "generator_chunk", ──────┤
  │     "delta": "Alexandre..."}          │
  │                                       │
  │◀── {"event": "critic_verdict", ───────┤
  │     "verdict": "revise",              │
  │     "issues": [...]}                  │
  │                                       │
  │◀── {"event": "refine_start"} ─────────┤
  │                                       │
  │◀── {"event": "loop_complete", ────────┤
  │     "final_answer": "..."}            │
```

---

## Related Documentation Files

- [PROJECT_OVERVIEW.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/PROJECT_OVERVIEW.md) — High-level architecture and quickstart guide.
- [BACKEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/BACKEND.md) — Detailed engine architecture and algorithms.
- [FRONTEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/FRONTEND.md) — CLI output format and Web UI visual dashboard spec.
- [SQL_DATABASE.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/SQL_DATABASE.md) — DDL SQL database schemas, ERD, and queries for all system components.
