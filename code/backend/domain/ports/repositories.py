"""Ports de persistência — segregados de propósito (ISP).

A segregação aqui não é higiene de código, é **controle de escopo do agente**
(§6): o QA Agent recebe `TestReportRepository` e `TestRunnerPort`, e portanto
não consegue nem acidentalmente escrever código de produção — ele não tem a
port para isso.

Ao injetar dependência em um agente, dê o mínimo. Se precisar de "tudo",
provavelmente o agente está fazendo duas coisas.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from domain.entities.backlog import Story
from domain.entities.delivery import ADR, Artifact
from domain.entities.messaging import AgentMessage, LlmCall
from domain.entities.quality import TestReport
from domain.entities.run import Run
from domain.enums import AgentRole


@runtime_checkable
class RunRepository(Protocol):
    async def save(self, run: Run) -> None: ...
    async def get(self, run_id: str) -> Run | None: ...
    async def list_recent(self, limit: int = 20) -> list[Run]: ...


@runtime_checkable
class MessageRepository(Protocol):
    """Append-only. Não existe `update` nem `delete` — é a trilha de auditoria."""

    async def append(self, message: AgentMessage) -> None: ...
    async def next_seq(self, run_id: str) -> int: ...
    async def list_by_run(self, run_id: str, since_seq: int = -1) -> list[AgentMessage]: ...
    async def list_by_agent(self, run_id: str, agent: AgentRole) -> list[AgentMessage]: ...


@runtime_checkable
class LlmCallRepository(Protocol):
    """Append-only. Prompt e resposta crus para a auditoria técnica."""

    async def append(self, call: LlmCall) -> None: ...
    async def get(self, call_id: str) -> LlmCall | None: ...
    async def list_by_run(self, run_id: str) -> list[LlmCall]: ...


@runtime_checkable
class StoryRepository(Protocol):
    async def save_many(self, run_id: str, stories: list[Story]) -> None: ...
    async def update(self, run_id: str, story: Story) -> None: ...
    async def get(self, run_id: str, story_id: str) -> Story | None: ...
    async def list_by_run(self, run_id: str) -> list[Story]: ...


@runtime_checkable
class ArtifactRepository(Protocol):
    """Append-only: rework gera nova tentativa, não sobrescreve a anterior."""

    async def append(self, artifact: Artifact) -> None: ...
    async def list_by_story(self, run_id: str, story_id: str) -> list[Artifact]: ...
    async def list_by_run(self, run_id: str) -> list[Artifact]: ...


@runtime_checkable
class AdrRepository(Protocol):
    async def append_many(self, run_id: str, adrs: list[ADR]) -> None: ...
    async def list_by_run(self, run_id: str) -> list[ADR]: ...


@runtime_checkable
class TestReportRepository(Protocol):
    async def append(self, report: TestReport) -> None: ...
    async def list_by_run(self, run_id: str) -> list[TestReport]: ...
    async def list_by_story(self, run_id: str, story_id: str) -> list[TestReport]: ...
