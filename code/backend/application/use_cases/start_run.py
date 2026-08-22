"""Caso de uso: recebe um briefing e roda o squad até o fim, até uma pausa
(interrupt/escalate) ou até o backlog esgotar. Orquestra, não decide regra de
negócio - a regra vive no grafo e nos agentes.

Separado em `create` (rápido: só grava o Run) e `execute` (lento: roda o
grafo) para que a API possa responder o run_id imediatamente e rodar o grafo
em background - ver interfaces/http/routers/runs.py."""
from __future__ import annotations

import logging
import uuid

from ... import config
from ...domain.entities.run import Run
from ...domain.enums import RunStatus
from ...pipeline.checkpointer import build_checkpointer
from ...pipeline.graph import build_graph
from ...pipeline.state import initial_state
from .history import build_history_context

_TERMINAL_STATUS = {"done": RunStatus.DONE, "awaiting_human": RunStatus.AWAITING_HUMAN, "failed": RunStatus.FAILED}

logger = logging.getLogger(__name__)


class StartRun:
    def __init__(self, container):
        self._container = container

    async def create(self, raw_briefing: str, budget_usd: float | None = None) -> str:
        run_id = str(uuid.uuid4())
        run = Run(
            id=run_id,
            raw_briefing=raw_briefing,
            status=RunStatus.PENDING,
            budget_usd=budget_usd or config.BUDGET_PER_RUN_USD,
        )
        await self._container.run_repo.save(run)
        return run_id

    async def execute(self, run_id: str) -> dict:
        run = await self._container.run_repo.get(run_id)
        run.status = RunStatus.RUNNING
        await self._container.run_repo.save(run)

        try:
            brief_history = await build_history_context(self._container)
            state = initial_state(run_id, run.raw_briefing, brief_history)

            checkpointer = build_checkpointer()
            graph = build_graph(self._container, checkpointer=checkpointer)

            final_state = await graph.ainvoke(
                state, config={"configurable": {"thread_id": run_id}, "recursion_limit": 100}
            )
        except Exception as exc:
            # Roda como fire-and-forget background task (ver interfaces/http/routers/runs.py) -
            # sem isso, uma exceção inesperada some no handler padrão do asyncio e o run
            # fica "running" para sempre, sem ninguém saber o que aconteceu.
            logger.exception("StartRun.execute falhou para run_id=%s", run_id)
            run.status = RunStatus.FAILED
            run.error = str(exc)
            await self._container.run_repo.save(run)
            return {"run_id": run_id, "status": run.status.value, "error": run.error}

        run.status = _TERMINAL_STATUS.get(final_state.get("status"), RunStatus.RUNNING)
        run.total_cost_usd = await self._container.token_meter.spent_usd(run_id)
        await self._container.run_repo.save(run)

        return {"run_id": run_id, "status": run.status.value, "state": final_state}
