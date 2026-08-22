from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..enums import RunStatus


@dataclass
class Run:
    id: str
    raw_briefing: str
    status: RunStatus = RunStatus.PENDING
    budget_usd: float = 5.0
    total_cost_usd: float = 0.0
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "raw_briefing": self.raw_briefing,
            "status": self.status.value,
            "budget_usd": self.budget_usd,
            "total_cost_usd": self.total_cost_usd,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Run":
        return cls(
            id=data["id"],
            raw_briefing=data["raw_briefing"],
            status=RunStatus(data.get("status", "pending")),
            budget_usd=data.get("budget_usd", 5.0),
            total_cost_usd=data.get("total_cost_usd", 0.0),
            error=data.get("error"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )
