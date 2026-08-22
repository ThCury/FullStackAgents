"""`escalate` pausa o run com `interrupt()` do LangGraph e pede decisão
humana - seja por limite de retrabalho (3 reprovações na mesma story) ou por
orçamento estourado (BudgetExceeded). O run fica pausado no checkpointer
Mongo até alguém retomar com `Command(resume=...)` - nada é perdido."""
from __future__ import annotations

from langgraph.types import interrupt

from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.repositories import MessageRepository
from .common import emit_pipeline_message
from ..state import SquadState


def make_escalate_node(message_repo: MessageRepository):
    async def node(state: SquadState) -> dict:
        reason = state.get("escalation_reason") or "limite de retrabalho atingido para a story atual"
        payload = {
            "reason": reason,
            "story_id": state.get("current_story_id"),
            "rework": state.get("rework", {}),
        }
        await emit_pipeline_message(
            message_repo,
            state["run_id"],
            to_agent=AgentRole.PIPELINE,
            kind=MessageKind.DECISION,
            ref=state.get("current_story_id"),
            summary=f"Run pausado para decisão humana: {reason}",
            rationale="escalate: interrupt() aguardando aprovação/decisão humana antes de continuar",
        )

        decision = interrupt(payload)

        if isinstance(decision, dict) and decision.get("action") == "resume_dev":
            rework = dict(state.get("rework", {}))
            story_id = state.get("current_story_id")
            if story_id:
                rework[story_id] = 0
            return {"status": "resume_dev", "rework": rework, "escalation_reason": None}

        return {"status": "failed"}

    return node
