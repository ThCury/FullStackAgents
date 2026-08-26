from collections.abc import Iterator
from typing import Protocol

from domain.models.llm_request import LLMRequest
from domain.models.llm_stream_event import LLMStreamEvent


class StreamingLLM(Protocol):
    """Uma iteração de conversa. O loop de ferramentas vive no agente, não aqui:
    o provider apenas reporta `tool_calls` no evento `completed`."""

    provider: str
    model: str

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]: ...
