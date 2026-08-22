from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from ..entities.agent_message import AgentMessage
from ..enums import AgentRole


@dataclass
class AgentContext:
    run_id: str
    state: dict[str, Any]  # trecho relevante do SquadState que o agente precisa


@dataclass
class AgentResult:
    state_updates: dict[str, Any]
    message: AgentMessage


class Agent(Protocol):
    role: AgentRole

    async def run(self, ctx: AgentContext) -> AgentResult: ...
