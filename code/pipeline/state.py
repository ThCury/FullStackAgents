"""Schema do estado compartilhado do grafo LangGraph.

Campos escalares (backlog, story_index, status, ...) seguem a semântica padrão
do LangGraph: cada nó retorna um dict parcial e o valor mais recente sobrescreve
o anterior. Campos anotados com `operator.add` são acumulativos — cada nó
retorna apenas os itens novos e o LangGraph concatena à lista existente. Isso é
o que torna a comunicação entre agentes auditável: nada é sobrescrito, tudo fica
registrado em ordem cronológica.
"""
from __future__ import annotations

import operator
from typing import Annotated, Literal, TypedDict


class UserStory(TypedDict):
    id: str
    title: str
    description: str
    priority: Literal["alta", "media", "baixa"]
    acceptance_criteria: list[str]


class DevDecision(TypedDict):
    story_id: str
    summary: str
    rationale: str
    files_changed: list[str]
    tests_written: list[str]


class QAResult(TypedDict):
    story_id: str
    approved: bool
    test_cases: list[dict]
    evidence: str
    feedback: str


class Message(TypedDict):
    from_agent: str
    to_agent: str
    content: str
    ts: float


class PipelineState(TypedDict):
    raw_brief: str
    enriched_brief: str

    backlog: list[UserStory]
    story_index: int
    current_story_id: str | None

    decision_log: Annotated[list[DevDecision], operator.add]
    qa_report: Annotated[list[QAResult], operator.add]
    communication_log: Annotated[list[Message], operator.add]

    revision_count: int
    max_revisions: int
    status: str


def initial_state(brief: str, max_revisions: int | None = None) -> PipelineState:
    from . import config

    return PipelineState(
        raw_brief=brief,
        enriched_brief="",
        backlog=[],
        story_index=0,
        current_story_id=None,
        decision_log=[],
        qa_report=[],
        communication_log=[],
        revision_count=0,
        max_revisions=max_revisions if max_revisions is not None else config.MAX_REVISIONS,
        status="started",
    )
