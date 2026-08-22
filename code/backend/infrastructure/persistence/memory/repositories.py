"""Repositórios em memória.

Não são "só para teste": `SQUAD_PERSISTENCE=memory` permite subir o squad
inteiro sem Mongo. Junto com `SQUAD_LLM=fake`, um dev clona o repo e vê a
esteira rodando sem instalar nada além das dependências Python.

As mesmas ports são implementadas pelo Mongo em `../mongo/repositories.py`. Se
um comportamento divergir entre as duas, é bug — a suíte
`tests/integration/test_repository_parity.py` compara as duas implementações
contra o mesmo roteiro.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from domain.entities.backlog import Story
from domain.entities.delivery import ADR, Artifact
from domain.entities.messaging import AgentMessage, LlmCall
from domain.entities.quality import TestReport
from domain.entities.run import Run
from domain.enums import AgentRole


class InMemoryRunRepository:
    def __init__(self) -> None:
        self._runs: dict[str, Run] = {}

    async def save(self, run: Run) -> None:
        self._runs[run.id] = run

    async def get(self, run_id: str) -> Run | None:
        return self._runs.get(run_id)

    async def list_recent(self, limit: int = 20) -> list[Run]:
        ordered = sorted(
            self._runs.values(),
            key=lambda r: r.created_at.isoformat() if r.created_at else "",
            reverse=True,
        )
        return ordered[:limit]


class InMemoryMessageRepository:
    """Append-only, com `seq` monotônico protegido por lock.

    O lock existe porque `next_seq` + `append` é read-modify-write: com fan-out
    de stories em paralelo, duas mensagens receberiam o mesmo `seq` e a timeline
    do Console ficaria ambígua.
    """

    def __init__(self) -> None:
        self._by_run: dict[str, list[AgentMessage]] = defaultdict(list)
        self._seq: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    async def append(self, message: AgentMessage) -> None:
        async with self._lock:
            self._by_run[message.run_id].append(message)

    async def next_seq(self, run_id: str) -> int:
        async with self._lock:
            current = self._seq[run_id]
            self._seq[run_id] = current + 1
            return current

    async def list_by_run(self, run_id: str, since_seq: int = -1) -> list[AgentMessage]:
        return [m for m in self._by_run[run_id] if m.seq > since_seq]

    async def list_by_agent(self, run_id: str, agent: AgentRole) -> list[AgentMessage]:
        return [m for m in self._by_run[run_id] if m.from_agent == agent]


class InMemoryLlmCallRepository:
    def __init__(self) -> None:
        self._by_id: dict[str, LlmCall] = {}
        self._by_run: dict[str, list[LlmCall]] = defaultdict(list)

    async def append(self, call: LlmCall) -> None:
        self._by_id[call.id] = call
        self._by_run[call.run_id].append(call)

    async def get(self, call_id: str) -> LlmCall | None:
        return self._by_id.get(call_id)

    async def list_by_run(self, run_id: str) -> list[LlmCall]:
        return list(self._by_run[run_id])


class InMemoryStoryRepository:
    def __init__(self) -> None:
        self._by_run: dict[str, dict[str, Story]] = defaultdict(dict)

    async def save_many(self, run_id: str, stories: list[Story]) -> None:
        for story in stories:
            self._by_run[run_id][story.id] = story

    async def update(self, run_id: str, story: Story) -> None:
        self._by_run[run_id][story.id] = story

    async def get(self, run_id: str, story_id: str) -> Story | None:
        return self._by_run[run_id].get(story_id)

    async def list_by_run(self, run_id: str) -> list[Story]:
        return list(self._by_run[run_id].values())


class InMemoryArtifactRepository:
    def __init__(self) -> None:
        self._by_run: dict[str, list[Artifact]] = defaultdict(list)

    async def append(self, artifact: Artifact) -> None:
        self._by_run[artifact.run_id].append(artifact)

    async def list_by_story(self, run_id: str, story_id: str) -> list[Artifact]:
        return [a for a in self._by_run[run_id] if a.story_ref == story_id]

    async def list_by_run(self, run_id: str) -> list[Artifact]:
        return list(self._by_run[run_id])


class InMemoryAdrRepository:
    def __init__(self) -> None:
        self._by_run: dict[str, list[ADR]] = defaultdict(list)

    async def append_many(self, run_id: str, adrs: list[ADR]) -> None:
        self._by_run[run_id].extend(adrs)

    async def list_by_run(self, run_id: str) -> list[ADR]:
        return list(self._by_run[run_id])


class InMemoryTestReportRepository:
    def __init__(self) -> None:
        self._by_run: dict[str, list[TestReport]] = defaultdict(list)

    async def append(self, report: TestReport) -> None:
        self._by_run[report.run_id].append(report)

    async def list_by_run(self, run_id: str) -> list[TestReport]:
        return list(self._by_run[run_id])

    async def list_by_story(self, run_id: str, story_id: str) -> list[TestReport]:
        return [r for r in self._by_run[run_id] if r.story_ref == story_id]
