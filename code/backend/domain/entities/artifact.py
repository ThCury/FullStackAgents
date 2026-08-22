from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Artifact:
    id: str
    run_id: str
    story_id: str
    summary: str
    files_changed: list[str] = field(default_factory=list)
    tests_written: list[str] = field(default_factory=list)
    commit_sha: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "story_id": self.story_id,
            "summary": self.summary,
            "files_changed": self.files_changed,
            "tests_written": self.tests_written,
            "commit_sha": self.commit_sha,
            "created_at": self.created_at,
        }
