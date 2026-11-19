import os
from unittest.mock import patch
from fastapi.testclient import TestClient

# Force mock mode for unit tests
os.environ["AGENTICLOOPQA_MOCK"] = "1"

from agentic_loop_qa.server import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "mode" in data
    assert "model" in data


def test_ask_endpoint_mock_mode():
    response = client.post(
        "/api/v1/ask",
        json={"question": "Who designed the Eiffel Tower?", "max_iterations": 2},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "data" in body
    assert body["data"]["question"] == "Who designed the Eiffel Tower?"
    assert "final_answer" in body["data"]
    assert "trace" in body["data"]


def test_eval_endpoint():
    response = client.post("/api/v1/eval", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "report" in body
    assert "baseline_em" in body["report"]


def test_serve_dashboard_index():
    response = client.get("/")
    assert response.status_code == 200
    assert "CriticRAG AI" in response.text
