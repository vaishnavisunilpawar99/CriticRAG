# CriticRAG AI — Project Overview & Architecture Guide

> **Trustworthy AI through Iterative Multi-Agent Self-Correction**  
> *Autonomous Question Answering with Evidence-Grounded Reasoning, Independent Critique, and Automated Refinement*

---

## Executive Summary

**CriticRAG AI** (also referenced as `AgenticLoopQA`) is a lightweight, high-reliability framework for open-domain Question Answering (QA). Built on the principles of **CRITIC**, **Reflexion**, and **Self-Refine**, the system addresses a fundamental limitation of standard large language model (LLM) generation: single-shot LLM answers often exhibit subtle factual hallucinations, unsupported logical leaps, or misinterpretations of evidence.

Instead of trusting an LLM's first attempt, CriticRAG AI decouples answer generation from fact-checking. A **Generator** agent drafts an initial answer grounded in retrieved evidence, a separate **Critic** agent independently audits the candidate answer against the evidence, and a **Refiner** agent incorporates precise critique feedback to revise the output. This cycle repeats under the orchestration of an **AgenticLoop** until the Critic approves the response, high confidence is achieved, or an iteration budget is reached.

```
                         ┌────────────────────┐
           question ───▶ │  Retriever Tool    │ ───▶ Evidence Passages
                         └────────────────────┘
                                   │
                                   ▼
                         ┌────────────────────┐
            ┌──────────▶ │  Generator Agent   │ ───▶ Initial Answer + CoT
            │            └────────────────────┘
            │                      │
            │                      ▼
            │            ┌────────────────────┐
            │            │    Critic Agent    │ ───▶ Verdict (approve / revise / reject)
            │            └────────────────────┘      + Confidence + Issues + Suggested Fix
            │                      │
            │  revise?             ▼
            │            ┌────────────────────┐
            └─────────── │   Refiner Agent    │ ◄─── (Stop if approved / confidence high /
                         └────────────────────┘      budget exhausted)
                                                             │
                                                             ▼
                                                       Final Answer
```

---

## Core System Architecture

The project consists of 5 main architectural pillars:

### 1. Retrieval Layer (`agentic_loop_qa/tools/retrieval.py`)
- Grounds all reasoning steps in verifiable document passages.
- Includes a zero-dependency **LocalCorpusRetriever** using bag-of-words token overlap with passage-length normalization for offline demos, tests, and CI.
- Provides a pluggable **WebSearchRetriever** interface for live search engines (Tavily, Serper, Bing).

### 2. Multi-Agent Reasoning Pipeline (`agentic_loop_qa/agents/`)
- **Generator Agent** (`generator.py`): Formulates initial answer candidates and chain-of-thought reasoning strictly using retrieved evidence passages.
- **Critic Agent** (`critic.py`): Acts as the trustworthiness firewall. Audits candidate answers strictly against the evidence passages and emits structured JSON verdicts (`approve`, `revise`, `reject_unanswerable`), confidence scores (0.0 to 1.0), issue descriptions, and suggested fixes.
- **Refiner Agent** (`refiner.py`): Performs targeted revision using the Critic’s specific feedback without losing valid contextual details.

### 3. Orchestration Engine (`agentic_loop_qa/core/loop.py`)
- Coordinates the interaction loop (`Generator` $\rightarrow$ `Critic` $\rightarrow$ `Refiner` $\rightarrow$ `Critic` ...).
- Enforces multi-stage termination guardrails to prevent infinite loops:
  1. **Approval**: Critic returns `approve`.
  2. **Unanswerable**: Critic flags evidence as insufficient (`reject_unanswerable`).
  3. **High Confidence**: Critic confidence exceeds configured threshold (default `0.85`).
  4. **Budget Exceeded**: Iteration count hits `max_iterations` limit (default `3`).

### 4. Evaluation Framework (`agentic_loop_qa/evaluation/`)
- Provides `EvaluationHarness` (`harness.py`) and standard metric utilities (`metrics.py`).
- Compares single-shot baseline generation against the multi-agent self-correction loop across Exact Match (EM) and token-level F1 metrics.
- Measures answer modification rates and convergence metrics.

### 5. Execution Interfaces & Deployment (`agentic_loop_qa/cli.py`, `Dockerfile`)
- CLI for single question execution (`ask`) and benchmark evaluation (`eval`).
- Containerized Docker & Docker Compose setup running as non-root user.

---

## Operational Modes

CriticRAG AI operates in two configurable modes:

