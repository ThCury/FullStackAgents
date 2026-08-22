"""TokenMeterPort real: grava cada chamada em `token_ledger` e aplica dois
tetos - por run (lido do próprio documento `runs`, para que ApproveBudget
consiga estender o teto de um run específico sem mexer em config global) e
por agente (fixo via config, para o Dev não conseguir sozinho estourar o teto
do run sem deixar margem para os demais)."""
from __future__ import annotations

from datetime import datetime, timezone

from motor.motor_asyncio import AsyncIOMotorDatabase

from ... import config
from ...domain.errors import BudgetExceeded
from ...domain.value_objects.token_usage import TokenUsage


class MongoTokenMeter:
    def __init__(self, db: AsyncIOMotorDatabase):
        self._col = db["token_ledger"]
        self._runs_col = db["runs"]

    async def spent_usd(self, run_id: str, agent: str | None = None) -> float:
        match: dict = {"run_id": run_id}
        if agent:
            match["agent"] = agent
        cursor = self._col.aggregate([
            {"$match": match},
            {"$group": {"_id": None, "total": {"$sum": "$cost_usd"}}},
        ])
        async for doc in cursor:
            return doc["total"]
        return 0.0

    async def assert_within_budget(self, run_id: str, agent: str) -> None:
        run_doc = await self._runs_col.find_one({"_id": run_id}, {"budget_usd": 1})
        budget_per_run = run_doc["budget_usd"] if run_doc and run_doc.get("budget_usd") else config.BUDGET_PER_RUN_USD

        run_spent = await self.spent_usd(run_id)
        if run_spent >= budget_per_run:
            raise BudgetExceeded("run", run_spent, budget_per_run)

        agent_spent = await self.spent_usd(run_id, agent)
        if agent_spent >= config.BUDGET_PER_AGENT_USD:
            raise BudgetExceeded(f"agent:{agent}", agent_spent, config.BUDGET_PER_AGENT_USD)

    async def record(self, run_id: str, agent: str, usage: TokenUsage, cost_usd: float) -> None:
        await self._col.insert_one({
            "run_id": run_id,
            "agent": agent,
            "usage": usage.to_dict(),
            "cost_usd": cost_usd,
            "created_at": datetime.now(timezone.utc),
        })
