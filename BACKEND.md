# CriticRAG AI — Backend Architecture & Core Engine Reference

> Technical reference for the Python backend engine, multi-agent reasoning loop, retrieval framework, LLM client layer, evaluation harness, and environment configuration.

---

## 1. Core Architecture & Types (`agentic_loop_qa/core/`)

The core execution engine models the agentic self-correction loop as a stateful transition process between immutable data types defined in `types.py`.

### Dataclass & Enum Specifications

```python
class Verdict(str, Enum):
    APPROVE = "approve"
    REVISE = "revise"
    REJECT_UNANSWERABLE = "reject_unanswerable"
```

- **`Passage`**: Represents a single chunk of retrieved evidence.
  - `title: str` — Document title or header.
  - `text: str` — Textual content.
  - `score: float` — Relevance score computed by retriever.
- **`GeneratorOutput`**: Result of an initial generation step.
  - `answer: str` — Candidate answer phrase/sentence.
  - `reasoning: str` — Chain-of-thought explanation.
  - `raw_text: str` — Unparsed LLM completion text.
- **`CritiqueOutput`**: Audit verdict produced by the Critic agent.
  - `verdict: Verdict` — Decision (`approve`, `revise`, `reject_unanswerable`).
  - `confidence: float` — Confidence score in range $[0.0, 1.0]$.
  - `issues: list[str]` — Identified flaws (unsupported claims, hallucinations, missing facts).
  - `suggested_fix: Optional[str]` — Actionable feedback for the Refiner agent.
- **`IterationTrace`**: Record of a single iteration step.
  - `iteration: int` — Step index (1-based).
  - `generator_output: GeneratorOutput` — Output generated for this iteration.
  - `critique: CritiqueOutput` — Critic evaluation of the output.
- **`LoopResult`**: Complete execution result object returned by `AgenticLoop.answer()`.
  - `question: str` — User query.
  - `final_answer: str` — Selected output answer string.
  - `iterations_used: int` — Total iterations executed before termination.
  - `converged: bool` — True if approved by Critic; False if terminated by budget or rejection.
  - `trace: list[IterationTrace]` — Full step-by-step reasoning history.
  - `passages_used: list[Passage]` — Retrieved evidence passages.

---

## 2. Orchestration Engine (`agentic_loop_qa/core/loop.py`)

The `AgenticLoop` class coordinates the multi-agent reasoning pipeline.

### Loop Control Flow

```
[Start answer(question)]
         │
         ▼
[Retrieve top_k passages] ──▶ passages: list[Passage]
         │
         ▼
[GeneratorAgent.generate(question, passages)] ──▶ current: GeneratorOutput
         │
         ▼
 ┌───▶ [Iteration 1 .. max_iterations]
 │       │
 │       ▼
 │     [CriticAgent.critique(question, passages, current, iteration)] ──▶ critique: CritiqueOutput
 │       │
 │       ▼
 │     [Append IterationTrace to trace]
 │       │
 │       ▼
 │     [Check Termination Conditions]
 │       ├── 1. critique.verdict in (APPROVE, REJECT_UNANSWERABLE)
 │       ├── 2. critique.confidence >= confidence_stop_threshold
 │       └── 3. iteration == max_iterations
 │       │
 │       ├── YES ──▶ Return LoopResult(converged, final_answer, trace, passages)
 │       │
 │       └── NO
 │            │
 │            ▼
 └─────────── [RefinerAgent.refine(question, passages, current, critique)] ──▶ current: GeneratorOutput
```

### Termination Decision Matrix

| Condition | Evaluated Standard | Resulting `LoopResult.converged` |
| :--- | :--- | :--- |
| **Critic Approval** | `verdict == Verdict.APPROVE` | `True` |
| **Unanswerable Verdict** | `verdict == Verdict.REJECT_UNANSWERABLE` | `False` |
| **High Confidence Threshold** | `confidence >= confidence_stop_threshold` (e.g. $\ge 0.85$) | `True` (if approved) / `False` |
| **Iteration Budget Exhaustion**| `iteration == max_iterations` (default 3) | `False` (returns best available refined answer) |

