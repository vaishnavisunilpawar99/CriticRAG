"""FastAPI web server for CriticRAG AI / AgenticLoopQA visual dashboard and REST API.

Exposes endpoints:
  - GET /                : Serves the interactive Web Dashboard UI.
  - GET /api/v1/health   : Health check, operational mode (LIVE/MOCK), active LLM model.
  - POST /api/v1/ask     : Run multi-agent QA loop for a single question.
  - POST /api/v1/eval    : Run evaluation benchmark comparison over dataset.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .config import SETTINGS
from .core.loop import AgenticLoop
from .evaluation.harness import run_evaluation
from .llm_client import LLMClient
from .tools.retrieval import get_default_retriever

app = FastAPI(
    title="CriticRAG AI API",
    description="Multi-Agent Question Answering with Evidence-Grounded Reasoning & Critic Audit",
    version="1.0.0",
)

# Enable CORS for local web development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "web"))


class AskRequest(BaseModel):
    question: str = Field(..., description="User question to answer", json_schema_extra={"example": "Who designed the Eiffel Tower?"})
    max_iterations: Optional[int] = Field(None, ge=1, le=10, description="Max iteration budget override")
    top_k: Optional[int] = Field(None, ge=1, le=10, description="Top-k evidence passages to retrieve")
    confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence threshold for early stopping")
    retriever_type: Optional[str] = Field(None, description="Retriever backend: 'vector', 'local', 'web', 'hybrid'")


class EvalRequest(BaseModel):
    dataset_path: Optional[str] = Field(None, description="Path to evaluation dataset JSON")
    max_iterations: Optional[int] = Field(None, ge=1, le=10, description="Max iteration budget override")


@app.get("/api/v1/health")
def get_health() -> Dict[str, Any]:
    if SETTINGS.mock_mode:
        mode = "mock"
        provider = "Mock Backend"
    elif SETTINGS.gemini_api_key:
        mode = "live"
        provider = "Google Gemini API"
    elif SETTINGS.anthropic_api_key:
        mode = "live"
        provider = "Anthropic API"
    else:
        mode = "mock"
        provider = "Mock Fallback"

    return {
        "status": "healthy",
        "mode": mode,
        "provider": provider,
        "model": SETTINGS.model_name,
        "retriever_type": SETTINGS.retriever_type,
        "max_iterations": SETTINGS.max_iterations,
        "confidence_threshold": SETTINGS.confidence_stop_threshold,
        "top_k_passages": SETTINGS.top_k_passages,
    }


@app.post("/api/v1/ask")
def ask_question(req: AskRequest) -> Dict[str, Any]:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question text cannot be empty.")

    try:
        max_iters = req.max_iterations or SETTINGS.max_iterations
        loop = AgenticLoop(max_iterations=max_iters, retriever_type=req.retriever_type)
        result = loop.answer(req.question.strip())
        return {
            "status": "success",
            "data": result.to_dict(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/v1/eval")
def evaluate_dataset(req: EvalRequest) -> Dict[str, Any]:
    try:
        dataset_path = req.dataset_path or os.path.join(
            os.path.dirname(__file__), "data", "sample_dataset.json"
        )
        if not os.path.exists(dataset_path):
            raise HTTPException(status_code=404, detail=f"Dataset file not found: {dataset_path}")

        report = run_evaluation(dataset_path=dataset_path, max_iterations=req.max_iterations)
        return {
            "status": "success",
            "report": report.to_dict(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# Serve static web dashboard assets
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_dashboard():
    index_path = os.path.join(WEB_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "CriticRAG AI API is running. Web UI build index.html not found."}


def start_server(host: str = "127.0.0.1", port: int = 8000) -> None:
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    start_server()
