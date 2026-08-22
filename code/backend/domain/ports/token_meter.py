"""Port de controle de orçamento. `assert_within_budget` é chamado ANTES de
cada chamada ao LLM (ver infrastructure/llm/budgeted_llm.py) - é o que torna
o teto de USD por run/agente enforçado, e não só um número decorativo no
dashboard."""
from __future__ import annotations

from typing import Protocol

from ..value_objects.token_usage import TokenUsage


class TokenMeterPort(Protocol):
    async def assert_within_budget(self, run_id: str, agent: str) -> None:
        """Levanta domain.errors.BudgetExceeded se o run OU o agente já
        estourou o teto configurado."""
        ...

    async def record(self, run_id: str, agent: str, usage: TokenUsage, cost_usd: float) -> None: ...

    async def spent_usd(self, run_id: str, agent: str | None = None) -> float: ...
