from __future__ import annotations

from ...domain.errors import BudgetExceeded
from ...domain.ports.agent import AgentContext
from ...domain.ports.repositories import StoryRepository
from ..state import SquadState


def make_po_node(po_agent, story_repo: StoryRepository):
    async def node(state: SquadState) -> dict:
        ctx = AgentContext(run_id=state["run_id"], state=dict(state))
        try:
            result = await po_agent.run(ctx)
        except BudgetExceeded as exc:
            return {"status": "awaiting_human", "escalation_reason": str(exc)}

        backlog = result.state_updates["backlog"]
        from ...domain.entities.story import Story

        await story_repo.save_many([Story.from_dict({**s, "run_id": state["run_id"]}) for s in backlog])

        return {
            "backlog": backlog,
            "messages": [result.message.to_dict()],
        }

    return node
