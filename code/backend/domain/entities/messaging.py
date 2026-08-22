"""A trilha de auditoria — o entregável mais importante da Trilha B.

O enunciado é explícito: "Um output final sem orquestração visível não será
considerado." Esta entidade é o que o avaliador lê para enxergar o squad
trabalhando junto.

Dois níveis, deliberadamente separados (§8):
  - `AgentMessage` — handoff de NEGÓCIO. Legível por humano. É a timeline.
  - `LlmCall`      — chamada TÉCNICA crua. Prompt e resposta. É a auditoria.

O Console mostra os dois lado a lado. É isso que separa "confia em mim" de
auditável.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from domain.enums import AgentRole, MessageKind
from domain.value_objects import TokenUsage


class AgentMessage(BaseModel):
    """Um handoff explícito entre dois agentes.

    Emitida pelo `BaseAgent` (template method) — não pela boa vontade de cada
    implementação. Agente que não emite não completa o `run()`.
    """

    model_config = ConfigDict(frozen=True)

    id: str
    run_id: str
    seq: int = Field(ge=0, description="Ordem total dentro do run")
    from_agent: AgentRole
    to_agent: AgentRole
    kind: MessageKind
    ref: str | None = Field(default=None, description="story_id / artifact_id relacionado")
    summary: str = Field(min_length=1, description="Uma linha legível por humano")
    payload: dict[str, Any] = Field(default_factory=dict)
    rationale: str = Field(
        default="",
        description="O POR QUÊ. É o que torna a mensagem auditável em vez de só logada.",
    )
    usage: TokenUsage = Field(default_factory=TokenUsage.zero)
    llm_call_ref: str | None = Field(
        default=None, description="Liga o handoff de negócio à chamada crua que o gerou"
    )
    created_at: datetime | None = None

    def headline(self) -> str:
        return f"#{self.seq} {self.from_agent} -> {self.to_agent} [{self.kind}] {self.summary}"


class LlmCall(BaseModel):
    """Registro cru de uma chamada ao modelo.

    `prompt_hash` existe para detectar quebra de prompt caching: se o hash do
    prefixo muda a cada chamada, o cache nunca vai acertar (§8.4).
    """

    model_config = ConfigDict(frozen=True)

    id: str
    run_id: str
    agent: AgentRole
    model: str
    system_prompt: str
    user_prompt: str
    raw_response: str
    usage: TokenUsage
    latency_ms: int = Field(default=0, ge=0)
    prompt_hash: str = ""
    effort: str = ""
    error: str | None = None
    created_at: datetime | None = None

    @property
    def cache_hit(self) -> bool:
        return self.usage.cache_read_tokens > 0
