"""AgentRole -> Agent. Existe para que adicionar um agente novo (ex: um
SecurityAgent) não exija editar nenhum agente existente - só um pacote novo
em agents/, uma entrada aqui e um nó no grafo (OCP, §6)."""
from __future__ import annotations

from ..domain.enums import AgentRole
from ..domain.ports.agent import Agent


class AgentRegistry:
    def __init__(self):
        self._agents: dict[AgentRole, Agent] = {}

    def register(self, role: AgentRole, agent: Agent) -> None:
        self._agents[role] = agent

    def get(self, role: AgentRole) -> Agent:
        return self._agents[role]

    def items(self):
        return self._agents.items()
