"""Repositórios MongoDB (ADR-01).

Convenções deste módulo
-----------------------
- `_id` recebe o id de domínio. Não geramos ObjectId: o id vem do
  `IdGeneratorPort` e é o mesmo que aparece no Console e nos logs.
- Coleções append-only (`agent_messages`, `llm_calls`, `artifacts`, `adrs`,
  `test_reports`) só têm `insert_one`. **Não adicione `update` nelas** — a
  imutabilidade é o que faz a trilha ser auditoria e não log.
- Serialização via `model_dump(mode="json")`, o que mantém o documento legível
  no Compass. Custo: datetime vira string ISO. Aceitável — as consultas de
  auditoria são por `run_id` e `seq`, não por range de data.
"""

from __future__ import annotations

from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from domain.entities.backlog import Story
from domain.entities.delivery import ADR, Artifact
from domain.entities.messaging import AgentMessage, LlmCall
from domain.entities.quality import TestReport
from domain.entities.run import Run
from domain.enums import AgentRole

# Motor é genérico sobre o tipo do documento. O alias evita repetir o
# parâmetro em cada assinatura e deixa óbvio que trafegamos dict cru.
type MongoDatabase = AsyncIOMotorDatabase[dict[str, Any]]


def _doc(entity: Any, id_field: str = "id") -> dict[str, Any]:
    data: dict[str, Any] = entity.model_dump(mode="json")
    data["_id"] = data.pop(id_field)
    return data


def _undoc(document: dict[str, Any], id_field: str = "id") -> dict[str, Any]:
    data = dict(document)
    data[id_field] = data.pop("_id")
    return data


class MongoRunRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.runs

    async def save(self, run: Run) -> None:
        document = _doc(run)
        await self._col.replace_one({"_id": run.id}, document, upsert=True)

    async def get(self, run_id: str) -> Run | None:
        document = await self._col.find_one({"_id": run_id})
        return Run.model_validate(_undoc(document)) if document else None

    async def list_recent(self, limit: int = 20) -> list[Run]:
        cursor = self._col.find().sort("created_at", DESCENDING).limit(limit)
        return [Run.model_validate(_undoc(d)) async for d in cursor]


class MongoMessageRepository:
    """Append-only. `seq` vem de um contador atômico.

    `find_one_and_update` com `$inc` é o que garante ordem total sem race —
    diferente do in-memory, aqui não dá para usar lock de processo, porque
    pode haver mais de uma instância da API.
    """

    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.agent_messages
        self._counters = db.counters

    async def append(self, message: AgentMessage) -> None:
        await self._col.insert_one(_doc(message))

    async def next_seq(self, run_id: str) -> int:
        document = await self._counters.find_one_and_update(
            {"_id": f"seq:{run_id}"},
            {"$inc": {"value": 1}},
            upsert=True,
            return_document=ReturnDocument.BEFORE,
        )
        return int(document["value"]) if document else 0

    async def list_by_run(self, run_id: str, since_seq: int = -1) -> list[AgentMessage]:
        cursor = self._col.find({"run_id": run_id, "seq": {"$gt": since_seq}}).sort(
            "seq", ASCENDING
        )
        return [AgentMessage.model_validate(_undoc(d)) async for d in cursor]

    async def list_by_agent(self, run_id: str, agent: AgentRole) -> list[AgentMessage]:
        cursor = self._col.find({"run_id": run_id, "from_agent": agent.value}).sort(
            "seq", ASCENDING
        )
        return [AgentMessage.model_validate(_undoc(d)) async for d in cursor]


class MongoLlmCallRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.llm_calls

    async def append(self, call: LlmCall) -> None:
        await self._col.insert_one(_doc(call))

    async def get(self, call_id: str) -> LlmCall | None:
        document = await self._col.find_one({"_id": call_id})
        return LlmCall.model_validate(_undoc(document)) if document else None

    async def list_by_run(self, run_id: str) -> list[LlmCall]:
        cursor = self._col.find({"run_id": run_id}).sort("created_at", ASCENDING)
        return [LlmCall.model_validate(_undoc(d)) async for d in cursor]


class MongoStoryRepository:
    """Única coleção com `update`: `status` da story muda ao longo do run."""

    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.stories

    async def save_many(self, run_id: str, stories: list[Story]) -> None:
        if not stories:
            return
        await self._col.insert_many([{**_doc(s), "run_id": run_id} for s in stories])

    async def update(self, run_id: str, story: Story) -> None:
        await self._col.replace_one(
            {"_id": story.id, "run_id": run_id}, {**_doc(story), "run_id": run_id}, upsert=True
        )

    async def get(self, run_id: str, story_id: str) -> Story | None:
        document = await self._col.find_one({"_id": story_id, "run_id": run_id})
        if not document:
            return None
        document.pop("run_id", None)
        return Story.model_validate(_undoc(document))

    async def list_by_run(self, run_id: str) -> list[Story]:
        cursor = self._col.find({"run_id": run_id})
        out: list[Story] = []
        async for document in cursor:
            document.pop("run_id", None)
            out.append(Story.model_validate(_undoc(document)))
        return out


class MongoArtifactRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.artifacts

    async def append(self, artifact: Artifact) -> None:
        await self._col.insert_one(_doc(artifact))

    async def list_by_story(self, run_id: str, story_id: str) -> list[Artifact]:
        cursor = self._col.find({"run_id": run_id, "story_ref": story_id}).sort(
            "attempt", ASCENDING
        )
        return [Artifact.model_validate(_undoc(d)) async for d in cursor]

    async def list_by_run(self, run_id: str) -> list[Artifact]:
        cursor = self._col.find({"run_id": run_id}).sort("created_at", ASCENDING)
        return [Artifact.model_validate(_undoc(d)) async for d in cursor]


class MongoAdrRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.adrs

    async def append_many(self, run_id: str, adrs: list[ADR]) -> None:
        if not adrs:
            return
        await self._col.insert_many([{**_doc(a), "run_id": run_id} for a in adrs])

    async def list_by_run(self, run_id: str) -> list[ADR]:
        cursor = self._col.find({"run_id": run_id}).sort("created_at", ASCENDING)
        out: list[ADR] = []
        async for document in cursor:
            document.pop("run_id", None)
            out.append(ADR.model_validate(_undoc(document)))
        return out


class MongoTestReportRepository:
    def __init__(self, db: MongoDatabase) -> None:
        self._col = db.test_reports

    async def append(self, report: TestReport) -> None:
        await self._col.insert_one(_doc(report))

    async def list_by_run(self, run_id: str) -> list[TestReport]:
        cursor = self._col.find({"run_id": run_id}).sort("created_at", ASCENDING)
        return [TestReport.model_validate(_undoc(d)) async for d in cursor]

    async def list_by_story(self, run_id: str, story_id: str) -> list[TestReport]:
        cursor = self._col.find({"run_id": run_id, "story_ref": story_id}).sort(
            "attempt", ASCENDING
        )
        return [TestReport.model_validate(_undoc(d)) async for d in cursor]
