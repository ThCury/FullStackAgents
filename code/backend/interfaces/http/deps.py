"""Injeção de dependência do FastAPI.

O container é construído uma vez no `lifespan` e guardado em `app.state`. Estas
funções só o expõem aos routers — não constroem nada. Construir por requisição
abriria conexão de Mongo a cada chamada e perderia o estado do EventBus.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from application.use_cases.query_run import QueryRunUseCase
from application.use_cases.run_squad import (
    ApproveBudgetUseCase,
    ResumeRunUseCase,
    StartRunUseCase,
)
from factory.container import Container


def get_container(request: Request) -> Container:
    container: Container | None = getattr(request.app.state, "container", None)
    if container is None:  # pragma: no cover — só ocorre se o lifespan não rodou
        raise RuntimeError("container não inicializado — verifique o lifespan da app")
    return container


ContainerDep = Annotated[Container, Depends(get_container)]


def get_start_run(container: ContainerDep) -> StartRunUseCase:
    return StartRunUseCase(
        runs=container.repositories.runs,
        workspace=container.workspace,
        events=container.events,
        ids=container.ids,
        clock=container.clock,
        graph=container.graph,
        policy=container.settings.budget_policy(),
    )


def get_resume_run(container: ContainerDep) -> ResumeRunUseCase:
    return ResumeRunUseCase(
        runs=container.repositories.runs,
        events=container.events,
        clock=container.clock,
        graph=container.graph,
    )


def get_approve_budget(container: ContainerDep) -> ApproveBudgetUseCase:
    return ApproveBudgetUseCase(runs=container.repositories.runs, meter=container.meter)


def get_query_run(container: ContainerDep) -> QueryRunUseCase:
    repos = container.repositories
    return QueryRunUseCase(
        runs=repos.runs,
        messages=repos.messages,
        llm_calls=repos.llm_calls,
        stories=repos.stories,
        artifacts=repos.artifacts,
        adrs=repos.adrs,
        reports=repos.test_reports,
        meter=container.meter,
    )


StartRunDep = Annotated[StartRunUseCase, Depends(get_start_run)]
ResumeRunDep = Annotated[ResumeRunUseCase, Depends(get_resume_run)]
ApproveBudgetDep = Annotated[ApproveBudgetUseCase, Depends(get_approve_budget)]
QueryRunDep = Annotated[QueryRunUseCase, Depends(get_query_run)]
