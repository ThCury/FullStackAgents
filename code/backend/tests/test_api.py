from fastapi.testclient import TestClient

from config import AGENT_LLM_PROFILES, AgentLLMProfile, BackendConfig, Settings
from main import create_app


def test_health_and_po_run(monkeypatch) -> None:
    monkeypatch.setitem(
        AGENT_LLM_PROFILES,
        "PRODUCT_OWNER",
        AgentLLMProfile(provider="fake", model="fake-po-v1"),
    )
    app = create_app(Settings(), BackendConfig(persistence="memory"))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        assert health.json()["persistence"] == "memory"
        response = client.post("/runs", json={"prompt": "Quero uma agenda para consultório."})
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        run_list = client.get("/runs")
        assert run_list.status_code == 200
        assert run_list.json()["total"] == 1
        assert run_list.json()["runs"][0]["run_id"] == run_id
        assert "response_received" not in run_list.json()["runs"][0]
        resume = client.get(f"/runs/{run_id}")
        assert resume.status_code == 200
        assert resume.json()["status"] == "SUCCESS"
        assert resume.json()["prompt_sent"] == "Quero uma agenda para consultório."
        assert "audit" not in resume.json()
        assert resume.json()["tokens_spent"]["total"] > 0
        full = client.get(f"/runs/{run_id}?dataset=full")
        assert full.status_code == 200
        assert full.json()["audit"]["timeline"]
        result = client.get(f"/runs/{run_id}/result")
        assert result.status_code == 200
        assert result.json()["user_stories"]
