from fastapi.testclient import TestClient

from config import AGENT_LLM_PROFILES, AgentLLMProfile, Settings
from main import create_app


def test_health_and_po_run(monkeypatch) -> None:
    monkeypatch.setitem(
        AGENT_LLM_PROFILES,
        "PRODUCT_OWNER",
        AgentLLMProfile(provider="fake", model="fake-po-v1"),
    )
    app = create_app(Settings())
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        response = client.post("/runs", json={"prompt": "Quero uma agenda para consultório."})
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        result = client.get(f"/runs/{run_id}/result")
        assert result.status_code == 200
        assert result.json()["user_stories"]
