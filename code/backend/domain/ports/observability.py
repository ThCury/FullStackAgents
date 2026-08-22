"""Ports de observabilidade — medição de tokens e barramento de eventos."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from domain.enums import AgentRole
from domain.value_objects import BudgetSnapshot, TokenUsage


@runtime_checkable
class TokenMeterPort(Protocol):
    """Controle de tokens nos 3 escopos: run, agente, chamada (§8.3).

    `assert_within_budget` levanta `BudgetExceeded` — o grafo captura e roteia
    para `escalate`, que pede aprovação humana. Estourar orçamento não mata o
    run.
    """

    async def assert_within_budget(self, run_id: str, agent: AgentRole, planned: int) -> None: ...
    async def record(self, run_id: str, agent: AgentRole, usage: TokenUsage) -> None: ...
    async def snapshot(self, run_id: str) -> BudgetSnapshot: ...
    async def approve_extension(self, run_id: str, extra_tokens: int) -> BudgetSnapshot: ...


class SquadEvent(BaseModel):
    """Evento para o Console. É o que faz a orquestração ser *visível*."""

    model_config = ConfigDict(frozen=True)

    run_id: str
    type: str  # node_started | node_finished | message | budget | interrupt | run_finished
    payload: dict[str, Any]


@runtime_checkable
class EventBusPort(Protocol):
    """Publish/subscribe para o stream SSE.

    Deliberadamente fire-and-forget: perder um evento de UI nunca pode derrubar
    a execução do squad.
    """

    async def publish(self, event: SquadEvent) -> None: ...
    def subscribe(self, run_id: str) -> EventSubscription: ...


@runtime_checkable
class EventSubscription(Protocol):
    def __aiter__(self) -> EventSubscription: ...
    async def __anext__(self) -> SquadEvent: ...
    async def close(self) -> None: ...
