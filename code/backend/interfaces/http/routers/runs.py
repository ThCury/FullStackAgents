"""Endpoints do ciclo de vida do run + o stream SSE que alimenta o Console."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from domain.enums import AgentRole
from domain.errors import NoCheckpointAvailable, RunNotFound, RunNotRetryable
from interfaces.http.deps import (
    ApproveBudgetDep,
    ContainerDep,
    QueryRunDep,
    ResumeRunDep,
    RetryRunDep,
    StartRunDep,
)

router = APIRouter(prefix="/runs", tags=["runs"])


class StartRunRequest(BaseModel):
    briefing: str = Field(min_length=20, description="Briefing cru do cliente")


class ResumeRunRequest(BaseModel):
    resolution: Literal["retry", "skip", "finish"]


class ApproveBudgetRequest(BaseModel):
    extra_tokens: int = Field(gt=0, le=5_000_000)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def start_run(payload: StartRunRequest, use_case: StartRunDep) -> dict[str, Any]:
    """Dispara o squad. Devolve 202 na hora — o run leva minutos e o Console
    acompanha por `/runs/{id}/stream`."""
    run = await use_case.execute(payload.briefing)
    return run.model_dump(mode="json")


@router.get("")
async def list_runs(
    use_case: QueryRunDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[dict[str, Any]]:
    return [r.model_dump(mode="json") for r in await use_case.list_runs(limit)]


@router.get("/{run_id}")
async def get_run(run_id: str, use_case: QueryRunDep) -> dict[str, Any]:
    try:
        return (await use_case.get_run(run_id)).model_dump(mode="json")
    except RunNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{run_id}/timeline")
async def get_timeline(
    run_id: str,
    use_case: QueryRunDep,
    since_seq: Annotated[int, Query(ge=-1)] = -1,
    agent: AgentRole | None = None,
) -> list[dict[str, Any]]:
    """A trilha de auditoria. `since_seq` busca só o delta na reconexão."""
    return await use_case.timeline(run_id, since_seq=since_seq, agent=agent)


@router.get("/{run_id}/calls/{call_id}")
async def get_llm_call(run_id: str, call_id: str, use_case: QueryRunDep) -> dict[str, Any]:
    """Prompt e resposta crus — o Inspector do Console.

    É o segundo nível da auditoria (§8): o avaliador vê o handoff de negócio e,
    ao lado, exatamente o prompt que o produziu.
    """
    call = await use_case.llm_call(call_id)
    if call is None or call.get("run_id") != run_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"chamada {call_id} não encontrada")
    return call


@router.get("/{run_id}/deliverables")
async def get_deliverables(run_id: str, use_case: QueryRunDep) -> dict[str, Any]:
    """Os 5 entregáveis da Trilha B em um payload."""
    return await use_case.deliverables(run_id)


@router.get("/{run_id}/metrics")
async def get_metrics(run_id: str, use_case: QueryRunDep) -> dict[str, Any]:
    return await use_case.metrics(run_id)


@router.post("/{run_id}/resume", status_code=status.HTTP_202_ACCEPTED)
async def resume_run(
    run_id: str, payload: ResumeRunRequest, use_case: ResumeRunDep
) -> dict[str, Any]:
    """Retoma um run pausado em `interrupt()` com a decisão humana."""
    try:
        run = await use_case.execute(run_id, payload.resolution)
    except RunNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    return run.model_dump(mode="json")


@router.post("/{run_id}/retry", status_code=status.HTTP_202_ACCEPTED)
async def retry_run(run_id: str, use_case: RetryRunDep) -> dict[str, Any]:
    """Retoma um run que FALHOU, do último nó concluído.

    Não é o mesmo que `/resume`: aquele responde a um `interrupt()` (pausa
    proposital esperando decisão humana); este recupera de falha (estouro de
    `max_tokens`, rate limit, queda de rede).

    O que já foi feito não é refeito: story aceita continua aceita, código
    escrito continua escrito, token gasto não é gasto de novo.
    """
    try:
        run = await use_case.execute(run_id)
    except RunNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except RunNotRetryable as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except NoCheckpointAvailable as exc:
        # 409, não 404: o run existe, mas não há estado para retomar.
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return run.model_dump(mode="json")


@router.get("/{run_id}/resumable")
async def is_resumable(run_id: str, use_case: RetryRunDep) -> dict[str, Any]:
    """O run pode ser retomado?

    O Console usa isto para só oferecer o botão quando ele funciona — melhor que
    deixar o usuário clicar e tomar um 409.
    """
    return {"run_id": run_id, "resumable": await use_case.has_checkpoint(run_id)}


@router.post("/{run_id}/budget")
async def approve_budget(
    run_id: str, payload: ApproveBudgetRequest, use_case: ApproveBudgetDep
) -> dict[str, Any]:
    try:
        return await use_case.execute(run_id, payload.extra_tokens)
    except RunNotFound as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc


@router.get("/{run_id}/stream")
async def stream_run(run_id: str, request: Request, container: ContainerDep) -> EventSourceResponse:
    """SSE: a orquestração ao vivo — o entregável mais importante da trilha.

    Escolhemos SSE e não WebSocket porque o fluxo é unidirecional (servidor →
    Console), reconecta sozinho no browser e atravessa proxy sem configuração
    especial. Não há comando indo pelo canal; ação do usuário usa os endpoints
    POST acima.

    O histórico durável NÃO vem daqui — vem de `/timeline`. Este canal é só
    tempo real: se o cliente reconectar, ele busca o delta por `since_seq` e
    volta a ouvir.
    """
    subscription = container.events.subscribe(run_id)

    async def publisher() -> AsyncIterator[dict[str, str]]:
        try:
            async for event in subscription:
                if await request.is_disconnected():
                    break
                yield {
                    "event": event.type,
                    "data": json.dumps(event.payload, ensure_ascii=False, default=str),
                }
        finally:
            await subscription.close()

    return EventSourceResponse(publisher())
