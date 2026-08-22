"""Implementações Mongo dos ports de repositório (domain/ports/repositories.py).
Cada classe implementa exatamente um Protocol - ISP na prática."""
from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorDatabase

from ....domain.entities.adr import ADR
from ....domain.entities.agent_message import AgentMessage
from ....domain.entities.artifact import Artifact
from ....domain.entities.run import Run
from ....domain.entities.story import Story
from ....domain.entities.test_report import TestReport, TestCase
from ....domain.enums import AgentRole, MessageKind, RunStatus, Verdict
from ....domain.value_objects.token_usage import TokenUsage


class MongoRunRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["runs"]

    async def save(self, run: Run) -> None:
        await self._col.update_one({"_id": run.id}, {"$set": {**run.to_dict(), "_id": run.id}}, upsert=True)

    async def get(self, run_id: str) -> Run | None:
        doc = await self._col.find_one({"_id": run_id})
        if not doc:
            return None
        doc.pop("_id", None)
        doc["id"] = run_id
        return Run.from_dict(doc)

    async def list_recent(self, limit: int = 20) -> list[Run]:
        cursor = self._col.find().sort("created_at", -1).limit(limit)
        runs = []
        async for doc in cursor:
            doc["id"] = doc.pop("_id")
            runs.append(Run.from_dict(doc))
        return runs


class MongoStoryRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["stories"]

    async def save_many(self, stories: list[Story]) -> None:
        if not stories:
            return
        for story in stories:
            doc = story.to_dict()
            await self._col.update_one({"_id": story.id}, {"$set": {**doc, "_id": story.id}}, upsert=True)

    async def update_status(self, story_id: str, status: str) -> None:
        await self._col.update_one({"_id": story_id}, {"$set": {"status": status}})

    async def list_by_run(self, run_id: str) -> list[Story]:
        cursor = self._col.find({"run_id": run_id})
        stories = []
        async for doc in cursor:
            doc["id"] = doc.pop("_id")
            stories.append(Story.from_dict(doc))
        return stories


class MongoMessageRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["agent_messages"]

    async def append(self, message: AgentMessage) -> None:
        doc = message.to_dict()
        doc["_id"] = message.id
        await self._col.insert_one(doc)

    async def list_by_run(self, run_id: str) -> list[AgentMessage]:
        cursor = self._col.find({"run_id": run_id}).sort("seq", 1)
        out = []
        async for doc in cursor:
            out.append(
                AgentMessage(
                    id=doc["_id"],
                    run_id=doc["run_id"],
                    seq=doc["seq"],
                    from_agent=AgentRole(doc["from_agent"]),
                    to_agent=AgentRole(doc["to_agent"]),
                    kind=MessageKind(doc["kind"]),
                    ref=doc.get("ref"),
                    summary=doc["summary"],
                    payload=doc.get("payload", {}),
                    rationale=doc.get("rationale", ""),
                    usage=TokenUsage(**doc.get("usage", {})),
                    created_at=doc["created_at"],
                )
            )
        return out

    async def next_seq(self, run_id: str) -> int:
        last = await self._col.find_one({"run_id": run_id}, sort=[("seq", -1)])
        return (last["seq"] + 1) if last else 1


class MongoArtifactRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["artifacts"]

    async def append(self, artifact: Artifact) -> None:
        doc = artifact.to_dict()
        doc["_id"] = artifact.id
        await self._col.insert_one(doc)

    async def list_by_run(self, run_id: str) -> list[Artifact]:
        cursor = self._col.find({"run_id": run_id})
        return [Artifact(**{**doc, "id": doc.pop("_id")}) async for doc in cursor]


class MongoADRRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["adrs"]

    async def append(self, adr: ADR) -> None:
        doc = adr.to_dict()
        doc["_id"] = adr.id
        await self._col.insert_one(doc)

    async def list_by_run(self, run_id: str) -> list[ADR]:
        cursor = self._col.find({"run_id": run_id})
        return [ADR(**{**doc, "id": doc.pop("_id")}) async for doc in cursor]


class MongoTestReportRepository:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["test_reports"]

    async def append(self, report: TestReport) -> None:
        doc = report.to_dict()
        doc["_id"] = report.id
        await self._col.insert_one(doc)

    async def list_by_run(self, run_id: str) -> list[TestReport]:
        cursor = self._col.find({"run_id": run_id})
        out = []
        async for doc in cursor:
            out.append(
                TestReport(
                    id=doc["_id"],
                    run_id=doc["run_id"],
                    story_ref=doc["story_ref"],
                    verdict=Verdict(doc["verdict"]),
                    test_cases=[TestCase(**c) for c in doc.get("test_cases", [])],
                    evidence=doc.get("evidence", ""),
                    feedback=doc.get("feedback", ""),
                    created_at=doc["created_at"],
                )
            )
        return out
