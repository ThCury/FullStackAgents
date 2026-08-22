"""Port do modelo de linguagem.

Esconde do resto do sistema *qual* provider e *como* falamos com ele. É o que
permite: (a) rodar todo o squad com `FakeLLM` determinístico nos testes,
(b) trocar `langchain-anthropic` pelo SDK cru sem tocar em nenhum agente.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from domain.enums import AgentRole, Effort
from domain.value_objects import TokenUsage


class LLMRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: str
    agent: AgentRole
    system: str = Field(
        description="Prefixo ESTÁVEL. Conteúdo volátil aqui destrói o prompt caching (§8.4)."
    )
    user: str
    output_schema: dict[str, Any] = Field(
        description="JSON Schema da resposta. Structured output elimina retry de parsing."
    )
    effort: Effort = Effort.HIGH
    max_tokens: int = Field(default=16_000, gt=0)
    cache_system: bool = True


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    data: dict[str, Any] = Field(description="Payload já validado contra `output_schema`")
    raw_text: str
    model: str
    usage: TokenUsage
    latency_ms: int = 0
    call_id: str | None = None


@runtime_checkable
class LLMPort(Protocol):
    """Uma operação só. ISP: quem chama o modelo não precisa de mais nada."""

    async def complete(self, request: LLMRequest) -> LLMResponse: ...

    async def count_tokens(self, request: LLMRequest) -> int:
        """Pré-medição antes de gastar.

        Implementações devem usar a API de contagem do provider — nunca
        `tiktoken`, que é de outro tokenizer e devolve número errado.
        """
        ...
