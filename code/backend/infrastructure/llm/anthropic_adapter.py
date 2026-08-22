"""Único ponto do sistema que conhece o SDK `anthropic` diretamente (DIP).
Implementa LLMPort com:
  - loop agentic manual (sem a tool runner beta - evita dependência beta)
  - prompt caching: prefixo estável do system prompt marcado com
    cache_control ephemeral (§8.4 - conteúdo estável primeiro)
  - dial de custo via output_config.effort, por chamada

Não decide orçamento (isso é o BudgetedLLM, um decorator - ver budgeted_llm.py).
"""
from __future__ import annotations

import anthropic

from ...domain.ports.llm import LLMPort, LLMRequest, LLMResponse
from ...domain.value_objects.token_usage import TokenUsage


class AnthropicAdapter(LLMPort):
    def __init__(self, api_key: str):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    def _build_system(self, system: str, cache_system: bool) -> str | list[dict]:
        if not cache_system:
            return system
        # Prefixo estável primeiro, com breakpoint de cache. O conteúdo
        # volátil (o brief da rodada, o estado da story) vive em `messages`,
        # nunca aqui - senão o cache invalida a cada chamada.
        return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

    async def complete(self, req: LLMRequest) -> LLMResponse:
        # Streaming (não apenas create()) é obrigatório aqui: com max_tokens alto
        # (Dev/PO passam de 16k), o SDK recusa non-streaming com ValueError
        # ("Streaming is required for operations that may take longer than 10
        # minutes") - get_final_message() dá a mesma resposta acumulada, sem
        # precisar tratar eventos um a um.
        async with self._client.messages.stream(
            model=req.model,
            max_tokens=req.max_tokens,
            system=self._build_system(req.system, req.cache_system),
            messages=req.messages,
            tools=req.tools,
            output_config={"effort": req.effort},
        ) as stream:
            response = await stream.get_final_message()
        usage = TokenUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            cache_creation_input_tokens=getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0) or 0,
        )
        texts = [b.text for b in response.content if b.type == "text"]
        tool_uses = [b for b in response.content if b.type == "tool_use"]
        return LLMResponse(
            text="\n".join(texts),
            tool_uses=tool_uses,
            raw_content=response.content,
            usage=usage,
            stop_reason=response.stop_reason,
        )
