from __future__ import annotations

import json
import re
from time import monotonic

from application.workspace_toolset import WorkspaceToolset
from domain.models.llm_message import LLMMessage
from domain.models.llm_request import LLMRequest
from domain.ports.agent_auditor import AgentAuditor
from domain.ports.streaming_llm import StreamingLLM

FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class MaxIterationsError(RuntimeError):
    """O agente não concluiu dentro do orçamento de iterações."""


class LoopOutcome:
    def __init__(self, text: str, iterations: int, writes: list[dict[str, str]]) -> None:
        self.text = text
        self.iterations = iterations
        self.writes = writes

    def as_json(self) -> dict:
        """Interpreta a resposta final como JSON, tolerando cerca de código."""
        candidate = self.text.strip()
        fenced = FENCE.match(candidate)
        if fenced:
            candidate = fenced.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as error:
            raise ValueError(f"Resposta final não é JSON válido: {error}") from error


class AgentLoop:
    """Conversa com o modelo até ele parar de pedir ferramentas.

    Cada iteração é uma chamada auditada: o `AgentAuditor` recebe a requisição,
    os deltas, as ferramentas pedidas e os resultados devolvidos.
    """

    def __init__(
        self,
        llm: StreamingLLM,
        auditor: AgentAuditor,
        toolset: WorkspaceToolset | None = None,
        max_iterations: int = 24,
    ) -> None:
        self._llm = llm
        self._auditor = auditor
        self._toolset = toolset
        self._max_iterations = max_iterations

    def run(self, request: LLMRequest) -> LoopOutcome:
        tools = self._toolset.definitions() if self._toolset else []
        history: list[LLMMessage] = list(request.history)

        for iteration in range(1, self._max_iterations + 1):
            current = request.model_copy(update={"tools": tools, "history": history})
            call_id = self._auditor.start_call(current, iteration)
            started = monotonic()
            parts: list[str] = []

            try:
                completion, tool_calls = self._consume(current, call_id, parts)
            except Exception as error:
                self._auditor.fail_call(
                    call_id, "".join(parts), self._elapsed(started), str(error)
                )
                raise

            text = "".join(parts)
            if not tool_calls:
                self._auditor.finish_call(
                    call_id, text, completion, self._elapsed(started), [], []
                )
                return LoopOutcome(text, iteration, self._writes())

            if self._toolset is None:
                raise ValueError("O modelo pediu ferramentas, mas nenhuma foi oferecida.")

            try:
                results = [self._toolset.execute(call) for call in tool_calls]
            except Exception as error:
                self._auditor.fail_call(call_id, text, self._elapsed(started), str(error))
                raise

            self._auditor.finish_call(
                call_id, text, completion, self._elapsed(started), tool_calls, results
            )
            history = history + [
                LLMMessage(role="assistant", content=text, tool_calls=tool_calls),
                LLMMessage(role="tool", tool_results=results),
            ]

        raise MaxIterationsError(
            f"O agente não concluiu em {self._max_iterations} iterações de ferramentas."
        )

    def _consume(self, request: LLMRequest, call_id: str, parts: list[str]):
        completion: dict = {}
        tool_calls = []
        for event in self._llm.stream(request):
            if event.type == "delta" and event.delta:
                parts.append(event.delta)
                self._auditor.stream_delta(call_id, "".join(parts))
            elif event.type == "completed":
                tool_calls = list(event.tool_calls)
                if event.completed:
                    completion = event.completed.model_dump()
        return completion, tool_calls

    def _writes(self) -> list[dict[str, str]]:
        return self._toolset.writes if self._toolset else []

    @staticmethod
    def _elapsed(started: float) -> int:
        return round((monotonic() - started) * 1000)
