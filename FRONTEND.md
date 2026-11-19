# CriticRAG AI — Frontend & Terminal UI Specification

> Comprehensive design specifications for the CLI Terminal User Interface and production Web Dashboard for multi-agent reasoning, real-time trace inspection, evidence source attribution, and evaluation benchmarking.

---

## 1. CLI Terminal Interface Specification

CriticRAG AI provides a rich command-line user interface implemented in `agentic_loop_qa/cli.py`.

### 1. `ask` Command Output Format
When executing `python -m agentic_loop_qa.cli ask "<question>"`, the terminal formats iteration steps into readable trace blocks:

```text
================================================================================
QUESTION: Who designed the Eiffel Tower?
================================================================================

[Retrieved 2 Evidence Passages]
  - [1] Eiffel Tower: The Eiffel Tower was constructed in Paris... (Score: 1.412)
  - [2] Gustave Eiffel: Alexandre Gustave Eiffel was a French civil engineer... (Score: 0.985)

--------------------------------------------------------------------------------
ITERATION 1
--------------------------------------------------------------------------------
[Generator]
  Answer: Alexandre Gustave Eiffel
  Reasoning: Passage [2] explicitly names Alexandre Gustave Eiffel as the French civil engineer who designed the tower.

[Critic Audit]
  Verdict: APPROVE  (Confidence: 0.95 / 1.00)
  Issues: None
  Suggested Fix: None

--------------------------------------------------------------------------------
FINAL RESULT
--------------------------------------------------------------------------------
Final Answer: Alexandre Gustave Eiffel
Iterations Used: 1 / 3
Converged: True
```

### 2. `eval` Command Summary Table
When running evaluation benchmarks (`python -m agentic_loop_qa.cli eval`), the terminal prints formatted metric comparison tables:

```text
================================================================================
EVALUATION BENCHMARK REPORT
================================================================================
Total Dataset Examples : 5
Average Iterations Used: 1.60
Answer Change Rate     : 40.0%

+-------------------+-----------------+-------------------+
| Metric            | Single-Shot     | Critic Loop (Ours)|
+-------------------+-----------------+-------------------+
| Exact Match (EM)  | 40.0%           | 80.0% (+40.0%)    |
| Token F1 Score    | 58.3%           | 91.7% (+33.4%)    |
+-------------------+-----------------+-------------------+

Report exported to: ./report.json
```

---

## 2. Web UI / Dashboard Architecture Design Specification

To provide a state-of-the-art interactive visual experience, the web frontend for CriticRAG AI is specified as a React / Next.js single-page application using modern design principles (glassmorphism, vibrant dark mode, and dynamic state transitions).

### Technology Stack
- **Framework**: Next.js 14 (App Router, TypeScript)
- **Styling**: Vanilla CSS Modules / CSS Custom Properties with Glassmorphism
- **Iconography**: Lucide React (`ShieldCheck`, `AlertTriangle`, `Cpu`, `Layers`, `Search`, `Sparkles`)
- **Charts & Data Visualization**: Recharts / Chart.js for benchmark comparison charts
- **State & Real-Time**: React Context + WebSockets for streaming agent trace tokens

---

## 3. Web UI Component Layout Hierarchy

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 HEADER & SYSTEM STATUS BAR                             │
│ [CriticRAG AI]  [Mode: LIVE/MOCK] [Model: Claude 3.5 Sonnet] [Budget: 3] [Conf: 0.85]   │
├───────────────────────────────────────┬────────────────────────────────────────────────┤
│                                       │                                                │
│  QUERY & CONTROLS PANEL               │  MULTI-AGENT TRACE VISUALIZER                  │
│ ┌───────────────────────────────────┐ │ ┌────────────────────────────────────────────┐ │
│ │ Question Textarea                 │ │ │ Iteration Timeline Header (Steps 1..3)     │ │
│ │ [ Submit Question ]               │ │ ├────────────────────────────────────────────┤ │
│ └───────────────────────────────────┘ │ │ Generator Card                             │ │
│ ┌───────────────────────────────────┐ │ │  - Candidate Answer                        │ │
│ │ Run Evaluation Benchmark          │ │ │  - Chain-of-Thought Reasoning              │ │
│ │ [ Run Eval on Dataset ]           │ │ ├────────────────────────────────────────────┤ │
│ └───────────────────────────────────┘ │ │ Critic Audit Card                          │ │
│                                       │ │  - Verdict Badge (Approve/Revise/Reject)   │ │
│  EVIDENCE SOURCE INSPECTOR            │ │  - Confidence Progress Bar (0% - 100%)     │ │
│ ┌───────────────────────────────────┐ │ │  - Issues Checklist                        │ │
│ │ Passage [1]: Eiffel Tower (1.41)  │ │ │  - Suggested Fix Guidance Box              │ │
│ │ Passage [2]: Gustave Eiffel (0.98)│ │ ├────────────────────────────────────────────┤ │
│ └───────────────────────────────────┘ │ │ Refiner Diff Card (Iteration 2+)           │ │
│                                       │ └────────────────────────────────────────────┘ │
├───────────────────────────────────────┴────────────────────────────────────────────────┤
│                     EVALUATION & BENCHMARK COMPARISON DASHBOARD                        │
│ [EM Metric Card: 40% -> 80%] [F1 Metric Card: 58% -> 91%] [Iteration Hist] [Results Table] │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. UI Component Specifications & Features

