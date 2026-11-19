from __future__ import annotations

import argparse
import json
import os

from .config import SETTINGS
from .core.loop import AgenticLoop
from .evaluation.harness import run_evaluation


def _print_trace(result) -> None:
    print(f"\nQuestion: {result.question}")
    print(f"Retrieved passages: {[p.title for p in result.passages_used]}")
    for t in result.trace:
        print(f"\n-- Iteration {t.iteration} --")
        print(f"  Answer:    {t.generator_output.answer}")
        print(f"  Reasoning: {t.generator_output.reasoning}")
        print(f"  Critic verdict: {t.critique.verdict.value} (confidence {t.critique.confidence:.2f})")
        if t.critique.issues:
            print(f"  Critic issues: {t.critique.issues}")
        if t.critique.suggested_fix:
            print(f"  Suggested fix: {t.critique.suggested_fix}")
    print(f"\nFinal answer ({'converged' if result.converged else 'budget exhausted'} "
          f"after {result.iterations_used} iteration(s)): {result.final_answer}")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="agentic-loop-qa",
        description="CRITIC / AgenticLoopQA: multi-agent self-correcting open-domain QA.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    ask_p = sub.add_parser("ask", help="Answer a single question with the self-correction loop.")
    ask_p.add_argument("question", type=str)
    ask_p.add_argument("--max-iterations", type=int, default=None)
    ask_p.add_argument("--json", action="store_true", help="Print machine-readable JSON only.")

    eval_p = sub.add_parser("eval", help="Run the baseline-vs-loop evaluation harness.")
    eval_p.add_argument(
        "--dataset",
        type=str,
        default=os.path.join(os.path.dirname(__file__), "data", "sample_dataset.json"),
    )
    eval_p.add_argument("--max-iterations", type=int, default=None)
    eval_p.add_argument("--out", type=str, default=None, help="Optional path to write full JSON report.")

    ui_p = sub.add_parser("ui", help="Launch the interactive Web Dashboard server.")
    ui_p.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    ui_p.add_argument("--host", type=str, default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")

    args = parser.parse_args()

    if SETTINGS.mock_mode:
        print("[AgenticLoopQA] Running in MOCK mode (no GEMINI_API_KEY / ANTHROPIC_API_KEY found "
              "or AGENTICLOOPQA_MOCK=1). Set GEMINI_API_KEY for live LLM calls.\n")
    elif SETTINGS.gemini_api_key:
        print(f"[AgenticLoopQA] Running in LIVE mode via Google Gemini API ({SETTINGS.model_name}).\n")
    elif SETTINGS.anthropic_api_key:
        print(f"[AgenticLoopQA] Running in LIVE mode via Anthropic API ({SETTINGS.model_name}).\n")

    if args.command == "ask":
        loop = AgenticLoop(max_iterations=args.max_iterations)
        result = loop.answer(args.question)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_trace(result)

    elif args.command == "eval":
        report = run_evaluation(args.dataset, max_iterations=args.max_iterations)
        print(report.summary())
        if args.out:
            with open(args.out, "w", encoding="utf-8") as f:
                json.dump(report.to_dict(), f, indent=2)
            print(f"\nFull report written to {args.out}")

    elif args.command == "ui":
        from .server import start_server
        print(f"[AgenticLoopQA] Launching Web Dashboard at http://{args.host}:{args.port}\n")
        start_server(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
