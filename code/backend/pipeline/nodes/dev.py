from __future__ import annotations

from ...domain.errors import BudgetExceeded
from ...domain.ports.agent import AgentContext
from ...domain.ports.repositories import StoryRepository
from .common import with_story_status
from ..state import SquadState


def make_dev_node(dev_agent, story_repo: StoryRepository):
    async def node(state: SquadState) -> dict:
        ctx = AgentContext(run_id=state["run_id"], state=dict(state))
        try:
            result = await dev_agent.run(ctx)
        except BudgetExceeded as exc:
            return {"status": "awaiting_human", "escalation_reason": str(exc)}

        story_id = state["current_story_id"]
        await story_repo.update_status(story_id, "in_qa")

        return {
            "backlog": with_story_status(state["backlog"], story_id, "in_qa"),
            "artifacts": [result.state_updates["artifact"]],
            "adrs": [result.state_updates["adr"]],
            "messages": [result.message.to_dict()],
        }

    return node