### 1. System Header & Configuration Toolbar (`Navbar.tsx`)
- **Status Indicator**: Dynamic glowing LED dot — Green for Live Anthropic Mode, Amber for Mock Mode.
- **Model Selector**: Dropdown to select model (`claude-3-5-sonnet-20241022`, `claude-3-haiku-20240307`).
- **Control Sliders**:
  - `Max Iterations`: Interactive slider $[1 \dots 5]$.
  - `Confidence Stop Threshold`: Range slider $[0.50 \dots 1.00]$.

### 2. Live Multi-Agent Trace Visualizer (`TraceVisualizer.tsx`)
The centerpiece of the UI, displaying step-by-step agent reasoning in real time.

```
Step 1: Generator ──▶ Step 1: Critic Audit ──▶ Step 1: Refiner Revision ──▶ Step 2: Critic Audit (APPROVED)
```

- **Generator Accordion**:
  - Highlights candidate answer in bold teal.
  - Displays chain-of-thought in an expandable markdown card.
- **Critic Audit Card**:
  - **Verdict Badge**:
    - `APPROVE`: Glowing emerald pill (`#10b981`).
    - `REVISE`: Warning amber pill (`#f59e0b`).
    - `REJECT_UNANSWERABLE`: Rose red pill (`#ef4444`).
  - **Confidence Gauge**: Linear animated progress bar colored dynamically by confidence percentage.
  - **Issues List**: Bulleted list of flagged hallucinations, unsupported claims, or logical gaps.
  - **Suggested Fix**: Guidance box detailing actionable changes for the Refiner.
- **Refiner Card**:
  - Uses visual text diffing (green highlight for added text, red strikethrough for replaced text) to illustrate how the answer evolved based on Critic feedback.

### 3. Evidence & Passage Inspector (`EvidencePanel.tsx`)
- Displays all document passages retrieved for the current query.
- Each passage card includes:
  - Passage Title and relevance score badge.
  - Full passage text with term-overlap matches highlighted.
  - Quick copy action button.

### 4. Benchmark Evaluation Dashboard (`EvaluationDashboard.tsx`)
Rendered when running `eval` mode to visually display self-correction improvements:

- **Metric Cards**: Side-by-side comparative cards displaying Exact Match (EM) and F1 Score for Single-shot Baseline vs Agentic Loop.
- **Improvement Delta Badge**: Displays percentage gain (e.g. `+40.0% EM`).
- **Iteration Distribution Histogram**: Bar chart showing how many questions resolved in 1, 2, or 3 iterations.
- **Interactive Results Matrix**: Filterable table showing individual dataset examples, single-shot answer, final loop answer, gold standard answer, EM pass/fail badge, and iterations used.

---

## 5. CSS Tokens & Aesthetics Guideline

To maintain a state-of-the-art UI theme, the web interface adheres to the following CSS tokens:

```css
:root {
  /* Dark Mode Palette */
  --bg-primary: #0a0d14;
  --bg-secondary: #121824;
  --bg-glass: rgba(18, 24, 36, 0.75);
  
  /* Brand Accent Colors */
  --accent-cyan: #06b6d4;
  --accent-indigo: #6366f1;
  --accent-purple: #a855f7;
  
  /* Status Colors */
  --status-success: #10b981;
  --status-warning: #f59e0b;
  --status-danger: #ef4444;
  
  /* Typography */
  --font-sans: 'Inter', system-ui, sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
  
  /* Elevation & Shadows */
  --shadow-glass: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
  --border-glass: 1px solid rgba(255, 255, 255, 0.08);
}
```

---

## Related Documentation Files

- [PROJECT_OVERVIEW.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/PROJECT_OVERVIEW.md) — Architectural overview, modes, and directory setup.
- [BACKEND.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/BACKEND.md) — Backend engine, agents, and evaluation framework.
- [APIS.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/APIS.md) — Python, JSON schema, CLI, REST, and WebSocket API contracts.
- [SQL_DATABASE.md](file:///c:/Users/purva/VIT/5th%20SEM/AI/CriticRAG%20AI/SQL_DATABASE.md) — Database schemas, ERD, and SQL queries for every component.
