from pathlib import Path

import pytest

from agents.coder.agent import CoderAgent
from agents.developer.agent import DeveloperAgent
from agents.product_owner.agent import ProductOwnerAgent
from application.costs import CostCalculator
from application.run_service import RunService
from domain.models.create_run_command import CreateRunCommand
from domain.models.product_backlog import REJECTION_MESSAGE
from infrastructure.llm import FakeStreamingLLM
from infrastructure.memory_repository import InMemoryRunRepository
from infrastructure.workspace_manager import LocalWorkspaceManager

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "template"


def make_service(tmp_path: Path, too_complex: bool = False) -> RunService:
    return RunService(
        repository=InMemoryRunRepository(),
        product_owner=ProductOwnerAgent(
            FakeStreamingLLM(too_complex=too_complex), model="fake-po-v1", effort="medium"
        ),
        developer=DeveloperAgent(FakeStreamingLLM(), model="fake-dev-v1", effort="medium"),
        coder=CoderAgent(FakeStreamingLLM(), model="fake-coder-v1", effort="medium"),
        workspace_manager=LocalWorkspaceManager(tmp_path, TEMPLATE_ROOT),
        cost_calculator=CostCalculator(),
        stream_persist_interval_ms=0,
    )


def calls_of(run: dict) -> list[dict]:
    return [item for item in run["audit"]["timeline"] if item["type"] == "LLM_CALL"]


def events_of(run: dict) -> list[str]:
    return [item["event"] for item in run["audit"]["timeline"] if item["type"] == "FLOW_EVENT"]


def artifact_of(run: dict, artifact_type: str) -> dict:
    return next(item for item in run["artifacts"] if item["type"] == artifact_type)


def test_prompt_is_saved_before_po_execution(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))

    assert run["status"] == "PENDING"
    assert run["input"]["content"] == "Quero um portal para clientes."
    assert run["audit"]["timeline"][0]["type"] == "USER_PROMPT"
    assert run["audit"]["timeline"][0]["brasil_datetime"].endswith("-03:00")


