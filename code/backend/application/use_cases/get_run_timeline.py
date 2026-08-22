"""Caso de uso: lê a trilha completa de um run - é o que a API (e futuramente
o Console) expõe para o avaliador enxergar o squad trabalhando."""
from __future__ import annotations

from ...domain.errors import RunNotFound


class GetRunTimeline:
    def __init__(self, container):
        self._container = container

    async def execute(self, run_id: str) -> dict:
        run = await self._container.run_repo.get(run_id)
        if run is None:
            raise RunNotFound(run_id)

        messages = await self._container.message_repo.list_by_run(run_id)
        stories = await self._container.story_repo.list_by_run(run_id)
        adrs = await self._container.adr_repo.list_by_run(run_id)
        test_reports = await self._container.test_report_repo.list_by_run(run_id)
        spent_usd = await self._container.token_meter.spent_usd(run_id)

        return {
            "run": run.to_dict(),
            "spent_usd": spent_usd,
            "messages": [m.to_dict() for m in messages],
            "backlog": [s.to_dict() for s in stories],
            "adrs": [a.to_dict() for a in adrs],
            "test_reports": [t.to_dict() for t in test_reports],
        }
