"""`dispatch` é determinístico (sem LLM) - pega a próxima story pronta,
decide fan-out (sequencial, decisão registrada com o usuário) e roteia."""
from __future__ import annotations

from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.repositories import MessageRepository, StoryRepository
from .common import emit_pipeline_message, with_story_status
from ..state import SquadState


def make_dispatch_node(message_repo: MessageRepository, story_repo: StoryRepository):
    async def node(state: SquadState) -> dict:
        pending = [s for s in state["backlog"] if s["status"] == "pending"]
        if not pending:
            return {"status": "integrating"}

        next_story = pending[0]
        await story_repo.update_status(next_story["id"], "in_dev")
        message = await emit_pipeline_message(
            message_repo,
            state["run_id"],
            to_agent=AgentRole.DEVELOPER,
            kind=MessageKind.HANDOFF,
            ref=next_story["id"],
            summary=f"Despachando story {next_story['id']} ({next_story['title']}) para o Dev",
            rationale="dispatch determinístico: próxima story com status 'pending' no backlog, fan-out sequencial",
        )
        return {
            "current_story_id": next_story["id"],
            "backlog": with_story_status(state["backlog"], next_story["id"], "in_dev"),
            "status": "in_dev",
            "messages": [message],
        }

    return node
