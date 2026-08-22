"""Template method comum aos 4 agentes: pré (build_prompt) -> loop agentic
contra o LLMPort -> valida/parseia (parse_result) -> emite AgentMessage.

Nenhuma subclasse pode "esquecer" de emitir a mensagem de auditoria - está
aqui, no `run()` final, não na boa vontade de cada implementação (§8.1)."""
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any

from .. import config
from ..domain.enums import AgentRole, MessageKind
from ..domain.entities.agent_message import AgentMessage
from ..domain.ports.agent import AgentContext, AgentResult
from ..domain.ports.llm import LLMPort, LLMRequest
from ..domain.ports.repositories import MessageRepository
from ..domain.value_objects.token_usage import TokenUsage


class BaseAgent(ABC):
    role: AgentRole
    model: str
    effort: str = "medium"
    # Thinking adaptativo (ligado por padrão em claude-sonnet-5/opus-5) consome
    # tokens do MESMO orçamento de max_tokens antes do texto visível - um valor
    # baixo aqui trunca a resposta sem aviso, muito antes do limite "parecer"
    # atingido. 16000 é o piso recomendado para chamadas não-streaming.
    max_output_tokens: int = 16000
    system_prompt: str = ""
    max_tool_iterations: int = config.MAX_TOOL_ITERATIONS

    def __init__(self, llm: LLMPort, message_repo: MessageRepository):
        self._llm = llm
        self._messages = message_repo

    # -- hooks dos agentes concretos ------------------------------------------

    def tools(self) -> list[dict]:
        return []

    def execute_tool(self, name: str, tool_input: dict) -> str:
        raise NotImplementedError(f"{self.role} não declara execute_tool para '{name}'")

    @abstractmethod
    def build_prompt(self, ctx: AgentContext) -> str: ...

    @abstractmethod
    def parse_result(
        self, raw_text: str, ctx: AgentContext
    ) -> tuple[dict[str, Any], MessageKind, str | None, str, str]:
        """Retorna (state_updates, kind, ref, summary, rationale)."""
        ...

    def next_agent(self, kind: MessageKind, state_updates: dict[str, Any]) -> AgentRole:
        return AgentRole.PIPELINE

    # -- template method -----------------------------------------------------

    async def run(self, ctx: AgentContext) -> AgentResult:
        user_prompt = self.build_prompt(ctx)
        raw_text, usage = await self._tool_loop(ctx.run_id, user_prompt)
        state_updates, kind, ref, summary, rationale = self.parse_result(raw_text, ctx)

        seq = await self._messages.next_seq(ctx.run_id)
        message = AgentMessage(
            id=str(uuid.uuid4()),
            run_id=ctx.run_id,
            seq=seq,
            from_agent=self.role,
            to_agent=self.next_agent(kind, state_updates),
            kind=kind,
            ref=ref,
            summary=summary,
            payload=state_updates,
            rationale=rationale,
            usage=usage,
            created_at=datetime.now(timezone.utc),
        )
        await self._messages.append(message)
        return AgentResult(state_updates=state_updates, message=message)

    async def _tool_loop(self, run_id: str, user_prompt: str) -> tuple[str, TokenUsage]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": user_prompt}]
        total_usage = TokenUsage()
        tools = self.tools()

        for _ in range(self.max_tool_iterations):
            req = LLMRequest(
                run_id=run_id,
                agent=self.role.value,
                model=self.model,
                system=self.system_prompt,
                messages=messages,
                tools=tools,
                effort=self.effort,
                max_tokens=self.max_output_tokens,
            )
            res = await self._llm.complete(req)
            total_usage = total_usage + res.usage
            messages.append({"role": "assistant", "content": res.raw_content})

            if res.stop_reason == "max_tokens":
                # Resposta cortada no meio (thinking + tool_use grande, ex: write_file de um
                # arquivo grande, comem o mesmo orçamento de max_tokens) - nunca é uma resposta
                # final válida, mesmo que não tenha vindo tool_use nesta rodada específica.
                messages.append({
                    "role": "user",
                    "content": (
                        "Sua resposta anterior foi cortada por exceder o limite de tokens antes "
                        "de terminar. Continue de onde parou (ou refaça de forma mais concisa) "
                        "até produzir a resposta final completa."
                    ),
                })
                continue

            if res.tool_uses:
                tool_results = []
                for tu in res.tool_uses:
                    try:
                        result = self.execute_tool(tu.name, tu.input)
                    except Exception as exc:  # nunca deixar o loop morrer por erro de tool
                        result = f"[erro ao executar {tu.name}] {exc}"
                    tool_results.append({"type": "tool_result", "tool_use_id": tu.id, "content": str(result)})
                messages.append({"role": "user", "content": tool_results})
                continue

            if not res.text.strip():
                # Parou de chamar ferramentas mas também não respondeu nada em texto -
                # sinal de confusão do modelo, não uma resposta final de verdade.
                messages.append({
                    "role": "user",
                    "content": "Sua resposta ficou vazia. Responda com o JSON final conforme instruído.",
                })
                continue

            return res.text, total_usage

        return "[o agente atingiu o número máximo de iterações de ferramentas]", total_usage
