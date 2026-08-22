"""REST de runs - o que o futuro Squad Console (Fase 2, ainda não construído)
vai consumir. `POST /runs` responde imediatamente com o run_id (202) e roda o
grafo em background, porque uma execução completa envolve várias chamadas de
LLM em sequência e não deve bloquear a requisição HTTP."""
from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from ....application.use_cases.approve_budget import ApproveBudget
from ....application.use_cases.get_run_timeline import GetRunTimeline
from ....application.use_cases.resume_run import ResumeRun
from ....application.use_cases.start_run import StartRun
from ....domain.errors import RunNotFound

router = APIRouter(prefix="/runs", tags=["runs"])


class StartRunRequest(BaseModel):
    briefing: str
    budget_usd: float | None = None


class ApproveBudgetRequest(BaseModel):
    extra_budget_usd: float


class ResumeRunRequest(BaseModel):
    action: str = "resume_dev"


def _track(request: Request, coro) -> None:
    """Mantém referência forte à task enquanto ela roda - sem isso o asyncio
    pode coletar a task no meio da execução (armadilha conhecida do asyncio)."""
    task = asyncio.create_task(coro)
    request.app.state.background_tasks.add(task)
    task.add_done_callback(request.app.state.background_tasks.discard)


@router.post("", status_code=202)
async def start_run(payload: StartRunRequest, request: Request):
    container = request.app.state.container
    use_case = StartRun(container)
    run_id = await use_case.create(payload.briefing, budget_usd=payload.budget_usd)
    _track(request, use_case.execute(run_id))
    return {"run_id": run_id, "status": "queued"}


@router.get("/{run_id}")
async def get_run(run_id: str, request: Request):
    container = request.app.state.container
    try:
        return await GetRunTimeline(container).execute(run_id)
    except RunNotFound:
        raise HTTPException(status_code=404, detail="run não encontrado")


@router.post("/{run_id}/resume", status_code=202)
async def resume_run(run_id: str, payload: ResumeRunRequest, request: Request):
    container = request.app.state.container
    _track(request, ResumeRun(container).execute(run_id, decision={"action": payload.action}))
    return {"run_id": run_id, "status": "resuming"}


@router.post("/{run_id}/approve-budget", status_code=202)
async def approve_budget(run_id: str, payload: ApproveBudgetRequest, request: Request):
    container = request.app.state.container
    _track(request, ApproveBudget(container).execute(run_id, payload.extra_budget_usd))
    return {"run_id": run_id, "status": "resuming"}
