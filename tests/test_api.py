"""
Integration tests for Relay FastAPI Server Endpoints (Phase 5).
"""

import pytest
from fastapi.testclient import TestClient
from relay.api.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "relay-ai"


def test_get_benchmark_tasks():
    response = client.get("/api/v1/benchmark/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    assert len(tasks) >= 6


def test_create_and_load_checkpoint():
    payload = {
        "session_state": {
            "session_id": "sess-api-test",
            "agent_type": "openhands",
            "task_goal": "Refactor router in FastAPI",
            "tokens_consumed": 95000,
            "token_limit": 128000,
            "active_files": ["api/main.py"]
        },
        "why_not_store": [
            {
                "approach_id": "wn-api-1",
                "attempted_idea": "Monolithic router file",
                "rationale_rejected": "Violates modular code organization"
            }
        ],
        "decision_log": [
            {
                "decision_id": "dec-api-1",
                "choice_made": "Modular APIRouter sub-modules",
                "justification": "Improves readability and testing"
            }
        ]
    }

    # Create checkpoint
    resp_create = client.post("/api/v1/checkpoint", json=payload)
    assert resp_create.status_code == 200
    chk_data = resp_create.json()
    assert "checkpoint_id" in chk_data
    checkpoint_id = chk_data["checkpoint_id"]

    # Fetch single checkpoint
    resp_get = client.get(f"/api/v1/checkpoints/{checkpoint_id}")
    assert resp_get.status_code == 200
    assert resp_get.json()["session_id"] == "sess-api-test"

    # List checkpoints
    resp_list = client.get("/api/v1/checkpoints?session_id=sess-api-test")
    assert resp_list.status_code == 200
    assert len(resp_list.json()) >= 1

    # Resume handoff
    resp_resume = client.post("/api/v1/resume", json={"checkpoint_id": checkpoint_id})
    assert resp_resume.status_code == 200
    resume_data = resp_resume.json()
    assert "resumed_prompt" in resume_data
    assert "Monolithic router file" in resume_data["resumed_prompt"]

    # Delete checkpoint
    resp_delete = client.delete(f"/api/v1/checkpoints/{checkpoint_id}")
    assert resp_delete.status_code == 200
    assert resp_delete.json()["status"] == "deleted"

    # Verify 404 after deletion
    resp_get_deleted = client.get(f"/api/v1/checkpoints/{checkpoint_id}")
    assert resp_get_deleted.status_code == 404
