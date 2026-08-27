from pathlib import Path

from fastapi.testclient import TestClient

from config import AGENT_LLM_PROFILES, AgentLLMProfile, BackendConfig, Settings
from main import create_app


def test_project_continues_in_the_same_workspace(monkeypatch, tmp_path: Path) -> None:
    for role in ("PRODUCT_OWNER", "DEVELOPER", "CODER"):
        monkeypatch.setitem(
            AGENT_LLM_PROFILES,
            role,
            AgentLLMProfile(provider="fake", model=f"fake-{role.lower()}-v1"),
        )
    app = create_app(Settings(dev_workspace_root=tmp_path), BackendConfig(persistence="memory"))

    with TestClient(app) as client:
        created = client.post(
            "/projects",
            json={"name": "calculadora", "prompt": "Criar uma calculadora de lucro."},
        )
        assert created.status_code == 202
        project_id = created.json()["project_id"]
        first_run_id = created.json()["run_id"]
        first_run = client.get(f"/runs/{first_run_id}?dataset=full").json()
        first_workspace = next(
            item["content"] for item in first_run["artifacts"] if item["type"] == "workspace"
        )

        continued = client.post(
            f"/projects/{project_id}/messages",
            json={"content": "Adicione uma explicação do lucro."},
        )
        assert continued.status_code == 202
        second_run = client.get(f"/runs/{continued.json()['run_id']}?dataset=full").json()
        second_workspace = next(
            item["content"] for item in second_run["artifacts"] if item["type"] == "workspace"
        )

        assert first_workspace["code_path"] == second_workspace["code_path"]
        assert "DEV_WORKSPACE_REUSED" in [
            item["event"]
            for item in second_run["audit"]["timeline"]
            if item["type"] == "FLOW_EVENT"
        ]
        assert client.get(f"/projects/{project_id}/messages").json()["total"] == 2
        assert client.get(f"/projects/{project_id}/runs").json()["total"] == 2
