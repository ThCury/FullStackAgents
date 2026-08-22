"""Helpers compartilhados pelos nós. Nós são adapters finos - traduzem
SquadState <-> chamada de agente/caso de uso, sem carregar regra de negócio
(§6, SRP)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ...domain.entities.agent_message import AgentMessage
from ...domain.enums import AgentRole, MessageKind
from ...domain.ports.repositories import MessageRepository


async def emit_pipeline_message(
    message_repo: MessageRepository,
    run_id: str,
    to_agent: AgentRole,
    kind: MessageKind,
    ref: str | None,
    summary: str,
    rationale: str,
) -> dict:
    """Mensagens de orquestração determinística (dispatch/escalate/integrate)
    também são auditáveis - remetente AgentRole.PIPELINE."""
    seq = await message_repo.next_seq(run_id)
    message = AgentMessage(
        id=str(uuid.uuid4()),
        run_id=run_id,
        seq=seq,
        from_agent=AgentRole.PIPELINE,
        to_agent=to_agent,
        kind=kind,
        ref=ref,
        summary=summary,
        payload={},
        rationale=rationale,
        created_at=datetime.now(timezone.utc),
    )
    await message_repo.append(message)
    return message.to_dict()


def with_story_status(backlog: list[dict], story_id: str, status: str) -> list[dict]:
    return [{**s, "status": status} if s["id"] == story_id else s for s in backlog]