---

## 3. Agent Subsystem (`agentic_loop_qa/agents/`)

Each agent encapsulates prompt construction, temperature control, and response parsing.

### 1. Generator Agent (`generator.py`)
- **System Prompt**: Instructs model to synthesize an answer based *only* on provided passages.
- **Output Format**: Returns JSON `{ "reasoning": "...", "answer": "..." }`.
- **Parsing Robustness**: Uses `extract_json()` regex fallback if LLM outputs markdown backticks. Fallback produces raw answer if JSON decoding fails.

### 2. Critic Agent (`critic.py`)
- **System Prompt**: Enforces strict fact-auditing against provided passages. Explicitly prohibits outside knowledge.
- **Output Format**:
  ```json
  {
    "verdict": "approve" | "revise" | "reject_unanswerable",
    "confidence": 0.9,
    "issues": ["Issue description..."],
    "suggested_fix": "Fix guidance..."
  }
  ```
- **Fail-Safe Mechanism**: If the critic output cannot be parsed as JSON, it defaults to:
  - `verdict = Verdict.REVISE`
  - `confidence = 0.0`
  - `issues = ["Critic response could not be parsed."]`

### 3. Refiner Agent (`refiner.py`)
- **System Prompt**: Instructs model to revise the candidate answer using the Critic's `issues` and `suggested_fix`.
- **User Prompt**: Includes original Question, Evidence, Previous Answer, Critic Verdict, Critic Issues, and Suggested Fix.
- **Temperature**: Configured at `0.2` to allow slight creative rephrasing while retaining evidence fidelity.

---

## 4. Retrieval Subsystem (`agentic_loop_qa/tools/retrieval.py`)

The retrieval framework adheres to the `Retriever` protocol:

```python
class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 3) -> list[Passage]: ...
```

### Local Corpus Retriever (`LocalCorpusRetriever`)

For zero-dependency offline operation, `LocalCorpusRetriever` implements a bag-of-words term-overlap scoring model.

#### Tokenization & Stopwords
Text is lowercased and stripped of punctuation using regex `[a-z0-9]+`. Common stopwords (`the`, `a`, `is`, `of`, `in`, `and`, etc.) are removed.

#### Relevance Scoring Equation
For a query string $Q$ and passage document $D$:
$$\text{score}(Q, D) = \frac{\sum_{t \in Q \cap D} \min(C_Q(t), C_D(t))}{\left(\sum_{t \in D} C_D(t)\right)^{0.3} + 10^{-6}}$$

Where $C_Q(t)$ and $C_D(t)$ are term frequency counts. The non-linear exponent exponent ($0.3$) normalizes passage length so long documents do not drown out short, precise passages.

### Web Search Retriever (`WebSearchRetriever`)
- Extensible stub class for live search engines (Tavily, Serper, Bing API).
- Instantiated automatically by `get_default_retriever()` when `AGENTICLOOPQA_SEARCH_API_KEY` is present.

---

## 5. Unified LLM Client (`agentic_loop_qa/llm_client.py`)

`LLMClient` abstracts the underlying LLM provider, providing seamless switching between Live Anthropic calls and deterministic Mock heuristics.

```
                  ┌──────────────────────────────┐
                  │       LLMClient.complete     │
                  └──────────────────────────────┘
                                  │
                   Is SETTINGS.mock_mode True?
                                /   \
                        YES    /     \   NO
                              /       \
                             ▼         ▼
             ┌──────────────────┐   ┌──────────────────────────┐
             │  _mock_complete  │   │  _live_complete          │
             └──────────────────┘   │  (Anthropic API Client)  │
                     │              └──────────────────────────┘
           Role Detection via                │
            System Prompt                    ▼
             /    |    \             anthropic.messages.create(
            /     |     \              model=SETTINGS.model_name,
           ▼      ▼      ▼             system=system,
       Generator Critic Refiner        messages=[...])
```