def test_full_flow_persists_po_dev_and_coder(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    assert saved["status"] == "COMPLETED"
    assert saved["error"] is None
    assert saved["output"]["status"] == "ACCEPTED"
    assert saved["output"]["user_stories"][0]["requirement_ids"] == ["RF-001"]
    assert {"PRODUCT_OWNER", "DEVELOPER", "CODER"} == {
        call["agent"]["role"] for call in calls_of(saved)
    }
    assert all(call["status"] == "SUCCEEDED" for call in calls_of(saved))
    assert saved["audit"]["totals"]["total_tokens"] > 0
    assert "RUN_COMPLETED" in events_of(saved)


def test_tool_loop_produces_one_audited_call_per_iteration(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    dev_calls = [call for call in calls_of(saved) if call["agent"]["role"] == "DEVELOPER"]
    assert [call["iteration"] for call in dev_calls] == [1, 2, 3]
    assert [call["tool_calls"][0]["name"] for call in dev_calls[:2]] == ["list_files", "read_file"]
    assert dev_calls[-1]["tool_calls"] == []
    assert dev_calls[0]["request"]["tools_offered"] == ["list_files", "read_file", "grep"]
    assert dev_calls[0]["tool_results"][0]["is_error"] is False
    assert "docs/agent-manifest.md" in dev_calls[0]["tool_results"][0]["content"]


def test_coder_writes_to_the_workspace(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    workspace = artifact_of(saved, "workspace")["content"]
    written = Path(workspace["code_path"]) / "docs" / "nota-do-coder.md"
    assert written.is_file()
    assert "Nota do coder" in written.read_text(encoding="utf-8")

    report = artifact_of(saved, "implementation_report")["content"]
    assert report["performed_writes"] == [{"path": "docs/nota-do-coder.md", "action": "create"}]
    assert report["divergences"] == []
    assert Path(report["path"]).is_file()


def test_coder_tools_include_write_but_planner_tools_do_not(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    offered = {
        call["agent"]["role"]: call["request"]["tools_offered"]
        for call in calls_of(saved)
        if call["iteration"] == 1
    }
    assert "write_file" not in offered["DEVELOPER"]
    assert "write_file" in offered["CODER"]
    assert offered["PRODUCT_OWNER"] == []


def test_too_complex_backlog_stops_before_the_workspace(tmp_path: Path) -> None:
    service = make_service(tmp_path, too_complex=True)
    run = service.create(CreateRunCommand(prompt="Quero um ERP completo."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    assert saved["status"] == "COMPLETED"
    assert saved["output"]["status"] == "TOO_COMPLEX"
    assert saved["output"]["rejection"] == REJECTION_MESSAGE
    assert "Thiago Cury Freire" in saved["output"]["rejection"]
    assert events_of(saved).count("PO_BACKLOG_REJECTED") == 1
    assert "DEV_WORKSPACE_CREATED" not in events_of(saved)
    assert saved["artifacts"] == []
    assert list(tmp_path.iterdir()) == []


def test_audited_prompt_version_comes_from_the_prompt_file(tmp_path: Path) -> None:
    service = make_service(tmp_path)
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    versions = {
        call["agent"]["role"]: call["request"]["system_prompt_version"]
        for call in calls_of(saved)
    }
    assert versions["PRODUCT_OWNER"].startswith("po-")
    assert versions["DEVELOPER"].startswith("dev-")
    assert versions["CODER"].startswith("coder-")


def test_failed_run_keeps_tokens_already_spent_by_po(tmp_path: Path) -> None:
    class FailingStreamingLLM:
        provider = "fake"

        def stream(self, request):
            raise RuntimeError("Falha simulada no DEV")

    service = RunService(
        repository=InMemoryRunRepository(),
        product_owner=ProductOwnerAgent(FakeStreamingLLM(), model="fake-po-v1", effort=None),
        developer=DeveloperAgent(FailingStreamingLLM(), model="fake-dev-v1", effort=None),
        coder=CoderAgent(FakeStreamingLLM(), model="fake-coder-v1", effort=None),
        workspace_manager=LocalWorkspaceManager(tmp_path, TEMPLATE_ROOT),
        cost_calculator=CostCalculator(),
        stream_persist_interval_ms=0,
    )
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    assert saved["status"] == "FAILED"
    assert saved["audit"]["totals"]["total_tokens"] > 0


def test_gemini_can_be_selected_per_agent_config(monkeypatch) -> None:
    from config import AGENT_LLM_PROFILES, AgentLLMProfile

    monkeypatch.setitem(
        AGENT_LLM_PROFILES,
        "PRODUCT_OWNER",
        AgentLLMProfile(provider="gemini", model="gemini-3.6-flash"),
    )
    profile = ProductOwnerAgent.llm_profile()
    assert profile.provider == "gemini"
    assert profile.model == "gemini-3.6-flash"


@pytest.mark.parametrize(
    "path",
    ["../fora.txt", "/etc/passwd", "codigo/../../fuga.txt"],
)
def test_workspace_refuses_paths_outside_the_run(tmp_path: Path, path: str) -> None:
    manager = LocalWorkspaceManager(tmp_path, TEMPLATE_ROOT)
    workspace = manager.create_project("run_abcdef12", "projeto")

    with pytest.raises(ValueError):
        manager.write_code(workspace, path, "conteudo")


def test_workspace_cannot_reach_another_run(tmp_path: Path) -> None:
    manager = LocalWorkspaceManager(tmp_path, TEMPLATE_ROOT)
    first = manager.create_project("run_11111111", "projeto")
    second = manager.create_project("run_22222222", "projeto")
    escape = f"../../{Path(second['code_path']).parent.name}/codigo/invadido.txt"

    with pytest.raises(ValueError):
        manager.write_code(first, escape, "conteudo")
