# CRITIC — Trustworthy AI through Iterative Self-Correction
### AgenticLoopQA: Autonomous Multi-Agent Reasoning with Self-Reflection

A small, dependency-light framework for **open-domain question answering**
built around a self-correction loop: a **Generator** proposes an answer, a
**Critic** checks it against retrieved evidence, and a **Refiner** revises
it — repeating until the Critic approves or an iteration budget runs out.

This mirrors the core idea behind CRITIC / Reflexion / Self-Refine style
work: LLMs make fewer factual errors when they're given the chance to
verify and correct their own output against external evidence, rather than
answering once and stopping.

## Architecture

```
                ┌─────────────┐
   question ──▶ │  Retriever  │──▶ evidence passages
                └─────────────┘
                       │
                       ▼
                ┌─────────────┐
        ┌─────▶ │  Generator  │  produces answer + reasoning
        │       └─────────────┘
        │              │
        │              ▼
        │       ┌─────────────┐
        │       │   Critic    │  verdict: approve / revise / unanswerable
        │       └─────────────┘        + confidence + issues + suggested fix
        │              │
        │      revise? │ approve / budget exhausted / confidence high
        │              ▼                        │
        │       ┌─────────────┐                 ▼
        └────── │  Refiner    │           final answer
                └─────────────┘
```

- **Retriever** (`agentic_loop_qa/tools/retrieval.py`) — grounds every
  answer in evidence. Supports 4 pluggable backends:
  - **Vector DB Retriever** (Dense TF-IDF + Cosine Similarity scoring)
  - **Hybrid RAG** (Reciprocal Rank Fusion - RRF)
  - **Live Web Search** (DuckDuckGo API / Tavily API)
  - **Local Corpus** (Sparse keyword-overlap search)
- **Generator** (`agents/generator.py`) — proposes an answer + chain-of-
  thought reasoning, grounded only in the retrieved evidence.
- **Critic** (`agents/critic.py`) — the trust mechanism. Independently
  checks the answer against the *same* evidence for unsupported claims,
  hallucinations, or logical gaps, and returns a structured verdict.
- **Refiner** (`agents/refiner.py`) — revises the answer using the
  Critic's specific feedback, rather than starting over from scratch.
- **AgenticLoop** (`core/loop.py`) — orchestrates the cycle and enforces
  termination conditions (approval, confidence threshold, or iteration
  budget) so the system never loops forever.
- **Web UI & Dashboard** (`agentic_loop_qa/server.py` & `web/`) — interactive
  glassmorphism dashboard visualizing step-by-step reasoning traces, evidence
  inspector, and benchmark evaluation comparison graphs.

## Why a Critic loop instead of one-shot generation?

Single-shot LLM answers can be fluent and wrong. Giving a *second*,
independent pass whose only job is to look for problems — before the
answer is shown to a user — catches a meaningful share of unsupported
claims without needing a bigger or fine-tuned model. The evaluation
harness in this repo (`evaluation/harness.py`) is built specifically to
measure that: it runs the same questions through a single-shot baseline
and through the full loop and reports Exact Match / F1 for both, plus how
often the loop actually changed the answer.

## How to Run the Project

### 1. Installation

```bash
# Clone the repository and enter directory
cd "CriticRAG AI"

# Install Python dependencies
pip install -r requirements.txt
```

### 2. Configure Environment (API Keys & Settings)

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
- **Google Gemini API (Free Tier)**: Set `GEMINI_API_KEY=AIzaSy...` (Default model: `gemini-3.5-flash`).
- **Anthropic Claude API**: Set `ANTHROPIC_API_KEY=sk-ant-...`.
- **Mock Mode**: Leave API keys blank or set `AGENTICLOOPQA_MOCK=1` for 100% offline testing.
- **Retriever Engine**: Set `AGENTICLOOPQA_RETRIEVER_TYPE=vector` (`vector`, `hybrid`, `web`, `local`).

---

### 3. Launching the Interactive Web Dashboard UI

Start the FastAPI server & Web UI dashboard:

```bash
python -m agentic_loop_qa.cli ui --port 8000
```
*(Or run `python -m agentic_loop_qa.server`)*

Open your browser and navigate to **`http://localhost:8000`**.

Features available in the Web UI:
- **Interactive Query Bar**: Submit custom questions or pick sample query presets.
- **Retriever Selector**: Dynamically select `Vector DB (Cosine Sim)`, `Hybrid RAG (RRF)`, `Live Web Search`, or `Sparse Keyword`.
- **Multi-Agent Trace Visualizer**: Inspect Generator reasoning, Critic audit cards with glowing verdict badges (`APPROVE`, `REVISE`, `REJECT`), and confidence meters.
- **Benchmark Evaluation Report**: Run baseline vs. Critic loop benchmark comparisons with Chart.js graphs and metric gain cards.

---

### 4. Running via Command Line Interface (CLI)

```bash
# Ask a single question (outputs full step-by-step reasoning + audit trace)
python -m agentic_loop_qa.cli ask "Who designed the Eiffel Tower?"

# Output machine-readable JSON trace
python -m agentic_loop_qa.cli ask "Who painted the Mona Lisa?" --json

# Run benchmark evaluation harness (Baseline vs. Critic Loop)
python -m agentic_loop_qa.cli eval --out report.json

# Run unit & integration test suite
python -m pytest -q
```

---

## Running in Docker

No local Python setup needed — run everything inside Docker containers.

