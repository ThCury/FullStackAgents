from __future__ import annotations

from time import monotonic
from uuid import uuid4

from application.costs import CostCalculator
from domain.models.audit_time import now_audit_time
from domain.models.llm_request import LLMRequest
from domain.models.run_totals import RunTotals
from domain.models.tool_call import ToolCall
from domain.models.tool_result import ToolResult
from domain.ports.run_repository import RunRepository

MAX_AUDITED_TOOL_OUTPUT = 4_000
TRUNCATION_NOTICE = "\n[... saída truncada na auditoria ...]"


class TimelineAuditor:
    """Grava cada iteração do loop de um agente como uma chamada na timeline.

    Uma iteração = uma entrada `LLM_CALL`. Um agente que usa dez ferramentas
    aparece como dez chamadas numeradas, com o custo e a latência de cada uma.
    """

    def __init__(
        self,
        repository: RunRepository,
        cost_calculator: CostCalculator,
        run_id: str,
        agent_id: str,
        role: str,
        version: str,
        provider: str,
        stream_persist_interval_seconds: float,
    ) -> None:
        self._repository = repository
        self._cost_calculator = cost_calculator
        self._run_id = run_id
        self._agent_id = agent_id
        self._role = role
        self._version = version
        self._provider = provider
        self._interval = stream_persist_interval_seconds
        self._last_persist = 0.0
        self._collected: list[RunTotals] = []
        self.iterations = 0

    @property
    def totals(self) -> RunTotals:
        if not self._collected:
            return self._cost_calculator.totals(0, 0, 0, 0)
        return self._cost_calculator.combine(*self._collected)

    def start_call(self, request: LLMRequest, iteration: int, retry_attempt: int = 1) -> str:
        call_id = f"call_{uuid4().hex}"
        self.iterations = iteration
        self._last_persist = monotonic()
        started_at = now_audit_time()
        self._repository.append_timeline(
            self._run_id,
            {
                "sequence": self._repository.reserve_sequence(self._run_id),
                "type": "LLM_CALL",
                "call_id": call_id,
                "attempt": 1,
                "iteration": iteration,
                "retry_attempt": retry_attempt,
                "agent": {"id": self._agent_id, "role": self._role, "version": self._version},
                "request": {
                    "from": {"type": "agent", "id": self._agent_id, "role": self._role},
                    "to": {"type": "llm_provider", "id": self._provider},
                    "prompt": request.prompt,
                    "system_prompt": request.system_prompt,
                    "system_prompt_version": self._version,
                    "model": request.model,
                    "provider": self._provider,
                    "parameters": {"temperature": request.temperature},
                    "effort": request.effort,
                    "tools_offered": [tool.name for tool in request.tools],
                    "history_messages": len(request.history),
                },
                "response": {
                    "from": {"type": "llm_provider", "id": self._provider},
                    "to": {"type": "agent", "id": self._agent_id},
                    "content": "",
                },
                "tool_calls": [],
                "tool_results": [],
                "usage": {
                    "input_tokens": None,
                    "output_tokens": None,
                    "cached_tokens": None,
                    "total_tokens": None,
                },
                "cost": {"estimated": None, "billed": None},
                "started_at": started_at.model_dump(),
                "status": "STREAMING",
                "error": None,
                **started_at.model_dump(),
            },
        )
        return call_id

    def stream_delta(self, call_id: str, content: str) -> None:
        if monotonic() - self._last_persist < self._interval:
            return
        self._repository.update_streaming_response(self._run_id, call_id, content)
        self._last_persist = monotonic()

    def finish_call(
        self,
        call_id: str,
        content: str,
        completion: dict,
        latency_ms: int,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> None:
        totals = self._cost_calculator.totals(
            completion.get("input_tokens"),
            completion.get("output_tokens"),
            completion.get("cached_tokens"),
            latency_ms,
        )
        self._collected.append(totals)
        self._repository.finish_call(
            self._run_id,
            call_id,
            {
                "response.content": content,
                "response.finish_reason": completion.get("finish_reason"),
                "provider_response_id": completion.get("provider_response_id"),
                "tool_calls": [call.model_dump() for call in tool_calls],
                "tool_results": [self._audited(result) for result in tool_results],
                "usage": {
                    "input_tokens": completion.get("input_tokens"),
                    "output_tokens": completion.get("output_tokens"),
                    "cached_tokens": completion.get("cached_tokens"),
                    "total_tokens": totals.total_tokens,
                },
                "cost": {"estimated": totals.estimated_cost.model_dump(), "billed": None},
                "finished_at": now_audit_time().model_dump(),
                "latency_ms": latency_ms,
                "status": "SUCCEEDED",
            },
        )
        # Atualiza após cada iteração: se um agente posterior falhar, o consumo
        # já realizado continua visível no resumo da run.
        self._repository.update_totals(self._run_id, self.totals.model_dump())

    def fail_call(self, call_id: str, content: str, latency_ms: int, error: str) -> None:
        self._repository.finish_call(
            self._run_id,
            call_id,
            {
                "response.content": content,
                "finished_at": now_audit_time().model_dump(),
                "latency_ms": latency_ms,
                "status": "FAILED",
                "error": error,
            },
        )

    @staticmethod
    def _audited(result: ToolResult) -> dict:
        """O conteúdo de um arquivo lido não precisa ir inteiro para o banco."""
        content = result.content
        if len(content) > MAX_AUDITED_TOOL_OUTPUT:
            content = content[:MAX_AUDITED_TOOL_OUTPUT] + TRUNCATION_NOTICE
        return {
            "call_id": result.call_id,
            "name": result.name,
            "is_error": result.is_error,
            "content": content,
        }
