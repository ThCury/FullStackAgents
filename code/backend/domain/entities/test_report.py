from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..enums import Verdict


@dataclass
class TestCase:
    name: str
    result: str  # pass | fail
    notes: str = ""

    def to_dict(self) -> dict:
        return {"name": self.name, "result": self.result, "notes": self.notes}


@dataclass
class TestReport:
    id: str
    run_id: str
    story_ref: str
    verdict: Verdict
    test_cases: list[TestCase]
    evidence: str
    feedback: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "story_ref": self.story_ref,
            "verdict": self.verdict.value,
            "test_cases": [c.to_dict() for c in self.test_cases],
            "evidence": self.evidence,
            "feedback": self.feedback,
            "created_at": self.created_at,
        }
