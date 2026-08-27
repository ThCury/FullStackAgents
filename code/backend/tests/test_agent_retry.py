from collections.abc import Iterator

from agents.agent_loop import AgentLoop
from domain.models.llm_completed import LLMCompleted
from domain.models.llm_request import LLMRequest
from domain.models.llm_stream_event import LLMStreamEvent
from domain.ports.agent_auditor import NullAgentAuditor


class FlakyLLM:
    provider = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("503 UNAVAILABLE")
        yield LLMStreamEvent(type="delta", delta='{"ok": true}')
        yield LLMStreamEvent(
            type="completed",
            completed=LLMCompleted(
                input_tokens=1,
                output_tokens=1,
                cached_tokens=0,
                finish_reason="stop",
            ),
        )


def test_agent_loop_retries_only_the_failed_llm_call() -> None:
    llm = FlakyLLM()
    auditor = NullAgentAuditor()
    outcome = AgentLoop(
        llm,
        auditor,
        max_iterations=1,
        max_retries=1,
        retry_base_delay_seconds=0,
    ).run(LLMRequest(prompt="teste", system_prompt="teste", model="fake"))

    assert outcome.as_json() == {"ok": True}
    assert llm.calls == 2
    assert auditor.calls == 2
