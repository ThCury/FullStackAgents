from __future__ import annotations

from ... import config
from ...domain.errors import BudgetExceeded
from ...domain.ports.agent import AgentContext
from ...domain.ports.repositories import StoryRepository
from .common import with_story_status
from ..state import SquadState


def make_qa_node(qa_agent, story_repo: StoryRepository):
    async def node(state: SquadState) -> dict:
        ctx = AgentContext(run_id=state["run_id"], state=dict(state))
        try:
            result = await qa_agent.run(ctx)
        except BudgetExceeded as exc:
            return {"status": "awaiting_human", "escalation_reason": str(exc)}

        story_id = state["current_story_id"]
        report = result.state_updates["test_report"]
        approved = report["verdict"] == "approved"

        updates: dict = {
            "test_reports": [report],
            "messages": [result.message.to_dict()],
        }

        if approved:
            await story_repo.update_status(story_id, "approved")
            updates["backlog"] = with_story_status(state["backlog"], story_id, "approved")
            updates["status"] = "running"
        else:
            rework = dict(state["rework"])
            rework[story_id] = rework.get(story_id, 0) + 1
            updates["rework"] = rework
            if rework[story_id] >= config.MAX_REVISIONS:
                await story_repo.update_status(story_id, "escalated")
                updates["backlog"] = with_story_status(state["backlog"], story_id, "escalated")
                # mesmo sinal usado pelo BudgetExceeded - é o que permite ao caller
                # (StartRun) distinguir "run pausado em escalate" de "run concluído"
                # olhando só o status final, sem inspecionar o motivo.
                updates["status"] = "awaiting_human"
                updates["escalation_reason"] = (
                    f"story {story_id} atingiu o limite de retrabalho ({rework[story_id]} reprovações)"
                )
            else:
                await story_repo.update_status(story_id, "in_dev")
                updates["backlog"] = with_story_status(state["backlog"], story_id, "in_dev")
                updates["status"] = "running"

        return updates

    return node
