from __future__ import annotations

from dataclasses import dataclass, field

from ..enums import Priority
from ..value_objects.acceptance_criterion import AcceptanceCriterion


@dataclass
class Story:
    id: str
    run_id: str
    title: str
    description: str
    priority: Priority
    scenario_tag: str
    acceptance_criteria: list[AcceptanceCriterion] = field(default_factory=list)
    status: str = "pending"  # pending | in_dev | in_qa | approved | rejected

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "scenario_tag": self.scenario_tag,
            "acceptance_criteria": [c.to_dict() for c in self.acceptance_criteria],
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Story":
        return cls(
            id=data["id"],
            run_id=data.get("run_id", ""),
            title=data["title"],
            description=data["description"],
            priority=Priority(data.get("priority", "should")),
            scenario_tag=data.get("scenario_tag", ""),
            acceptance_criteria=[AcceptanceCriterion.from_dict(c) for c in data.get("acceptance_criteria", [])],
            status=data.get("status", "pending"),
        )
