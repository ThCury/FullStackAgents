from fastapi.testclient import TestClient

from fullstack_agents.config import Settings
from fullstack_agents.main import create_app


def test_health_and_po_run() -> None:
    app = create_app(Settings(persistence="memory", llm_mode="fake"))
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200
        response = client.post("/runs", json={"prompt": "Quero uma agenda para consultório."})
        assert response.status_code == 202
        run_id = response.json()["run_id"]
        result = client.get(f"/runs/{run_id}/result")
        assert result.status_code == 200
        assert result.json()["user_stories"]