| Mode | Trigger Condition | Characteristics & Primary Use Case |
| :--- | :--- | :--- |
| **Mock Mode** | `AGENTICLOOPQA_MOCK=1` or `ANTHROPIC_API_KEY` is empty/unset | Deterministic rule-based LLM & local retrieval stand-in. Enables instant unit testing, offline CI/CD execution, and zero-cost control flow validation. |
| **Live Mode** | `ANTHROPIC_API_KEY` set & `AGENTICLOOPQA_MOCK=0` | Real multi-agent reasoning via Anthropic API (e.g. `claude-3-5-sonnet-20241022`). Performs real chain-of-thought, evidence critique, and dynamic revisions. |

---

## Directory Structure & Component Mapping

```
CriticRAG AI/
├── agentic_loop_qa/          # Main Python Package
│   ├── agents/               # Specialized AI Agents
│   │   ├── __init__.py
│   │   ├── critic.py         # Fact-auditing & structured verdict generation
│   │   ├── generator.py      # Evidence-grounded initial QA generation
│   │   └── refiner.py        # Feedback-driven answer revision
│   ├── core/                 # Core Loop Orchestration & Data Structures
│   │   ├── __init__.py
│   │   ├── loop.py           # AgenticLoop orchestrator
│   │   ├── parsing.py        # JSON extraction from LLM responses
│   │   └── types.py          # Dataclasses & Verdict Enums (LoopResult, Passage, etc.)
│   ├── data/                 # Bundled Datasets & Knowledge Corpora
│   │   ├── local_corpus.json # Demo passages corpus (12 facts)
│   │   └── sample_dataset.json # Ground truth QA evaluation examples
│   ├── evaluation/           # Benchmarking & Metrics
│   │   ├── __init__.py
│   │   ├── harness.py        # Baseline vs. Loop comparative evaluator
│   │   └── metrics.py        # Exact Match (EM) & Token F1 calculations
│   ├── tools/                # Tooling & Retrieval
│   │   ├── __init__.py
│   │   └── retrieval.py      # LocalCorpus & WebSearch retriever implementations
│   ├── cli.py                # Command-line interface subcommands (ask, eval)
│   ├── config.py             # Environment-driven configuration settings
│   └── llm_client.py         # Unified Anthropic API client & mock backend fallback
├── tests/                    # Test Suite
│   ├── test_harness.py       # Evaluation harness unit tests
│   ├── test_loop_mock.py     # End-to-end mock loop execution tests
│   ├── test_metrics.py       # Metric computation unit tests
│   └── test_retrieval.py     # Tokenization & overlap scoring tests
├── Dockerfile                # Production container definition (Python 3.11-slim)
├── docker-compose.yml        # Docker service shortcuts for ask, eval, and test
├── Makefile                  # Build and execution command shortcuts
├── requirements.txt          # Python dependencies (`anthropic`, `pytest`)
├── .env.example              # Sample environment configuration template
└── README.md                 # Project landing documentation
```

---

## Quickstart Guide

### 1. Local Python Installation

```bash
# Clone and enter directory
cd "CriticRAG AI"

# Install dependencies
pip install -r requirements.txt

# (Optional) Export Anthropic key for Live mode; leave unset for Mock mode
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Ask a single question with live trace output
python -m agentic_loop_qa.cli ask "Who designed the Eiffel Tower?"

# Run the evaluation benchmark suite
python -m agentic_loop_qa.cli eval --out report.json

# Run unit and integration test suite
pytest -q
```

### 2. Docker & Compose Execution

```bash
# Build Docker image
docker build -t agentic-loop-qa .

# Run single question via Docker (Mock mode)
docker run --rm agentic-loop-qa ask "Who painted the Mona Lisa?"

# Run live question using environment key
docker run --rm -e ANTHROPIC_API_KEY=sk-ant-... agentic-loop-qa ask "Where is the Eiffel Tower?"

# Convenient Makefile targets
make build
make ask Q="Who discovered penicillin?"
make eval
make test
```

---

## Related Documentation Files

- [BACKEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/BACKEND.md) — Exhaustive Python backend architecture, agent prompts, and evaluation details.
- [FRONTEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/FRONTEND.md) — CLI output format and production React/Next.js Web UI design specification.
- [APIS.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/APIS.md) — Class APIs, LLM prompt/response JSON contracts, CLI commands, REST endpoints, and WebSocket specs.
- [SQL_DATABASE.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/SQL_DATABASE.md) — DDL SQL schemas, ERD diagrams, indices, and queries for all system components.
