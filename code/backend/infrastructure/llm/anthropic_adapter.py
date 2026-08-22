"""Adapter da Anthropic — a única classe do sistema que conhece o provider.

Por que o SDK direto e não `ChatAnthropic` do LangChain
------------------------------------------------------
Usamos LangGraph para orquestração (ADR-03), mas as chamadas passam pelo SDK
`anthropic` porque precisamos de três coisas com controle exato:

  1. `output_config.effort` — o dial de custo por agente (ADR-05). Preferimos
     baixar effort a trocar de modelo.
  2. Posicionamento do breakpoint de prompt caching. O ganho depende de o
     prefixo ser byte-a-byte estável; abstração no meio esconde invalidação.
  3. `count_tokens` do provider, para pré-medição honesta. Nunca `tiktoken` —
     é outro tokenizer e devolve número errado.

A `LLMPort` esconde essa escolha: nenhum agente sabe qual provider existe. Se um
dia `ChatAnthropic` repassar esses parâmetros, troca-se aqui e só aqui.

Notas de API que já custaram tempo a alguém:
  - `claude-opus-5` já vem com thinking ligado; `budget_tokens` foi REMOVIDO e
    retorna 400. Use `thinking={"type": "adaptive"}` e controle por `effort`.
  - `effort` vai dentro de `output_config`, não no topo do request.
  - Streaming é obrigatório para `max_tokens` grande, senão dá timeout de HTTP.
"""

from __future__ import annotations

import json
import time
from typing import Any

from anthropic import AsyncAnthropic

from domain.ports.llm import LLMRequest, LLMResponse
from domain.value_objects import TokenUsage

DEFAULT_MODEL = "claude-opus-5"

# Acima disso o SDK exige streaming para não estourar o timeout de HTTP.
_STREAMING_THRESHOLD = 8_000


class AnthropicAdapter:
    def __init__(
        self,
        client: AsyncAnthropic | None = None,
        model: str = DEFAULT_MODEL,
    ) -> None:
        self._client = client or AsyncAnthropic()
        self._model = model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        params = self._build_params(request)
        started = time.perf_counter()

        if request.max_tokens >= _STREAMING_THRESHOLD:
            async with self._client.messages.stream(**params) as stream:
                message = await stream.get_final_message()
        else:
            message = await self._client.messages.create(**params)

        latency_ms = int((time.perf_counter() - started) * 1000)
        raw_text = _first_text_block(message)

        return LLMResponse(
            data=json.loads(raw_text),
            raw_text=raw_text,
            model=message.model,
            usage=_to_usage(message.usage),
            latency_ms=latency_ms,
            call_id=message.id,
        )

    async def count_tokens(self, request: LLMRequest) -> int:
        """Pré-medição pelo tokenizer do provider."""
        # Para CONTAR, o `cache_control` do bloco e irrelevante — manda a string
        # crua e evita divergencia de tipo com o SDK.
        result = await self._client.messages.count_tokens(
            model=self._model,
            system=request.system,
            messages=[{"role": "user", "content": request.user}],
        )
        return int(result.input_tokens)

    # ------------------------------------------------------------------ interno
    def _build_params(self, request: LLMRequest) -> dict[str, Any]:
        return {
            "model": self._model,
            "max_tokens": request.max_tokens,
            "system": self._system_blocks(request),
            "messages": [{"role": "user", "content": request.user}],
            # Thinking adaptativo: sem `budget_tokens`, que foi removido.
            "thinking": {"type": "adaptive"},
            "output_config": {
                "effort": request.effort.value,
                "format": {
                    "type": "json_schema",
                    "schema": request.output_schema,
                },
            },
        }

    def _system_blocks(self, request: LLMRequest) -> list[dict[str, Any]]:
        """O system prompt é o prefixo estável — logo, o breakpoint de cache.

        Nada volátil pode entrar aqui: um timestamp ou id invalida o cache
        silenciosamente e o custo triplica sem ninguém perceber. Confira pelo
        `cache_read_tokens` no painel de tokens do Console.
        """
        block: dict[str, Any] = {"type": "text", "text": request.system}
        if request.cache_system:
            block["cache_control"] = {"type": "ephemeral"}
        return [block]


def _first_text_block(message: Any) -> str:
    for block in message.content:
        if getattr(block, "type", None) == "text":
            return str(block.text)
    raise ValueError(f"resposta sem bloco de texto (stop_reason={message.stop_reason})")


def _to_usage(usage: Any) -> TokenUsage:
    return TokenUsage(
        input_tokens=getattr(usage, "input_tokens", 0) or 0,
        output_tokens=getattr(usage, "output_tokens", 0) or 0,
        cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
        cache_write_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
    )
