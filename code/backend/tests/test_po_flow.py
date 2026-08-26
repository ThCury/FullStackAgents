from agents.product_owner.agent import ProductOwnerAgent
from application.costs import CostCalculator
from application.run_service import RunService
from domain.models.create_run_command import CreateRunCommand
from infrastructure.llm import FakeStreamingLLM
from infrastructure.memory_repository import InMemoryRunRepository


def make_service() -> RunService:
    return RunService(
        repository=InMemoryRunRepository(),
        agent=ProductOwnerAgent(FakeStreamingLLM(), model="fake-po-v1", effort="medium"),
        cost_calculator=CostCalculator(),
        stream_persist_interval_ms=0,
    )


def test_prompt_is_saved_before_po_execution() -> None:
    service = make_service()
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))

    assert run["status"] == "PENDING"
    assert run["input"]["content"] == "Quero um portal para clientes."
    assert run["audit"]["timeline"][0]["type"] == "USER_PROMPT"
    assert run["audit"]["timeline"][0]["brasil_datetime"].endswith("-03:00")


def test_po_result_and_audit_are_persisted() -> None:
    service = make_service()
    run = service.create(CreateRunCommand(prompt="Quero um portal para clientes."))
    service.execute(run["_id"])
    saved = service.get_or_raise(run["_id"])

    assert saved["status"] == "COMPLETED"
    assert saved["output"]["requirements"]
    assert saved["output"]["user_stories"]
    call = next(item for item in saved["audit"]["timeline"] if item["type"] == "LLM_CALL")
    assert call["status"] == "SUCCEEDED"
    assert call["request"]["system_prompt"]
    assert call["response"]["content"]
    assert call["usage"]["total_tokens"] > 0
    assert call["latency_ms"] >= 0


def test_gemini_can_be_selected_per_agent_config(monkeypatch) -> None:
    from config import AGENT_LLM_PROFILES, AgentLLMProfile

    monkeypatch.setitem(
        AGENT_LLM_PROFILES,
        "PRODUCT_OWNER",
        AgentLLMProfile(provider="gemini", model="gemini-2.5-flash"),
    )
    profile = ProductOwnerAgent.llm_profile()
    assert profile.provider == "gemini"
    assert profile.model == "gemini-2.5-flash"
