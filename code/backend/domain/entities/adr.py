from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ADR:
    """Log de decisão técnica do Dev Agent. `alternatives_considered` é
    obrigatório - sem alternativas, 'justificativa' vira racionalização."""

    id: str
    run_id: str
    story_ref: str
    decision: str
    context: str
    alternatives_considered: list[str]
    rationale: str
    consequences: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "story_ref": self.story_ref,
            "decision": self.decision,
            "context": self.context,
            "alternatives_considered": self.alternatives_considered,
            "rationale": self.rationale,
            "consequences": self.consequences,
            "created_at": self.created_at,
        }
