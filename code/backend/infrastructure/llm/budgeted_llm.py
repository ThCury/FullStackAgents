"""BudgetedLLM — decorator de `LLMPort` que aplica orçamento de tokens.

OCP na prática (§8.3): adiciona controle de custo sem tocar em uma linha do
`AnthropicAdapter` nem de nenhum agente. Compõe com qualquer outra
implementação da port, inclusive o `FakeLLM`.

Empilhamento típico, montado em `factory/container.py`:

    BudgetedLLM(AnthropicAdapter(...), meter)

Por que não colocar o controle dentro do adapter: aí `FakeLLM` não teria
orçamento, e teste de estouro de orçamento passaria a exigir rede.
"""

from __future__ import annotations

from domain.ports.llm import LLMPort, LLMRequest, LLMResponse
from domain.ports.observability import TokenMeterPort


class BudgetedLLM:
    def __init__(self, inner: LLMPort, meter: TokenMeterPort) -> None:
        self._inner = inner
        self._meter = meter

    async def complete(self, request: LLMRequest) -> LLMResponse:
        planned = await self._inner.count_tokens(request)
        # Levanta `BudgetExceeded`. O grafo captura e roteia para `escalate`,
        # que pausa em `interrupt()` e pede aprovação humana — não mata o run.
        await self._meter.assert_within_budget(request.run_id, request.agent, planned)

        response = await self._inner.complete(request)
        await self._meter.record(request.run_id, request.agent, response.usage)
        return response

    async def count_tokens(self, request: LLMRequest) -> int:
        return await self._inner.count_tokens(request)
