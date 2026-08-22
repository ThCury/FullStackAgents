"""Caso de uso: humano aprova orçamento extra para um run pausado por
BudgetExceeded (§8.3) - estende o teto daquele run específico e retoma."""
from __future__ import annotations

from ...domain.errors import RunNotFound
from .resume_run import ResumeRun


class ApproveBudget:
    def __init__(self, container):
        self._container = container

    async def execute(self, run_id: str, extra_budget_usd: float) -> dict:
        run = await self._container.run_repo.get(run_id)
        if run is None:
            raise RunNotFound(run_id)

        run.budget_usd += extra_budget_usd
        await self._container.run_repo.save(run)

        return await ResumeRun(self._container).execute(run_id, decision={"action": "resume_dev"})
