from collections.abc import Iterator
from typing import Protocol

from domain.models.llm_request import LLMRequest
from domain.models.llm_stream_event import LLMStreamEvent


class StreamingLLM(Protocol):
    provider: str
    model: str

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]: ...
