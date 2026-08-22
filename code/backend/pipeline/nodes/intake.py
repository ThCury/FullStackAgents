from __future__ import annotations

from ...domain.errors import BudgetExceeded
from ...domain.ports.agent import AgentContext
from ..state import SquadState


def make_intake_node(analyst_agent):
    async def node(state: SquadState) -> dict:
        ctx = AgentContext(run_id=state["run_id"], state=dict(state))
        try:
            result = await analyst_agent.run(ctx)
        except BudgetExceeded as exc:
            return {"status": "awaiting_human", "escalation_reason": str(exc)}
        return {
            "briefing": result.state_updates["briefing"],
            "messages": [result.message.to_dict()],
        }

    return node
