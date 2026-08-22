"""Caso de uso: retoma um run pausado em `escalate` (interrupt()) com a
decisão humana. `decision={"action": "resume_dev"}` volta ao Dev; qualquer
outra coisa encerra o run como "failed" (ver pipeline/nodes/escalate.py)."""
from __future__ import annotations

import logging

from langgraph.types import Command

from ...domain.enums import RunStatus
from ...domain.errors import RunNotFound
from ...pipeline.checkpointer import build_checkpointer
from ...pipeline.graph import build_graph
from .start_run import _TERMINAL_STATUS

logger = logging.getLogger(__name__)


class ResumeRun:
    def __init__(self, container):
        self._container = container

    async def execute(self, run_id: str, decision: dict) -> dict:
        run = await self._container.run_repo.get(run_id)
        if run is None:
            raise RunNotFound(run_id)

        try:
            checkpointer = build_checkpointer()
            graph = build_graph(self._container, checkpointer=checkpointer)

            final_state = await graph.ainvoke(
                Command(resume=decision),
                config={"configurable": {"thread_id": run_id}, "recursion_limit": 100},
            )
        except Exception as exc:
            # mesmo motivo do try/except em StartRun.execute: isto roda como
            # fire-and-forget background task na API.
            logger.exception("ResumeRun.execute falhou para run_id=%s", run_id)
            run.status = RunStatus.FAILED
            run.error = str(exc)
            await self._container.run_repo.save(run)
            return {"run_id": run_id, "status": run.status.value, "error": run.error}

        run.status = _TERMINAL_STATUS.get(final_state.get("status"), RunStatus.RUNNING)
        run.total_cost_usd = await self._container.token_meter.spent_usd(run_id)
        await self._container.run_repo.save(run)

        return {"run_id": run_id, "status": run.status.value, "state": final_state}
