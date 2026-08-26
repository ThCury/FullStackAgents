from typing import Protocol

from domain.models.llm_request import LLMRequest
from domain.models.tool_call import ToolCall
from domain.models.tool_result import ToolResult


class AgentAuditor(Protocol):
    """Registra cada iteração do loop de ferramentas na trilha de auditoria.

    O loop não conhece persistência: ele apenas avisa o que aconteceu, e quem
    orquestra decide como gravar.
    """

    def start_call(self, request: LLMRequest, iteration: int) -> str:
        """Abre a chamada e devolve o call_id que a identifica."""
        ...

    def stream_delta(self, call_id: str, content: str) -> None: ...

    def finish_call(
        self,
        call_id: str,
        content: str,
        completion: dict,
        latency_ms: int,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> None: ...

    def fail_call(self, call_id: str, content: str, latency_ms: int, error: str) -> None: ...


class NullAgentAuditor:
    """Auditor inerte para testes e execuções fora do grafo."""

    def __init__(self) -> None:
        self.calls = 0

    def start_call(self, request: LLMRequest, iteration: int) -> str:
        self.calls += 1
        return f"call_{iteration}"

    def stream_delta(self, call_id: str, content: str) -> None:
        return None

    def finish_call(
        self,
        call_id: str,
        content: str,
        completion: dict,
        latency_ms: int,
        tool_calls: list[ToolCall],
        tool_results: list[ToolResult],
    ) -> None:
        return None

    def fail_call(self, call_id: str, content: str, latency_ms: int, error: str) -> None:
        return None
