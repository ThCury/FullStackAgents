"""Port do LLM. Nenhuma camada de domínio/aplicação/agente conhece o SDK da
Anthropic diretamente - todas falam com este Protocol. Só
`infrastructure/llm/anthropic_adapter.py` conhece o SDK de verdade."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..value_objects.token_usage import TokenUsage


@dataclass
class LLMRequest:
    run_id: str
    agent: str
    model: str
    system: str
    messages: list[dict[str, Any]]
    tools: list[dict] = field(default_factory=list)
    max_tokens: int = 4096
    effort: str = "medium"  # low | medium | high | xhigh - dial de custo (ADR-05 / §8.4)
    cache_system: bool = True  # aplica cache_control no prefixo estável do system prompt


@dataclass
class LLMResponse:
    text: str
    tool_uses: list[Any]
    raw_content: list[Any]
    usage: TokenUsage
    stop_reason: str


class LLMPort(Protocol):
    async def complete(self, req: LLMRequest) -> LLMResponse: ...
