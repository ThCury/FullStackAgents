"""Consultas de leitura para o Console.

Separadas dos casos de uso de escrita de propósito: são o que alimenta a
auditoria e não têm efeito colateral nenhum. Isso mantém óbvio que abrir a
timeline não muda o estado do run.
"""

from __future__ import annotations

from typing import Any

from domain.entities.run import Run
from domain.enums import AgentRole
from domain.errors import RunNotFound
from domain.ports.observability import TokenMeterPort
from domain.ports.repositories import (
    AdrRepository,
    ArtifactRepository,
    LlmCallRepository,
    MessageRepository,
    RunRepository,
    StoryRepository,
    TestReportRepository,
)


class QueryRunUseCase:
    def __init__(
        self,
        runs: RunRepository,
        messages: MessageRepository,
        llm_calls: LlmCallRepository,
        stories: StoryRepository,
        artifacts: ArtifactRepository,
        adrs: AdrRepository,
        reports: TestReportRepository,
        meter: TokenMeterPort,
    ) -> None:
        self._runs = runs
        self._messages = messages
        self._llm_calls = llm_calls
        self._stories = stories
        self._artifacts = artifacts
        self._adrs = adrs
        self._reports = reports
        self._meter = meter

    async def get_run(self, run_id: str) -> Run:
        run = await self._runs.get(run_id)
        if run is None:
            raise RunNotFound(run_id)
        return run

    async def list_runs(self, limit: int = 20) -> list[Run]:
        return await self._runs.list_recent(limit)

    async def timeline(
        self, run_id: str, since_seq: int = -1, agent: AgentRole | None = None
    ) -> list[dict[str, Any]]:
        """A trilha de auditoria. `since_seq` permite ao Console buscar só o
        delta ao reconectar o SSE, em vez de recarregar o run inteiro."""
        messages = (
            await self._messages.list_by_agent(run_id, agent)
            if agent
            else await self._messages.list_by_run(run_id, since_seq)
        )
        return [m.model_dump(mode="json") for m in messages]

    async def llm_call(self, call_id: str) -> dict[str, Any] | None:
        """Prompt e resposta crus — o painel Inspector do Console."""
        call = await self._llm_calls.get(call_id)
        return call.model_dump(mode="json") if call else None

    async def deliverables(self, run_id: str) -> dict[str, Any]:
        """Os 5 entregáveis do enunciado, em um payload só.

        Deliberadamente uma chamada e não cinco: é o que o avaliador abre, e
        cinco requisições em cascata deixariam a tela montando aos pedaços.
        """
        stories = await self._stories.list_by_run(run_id)
        adrs = await self._adrs.list_by_run(run_id)
        reports = await self._reports.list_by_run(run_id)
        artifacts = await self._artifacts.list_by_run(run_id)
        messages = await self._messages.list_by_run(run_id)

        return {
            "backlog": [s.model_dump(mode="json") for s in stories],
            "adrs": [a.model_dump(mode="json") for a in adrs],
            "test_reports": [r.model_dump(mode="json") for r in reports],
            "artifacts": [a.model_dump(mode="json") for a in artifacts],
            "message_count": len(messages),
        }

    async def metrics(self, run_id: str) -> dict[str, Any]:
        """Painel de tokens e custo.

        `cache_hit_rate` é a métrica que denuncia prompt caching quebrado: se
        cair para zero entre runs, algum prefixo virou volátil (§8.4).
        """
        snapshot = await self._meter.snapshot(run_id)
        calls = await self._llm_calls.list_by_run(run_id)
        hits = sum(1 for c in calls if c.cache_hit)

        return {
            "budget": snapshot.model_dump(mode="json"),
            "calls_total": len(calls),
            "cache_hits": hits,
            "cache_hit_rate": round(hits / len(calls), 3) if calls else 0.0,
            "latency_ms_avg": (
                round(sum(c.latency_ms for c in calls) / len(calls)) if calls else 0
            ),
            "by_agent": {
                role.value: snapshot.spent_by_agent.get(role.value, 0) for role in AgentRole
            },
        }
