"""TokenMeter em memória, com ledger append-only opcional.

Escopos (§8.3): por chamada, por agente, por run. `assert_within_budget`
levanta `BudgetExceeded`; o grafo roteia para `escalate`, que pausa em
`interrupt()` e pede aprovação humana. Estourar orçamento não mata o run —
falha graciosa e visível no Console.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict

from domain.enums import AgentRole
from domain.errors import BudgetExceeded
from domain.ports.observability import EventBusPort, SquadEvent
from domain.value_objects import BudgetPolicy, BudgetSnapshot, TokenUsage


class InMemoryTokenMeter:
    """Suficiente para um run: o volume é de centenas de chamadas.

    Se um dia o Console precisar de histórico entre reinícios, troque por uma
    implementação Mongo sobre a coleção `token_ledger` — a port não muda.
    """

    def __init__(
        self,
        policy: BudgetPolicy | None = None,
        events: EventBusPort | None = None,
    ) -> None:
        self._policy = policy or BudgetPolicy()
        self._events = events
        self._lock = asyncio.Lock()
        self._by_agent: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._totals: dict[str, int] = defaultdict(int)
        self._cost: dict[str, float] = defaultdict(float)
        self._extra: dict[str, int] = defaultdict(int)
        self._extensions: dict[str, int] = defaultdict(int)

    async def assert_within_budget(self, run_id: str, agent: AgentRole, planned: int) -> None:
        async with self._lock:
            if planned > self._policy.per_call:
                raise BudgetExceeded(run_id, f"call:{agent}", planned, self._policy.per_call)

            # A extensão aprovada por humano alivia os dois tetos, não só o do
            # run. Um teto por agente é guarda contra um papel desandar; se o
            # humano acabou de olhar o caso e liberou mais orçamento, manter o
            # cap por agente bloqueando faria a aprovação não surtir efeito —
            # e o run voltaria para `escalate` em loop.
            extra = self._extra[run_id]

            agent_spent = self._by_agent[run_id][agent] + planned
            agent_limit = self._policy.per_agent + extra
            if agent_spent > agent_limit:
                raise BudgetExceeded(run_id, f"agent:{agent}", agent_spent, agent_limit)

            run_limit = self._policy.per_run + extra
            run_spent = self._totals[run_id] + planned
            if run_spent > run_limit:
                raise BudgetExceeded(run_id, "run", run_spent, run_limit)

    async def record(self, run_id: str, agent: AgentRole, usage: TokenUsage) -> None:
        async with self._lock:
            self._by_agent[run_id][agent] += usage.total
            self._totals[run_id] += usage.total
            self._cost[run_id] += usage.cost_usd
            snapshot = self._snapshot_unlocked(run_id)

        if self._events is not None:
            await self._events.publish(
                SquadEvent(
                    run_id=run_id,
                    type="budget",
                    payload=snapshot.model_dump(mode="json"),
                )
            )

    async def snapshot(self, run_id: str) -> BudgetSnapshot:
        async with self._lock:
            return self._snapshot_unlocked(run_id)

    async def approve_extension(self, run_id: str, extra_tokens: int) -> BudgetSnapshot:
        """Decisão humana vinda do `interrupt()`. Fica registrada em
        `extensions_approved` — aumentar orçamento é decisão auditável."""
        async with self._lock:
            self._extra[run_id] += extra_tokens
            self._extensions[run_id] += 1
            return self._snapshot_unlocked(run_id)

    def _snapshot_unlocked(self, run_id: str) -> BudgetSnapshot:
        policy = self._policy.model_copy(
            update={"per_run": self._policy.per_run + self._extra[run_id]}
        )
        return BudgetSnapshot(
            policy=policy,
            spent_by_agent=dict(self._by_agent[run_id]),
            total_spent=self._totals[run_id],
            total_cost_usd=round(self._cost[run_id], 6),
            extensions_approved=self._extensions[run_id],
        )
