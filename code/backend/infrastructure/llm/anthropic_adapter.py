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

from domain.errors import LLMRefused, LLMResponseInvalid, LLMResponseTruncated
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
        api_key: str | None = None,
    ) -> None:
        # A chave vem das Settings, não do ambiente: quando ela está no arquivo
        # `.env`, o pydantic-settings a carrega no objeto de config mas não a
        # exporta para `os.environ`, e o `AsyncAnthropic()` sem argumento não a
        # encontraria. `api_key=None` mantém o comportamento padrão do SDK
        # (procura `ANTHROPIC_API_KEY` no ambiente) para quem exporta a variável.
        self._client = client or AsyncAnthropic(api_key=api_key)
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

        # Checar ANTES de tentar parsear. Sem isto, uma resposta truncada virava
        # `JSONDecodeError: Unterminated string at char 21534` — erro que não diz
        # nada a quem está diagnosticando, e que já custou um run de 16 minutos.
        _assert_usable(message, request)

        raw_text = _first_text_block(message)

        return LLMResponse(
            data=_parse_json(raw_text, request),
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
                    "schema": _strict_schema(request.output_schema),
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


def _assert_usable(message: Any, request: LLMRequest) -> None:
    """Recusa resposta inutilizável com diagnóstico acionável.

    `stop_reason` precisa ser inspecionado antes do conteúdo:

    - `max_tokens` — a resposta foi **cortada**. Em `claude-opus-5` o thinking
      adaptativo é ligado por padrão e consome o MESMO `max_tokens` da saída, então
      um teto que parece folgado para o JSON pode ser todo consumido pelo
      raciocínio. Aumentar `max_tokens` não encarece: a cobrança é por token
      gerado, não pelo teto.
    - `refusal` — classificador de segurança recusou. HTTP 200, conteúdo vazio.
    """
    stop_reason = getattr(message, "stop_reason", None)

    if stop_reason == "max_tokens":
        raise LLMResponseTruncated(
            agent=request.agent.value,
            max_tokens=request.max_tokens,
            output_tokens=getattr(message.usage, "output_tokens", 0),
        )

    if stop_reason == "refusal":
        details = getattr(message, "stop_details", None)
        raise LLMRefused(
            agent=request.agent.value,
            category=getattr(details, "category", None) or "desconhecida",
        )


def _parse_json(raw_text: str, request: LLMRequest) -> dict[str, Any]:
    """Parse com erro legível.

    Com `stop_reason` já validado, um JSON inválido aqui é falha real do modelo,
    não truncamento — e o trecho do texto ajuda a diagnosticar qual.
    """
    try:
        parsed: dict[str, Any] = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise LLMResponseInvalid(
            agent=request.agent.value, reason=str(exc), excerpt=raw_text[-300:]
        ) from exc
    return parsed


def _strict_schema(schema: Any) -> Any:
    """Adapta o JSON Schema do Pydantic ao que o structured output exige.

    A API recusa o schema com HTTP 400 se algum objeto não declarar
    `additionalProperties: false` explicitamente:

        output_config.format.schema: For 'object' type,
        'additionalProperties' must be explicitly set to false

    O `model_config = ConfigDict(extra="forbid")` resolve para o modelo de
    topo, mas **não** para os modelos aninhados que ele referencia em `$defs`
    (`Pain`, `Constraint`, `Actor`…). Marcar `extra="forbid"` em toda entidade
    do domínio só para agradar um provider seria acoplamento na direção errada —
    então a normalização mora aqui, no adapter, que é quem conhece a exigência.

    Percorre recursivamente `properties`, `$defs`, `items`, `anyOf`/`oneOf`/
    `allOf` e `additionalProperties` aninhado.
    """
    if isinstance(schema, list):
        return [_strict_schema(item) for item in schema]
    if not isinstance(schema, dict):
        return schema

    out = {key: _strict_schema(value) for key, value in schema.items()}
    if out.get("type") == "object":
        out["additionalProperties"] = False
    return out


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
