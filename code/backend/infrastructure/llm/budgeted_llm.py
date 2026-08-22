"""Decorator OCP sobre LLMPort: aplica orçamento sem o adapter saber que
orçamento existe (§8.3). Checa ANTES de disparar a chamada e registra o gasto
real depois - o roteador do grafo trata BudgetExceeded mandando o run para
`escalate` (interrupt humano), não deixando o run simplesmente falhar."""
from __future__ import annotations

from ... import config
from ...domain.ports.llm import LLMPort, LLMRequest, LLMResponse
from ...domain.ports.token_meter import TokenMeterPort


class BudgetedLLM(LLMPort):
    def __init__(self, inner: LLMPort, meter: TokenMeterPort):
        self._inner = inner
        self._meter = meter

    async def complete(self, req: LLMRequest) -> LLMResponse:
        await self._meter.assert_within_budget(req.run_id, req.agent)
        res = await self._inner.complete(req)
        cost = res.usage.cost_usd(config.PRICE_INPUT_PER_MTOK, config.PRICE_OUTPUT_PER_MTOK)
        await self._meter.record(req.run_id, req.agent, res.usage, cost)
        return res
