from application.costs import CostCalculator
from domain.models.llm_request import LLMRequest
from infrastructure.memory_repository import InMemoryRunRepository
from pipeline.timeline_auditor import TimelineAuditor


def test_auditor_updates_run_totals_after_each_successful_call() -> None:
    repository = InMemoryRunRepository()
    calculator = CostCalculator()
    repository.create(
        {
            "_id": "run_test",
            "audit": {
                "next_sequence": 0,
                "timeline": [],
                "totals": calculator.totals(0, 0, 0, 0).model_dump(),
            },
        }
    )
    auditor = TimelineAuditor(
        repository=repository,
        cost_calculator=calculator,
        run_id="run_test",
        agent_id="po",
        role="PRODUCT_OWNER",
        version="po-test",
        provider="fake",
        stream_persist_interval_seconds=0,
    )
    call_id = auditor.start_call(
        LLMRequest(
            prompt="Criar uma calculadora.",
            system_prompt="Você é PO.",
            model="fake-po-v1",
        ),
        iteration=1,
    )
    auditor.finish_call(
        call_id,
        '{"status": "ACCEPTED"}',
        {"input_tokens": 10, "output_tokens": 20, "cached_tokens": 0},
        latency_ms=50,
        tool_calls=[],
        tool_results=[],
    )

    assert repository.get("run_test")["audit"]["totals"]["total_tokens"] == 30