### Mock Heuristic Operations
In mock mode (`mock_mode=True`), `LLMClient` performs rule-based extraction without external API calls:
- **Mock Generator**: Extracts capitalized entity phrases from context overlapping with query tokens.
- **Mock Critic**: Checks if candidate answer string is substring of context. Iteration 1 returns `revise` ($0.4$ confidence) to demonstrate refinement; iteration 2 returns `approve` ($0.75$ confidence).
- **Mock Refiner**: Selects alternate entity candidate from context to simulate answer updating.

---

## 6. Evaluation Framework (`agentic_loop_qa/evaluation/`)

The evaluation framework evaluates question answering quality across ground truth datasets (`sample_dataset.json`).

### Metrics (`metrics.py`)

#### Text Normalization (`_normalize_answer`)
1. Converts text to lowercase.
2. Removes punctuation (`re.sub(r"[^\w\s]", "", text)`).
3. Strips articles (`a`, `an`, `the`).
4. Fixes whitespace formatting.

#### Exact Match (EM) (`compute_em`)
$$\text{EM} = \begin{cases} 1.0 & \text{if } \text{norm}(\text{prediction}) == \text{norm}(\text{gold}) \\ 0.0 & \text{otherwise} \end{cases}$$

#### Token-Level F1 Score (`compute_f1`)
For token sets $P$ (prediction) and $G$ (gold standard):
$$\text{Precision} = \frac{|P \cap G|}{|P|}, \quad \text{Recall} = \frac{|P \cap G|}{|G|}$$
$$\text{F1} = \frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$$

If $|P| = 0$ or $|G| = 0$, $\text{F1} = 1.0$ if $P == G$ else $0.0$.

### Evaluation Harness (`harness.py`)
`EvaluationHarness` runs every QA example through two pathways:
1. **Single-shot Baseline**: `GeneratorAgent.generate()` output evaluated directly against gold answers.
2. **Critic Loop**: `AgenticLoop.answer()` output evaluated against gold answers.

#### Exported Metrics Payload Structure (`report.json`)
```json
{
  "total_examples": 5,
  "baseline": { "em": 0.40, "f1": 0.55 },
  "agentic_loop": { "em": 0.80, "f1": 0.88 },
  "change_rate": 0.60,
  "average_iterations": 1.80,
  "results": [ ... ]
}
```

---

## 7. Configuration & Environment (`config.py`)

System settings are loaded from environment variables using `Settings`:

| Setting | Environment Variable | Default Value | Description |
| :--- | :--- | :--- | :--- |
| `model_name` | `AGENTICLOOPQA_MODEL` | `claude-3-5-sonnet-20241022` | Anthropic model identifier |
| `max_tokens` | `AGENTICLOOPQA_MAX_TOKENS` | `1024` | Max tokens per LLM completion |
| `max_iterations` | `AGENTICLOOPQA_MAX_ITERATIONS` | `3` | Iteration loop budget cap |
| `confidence_stop_threshold` | `AGENTICLOOPQA_CONF_THRESHOLD` | `0.85` | Confidence threshold to halt early |
| `top_k_passages` | `AGENTICLOOPQA_TOP_K` | `3` | Passages retrieved per question |
| `mock_mode` | `AGENTICLOOPQA_MOCK` | `True` (if API key missing) | Toggles mock heuristic backend |
| `local_corpus_path` | `AGENTICLOOPQA_CORPUS_PATH` | `.../data/local_corpus.json` | Path to local JSON corpus |
| `sample_dataset_path` | `AGENTICLOOPQA_DATASET_PATH` | `.../data/sample_dataset.json` | Path to evaluation dataset |

---

## Related Documentation Files

- [PROJECT_OVERVIEW.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/PROJECT_OVERVIEW.md) — High-level architecture, quickstart, and project layout.
- [FRONTEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/FRONTEND.md) — CLI output format and Web UI visual dashboard spec.
- [APIS.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/APIS.md) — Full API reference contracts for Python, LLM JSON, CLI, and REST endpoints.
- [SQL_DATABASE.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/SQL_DATABASE.md) — Relational & Vector SQL schemas for all system components.
