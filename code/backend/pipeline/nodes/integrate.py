"""`integrate` também é determinístico: backlog vazio (todas as stories
aprovadas ou escaladas). Nesta fase (Fase 0/1 da arquitetura) marca o run como
concluído - subir o app via docker compose e gerar os relatórios finais fica
para a Fase 4 (scaffold curado do Rivexx + seed), que ainda não foi
construída. Os 3 entregáveis (backlog/decisões/QA) já existem em Mongo desde
o primeiro momento em que cada agente entrega, então nada fica perdido
enquanto isso não é automatizado aqui."""
from __future__ import annotations

from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.repositories import MessageRepository
from .common import emit_pipeline_message
from ..state import SquadState


def make_integrate_node(message_repo: MessageRepository):
    async def node(state: SquadState) -> dict:
        approved = sum(1 for s in state["backlog"] if s["status"] == "approved")
        escalated = sum(1 for s in state["backlog"] if s["status"] == "escalated")
        await emit_pipeline_message(
            message_repo,
            state["run_id"],
            to_agent=AgentRole.PIPELINE,
            kind=MessageKind.DECISION,
            ref=None,
            summary=f"Backlog concluído: {approved} stories aprovadas, {escalated} escaladas",
            rationale="integrate: dispatch não encontrou mais stories pendentes",
        )
        return {"status": "done"}

    return node
