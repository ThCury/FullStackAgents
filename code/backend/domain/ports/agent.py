"""Port do agente — o contrato que torna o registry substituível (LSP + OCP).

O grafo nunca conhece um agente concreto: pede ao `agent_registry` por
`AgentRole` e chama `run()`. Adicionar um agente novo não edita nenhum
existente.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from domain.entities.messaging import AgentMessage
from domain.enums import AgentRole, MessageKind
from domain.value_objects import TokenUsage


class AgentContext(BaseModel):
    """Tudo que o agente precisa para trabalhar — e nada além.

    `inputs` é intencionalmente opaco: cada agente conhece a forma do que
    consome e valida no `build_prompt`. O grafo só transporta.
    """

    model_config = ConfigDict(frozen=True)

    run_id: str
    seq: int = Field(ge=0, description="Posição na trilha de auditoria")
    inputs: dict[str, Any] = Field(default_factory=dict)
    feedback: list[str] = Field(
        default_factory=list,
        description="Mudanças requeridas pelo QA em uma tentativa anterior",
    )
    attempt: int = Field(default=1, ge=1)


class AgentResult(BaseModel):
    """Saída de um agente: o artefato + a mensagem auditável que o acompanha."""

    model_config = ConfigDict(frozen=True)

    role: AgentRole
    payload: dict[str, Any]
    message: AgentMessage
    usage: TokenUsage = Field(default_factory=TokenUsage.zero)
    kind: MessageKind = MessageKind.DELIVERY


@runtime_checkable
class Agent(Protocol):
    """Um papel = uma responsabilidade.

    Implementar direto é possível, mas herde de `agents.base.BaseAgent`: ele
    garante a emissão da `AgentMessage`, que é requisito de avaliação, não
    detalhe de implementação.
    """

    role: AgentRole

    async def run(self, ctx: AgentContext) -> AgentResult: ...
