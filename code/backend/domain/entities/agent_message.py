from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..enums import AgentRole, MessageKind
from ..value_objects.token_usage import TokenUsage


@dataclass
class AgentMessage:
    """O envelope de auditoria - é o que o avaliador lê para 'enxergar o
    squad trabalhando junto'. Todo agente é obrigado a emitir uma mensagem
    ao final do seu `run()` (garantido pelo template method em agents/base.py,
    não pela disciplina de cada implementação)."""

    id: str
    run_id: str
    seq: int
    from_agent: AgentRole
    to_agent: AgentRole
    kind: MessageKind
    ref: str | None
    summary: str
    payload: dict
    rationale: str
    usage: TokenUsage = field(default_factory=TokenUsage)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "seq": self.seq,
            "from_agent": self.from_agent.value,
            "to_agent": self.to_agent.value,
            "kind": self.kind.value,
            "ref": self.ref,
            "summary": self.summary,
            "payload": self.payload,
            "rationale": self.rationale,
            "usage": self.usage.to_dict(),
            "created_at": self.created_at,
        }