```bash
# Build the Docker image
docker build -t agentic-loop-qa .

# Launch Interactive Web Dashboard via Docker
docker run --rm -p 8000:8000 --env-file .env agentic-loop-qa ui --host 0.0.0.0 --port 8000

# Ask a single question via Docker (Live Gemini mode)
docker run --rm --env-file .env agentic-loop-qa ask "Who designed the Eiffel Tower?"

# Ask a single question via Docker (Mock mode, no keys needed)
docker run --rm agentic-loop-qa ask "Who designed the Eiffel Tower?"

# Run evaluation harness inside Docker and save report to host
mkdir -p reports
docker run --rm --env-file .env -v $(pwd)/reports:/app/reports agentic-loop-qa eval --out /app/reports/report.json

# Run unit tests inside container
docker run --rm --entrypoint python agentic-loop-qa -m pytest -q
```

### docker compose & Makefile

Shortcuts available via `docker-compose.yml` and `Makefile`:

```bash
# Makefile shortcuts
make build               # Builds Docker image
make ui                  # Launches Web Dashboard on http://localhost:8000
make ask Q="Who painted the Mona Lisa?"   # Runs single query
make eval                # Runs evaluation harness & saves report
make test                # Executes pytest suite inside container
```

---

## Retrieval Engine Backends

| Retriever Type | Class Name | Mechanism & Scoring | Best Use Case |
| :--- | :--- | :--- | :--- |
| **`vector`** (Default) | `VectorCorpusRetriever` | Dense TF-IDF Vector Space Model with **Cosine Similarity** ($\frac{\vec{q} \cdot \vec{d}}{\|\vec{q}\| \|\vec{d}\|}$). | High precision semantic matching over local document corpora. |
| **`hybrid`** | `HybridRetriever` | **Reciprocal Rank Fusion (RRF)** combining vector similarity rank & keyword overlap rank ($\sum \frac{1}{60 + rank}$). | Best overall retrieval quality across diverse queries. |
| **`web`** | `WebSearchRetriever` | Live web search via **DuckDuckGo API** (free) or **Tavily API**. | Real-time open-domain web grounding. |
| **`local`** | `LocalCorpusRetriever` | Sparse bag-of-words token overlap with passage-length normalization. | Fast, lightweight offline keyword search. |

---

## Operating Modes

| Mode  | Trigger | Behavior |
| :--- | :--- | :--- |
| **Mock** | Default when `GEMINI_API_KEY` & `ANTHROPIC_API_KEY` are unset, or `AGENTICLOOPQA_MOCK=1` | Deterministic rule-based stand-in — zero API cost & zero network needed for tests and CI/CD. |
| **Live** | `GEMINI_API_KEY` or `ANTHROPIC_API_KEY` set, `AGENTICLOOPQA_MOCK` unset/0 | Real multi-agent reasoning via Google Gemini API (`gemini-3.5-flash`) or Anthropic API (`claude-sonnet-5`). |

---

## Project Layout

```
CriticRAG AI/
├── agentic_loop_qa/          # Main Python Package
│   ├── agents/               # Multi-Agent Reasoning
│   │   ├── critic.py         # Fact-auditing & verdict generation
│   │   ├── generator.py      # Evidence-grounded QA generation
│   │   └── refiner.py        # Feedback-driven answer revision
│   ├── core/                 # Orchestration Engine
│   │   ├── loop.py           # AgenticLoop orchestrator
│   │   ├── parsing.py        # Structured JSON extraction
│   │   └── types.py          # Dataclasses & Verdict Enums
│   ├── data/                 # Knowledge Corpora & Datasets
│   │   ├── local_corpus.json # Fact corpus
│   │   └── sample_dataset.json # Ground-truth benchmark dataset
│   ├── evaluation/           # Benchmarking Framework
│   │   ├── harness.py        # Baseline vs. Loop comparative evaluator
│   │   └── metrics.py        # Exact Match (EM) & Token F1 metrics
│   ├── tools/                # RAG Retrieval Backends
│   │   └── retrieval.py      # Vector, Hybrid, WebSearch & Local retrievers
│   ├── web/                  # Interactive Web Dashboard UI
│   │   ├── index.html        # Dashboard single-page application
│   │   ├── styles.css        # Cyberpunk glassmorphism design system
│   │   └── app.js            # Client REST fetching & Chart.js rendering
│   ├── cli.py                # Command-line interface (`ask`, `eval`, `ui`)
│   ├── config.py             # Central environment configurations & `.env` loader
│   ├── llm_client.py         # Gemini & Anthropic API client + mock backend
│   └── server.py             # FastAPI REST server & dashboard provider
├── tests/                    # Test Suite
│   ├── conftest.py           # Test isolation & mock environment setup
│   ├── test_harness.py       # Evaluation harness unit tests
│   ├── test_loop_mock.py     # End-to-end loop tests
│   ├── test_metrics.py       # Metric computation unit tests
│   ├── test_retrieval.py     # Vector, Web & Hybrid retriever unit tests
│   └── test_server.py        # FastAPI endpoints & REST API unit tests
├── Dockerfile                # Production container definition (Python 3.11-slim)
├── docker-compose.yml        # Docker service shortcuts
├── Makefile                  # Execution command shortcuts (`make ui`, `make ask`, etc.)
├── requirements.txt          # Dependencies (`anthropic`, `fastapi`, `uvicorn`, `pytest`)
├── .env.example              # Environment configuration template
└── README.md                 # Project documentation
```

## Limitations & honesty about the mock backend

The mock LLM backend uses simple keyword-overlap heuristics purely to
exercise the loop's control flow (generate → critique → revise → stop)
without any API cost or network access. It is **not** a demonstration of
real reasoning quality — for that, set `ANTHROPIC_API_KEY` and run in live
mode. The local retrieval corpus is similarly a small 12-passage demo set,
not a production knowledge base.
