from __future__ import annotations

import json
from collections.abc import Iterator

from domain.models.llm_completed import LLMCompleted
from domain.models.llm_request import LLMRequest
from domain.models.llm_stream_event import LLMStreamEvent


class FakeStreamingLLM:
    provider = "fake"
    model = "fake-po-v1"

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        response = {
            "summary": f"Entendimento inicial: {request.prompt.strip()}",
            "requirements": [
                {
                    "id": "RF-001",
                    "description": "O sistema deve atender ao objetivo descrito no prompt.",
                    "priority": "must",
                }
            ],
            "user_stories": [
                {
                    "id": "US-001",
                    "title": "Atender ao objetivo principal",
                    "as_a": "usuário do produto",
                    "i_want": "utilizar a funcionalidade descrita no pedido",
                    "so_that": "eu possa alcançar o resultado esperado",
                    "acceptance_criteria": [
                        "O fluxo principal descrito no prompt está disponível."
                    ],
                    "priority": "must",
                }
            ],
            "assumptions": ["O detalhamento será refinado em incrementos posteriores."],
            "open_questions": [],
        }
        text = json.dumps(response, ensure_ascii=False)
        for index in range(0, len(text), 80):
            chunk = text[index : index + 80]
            yield LLMStreamEvent(type="delta", delta=chunk)
        yield LLMStreamEvent(
            type="completed",
            completed=LLMCompleted(
                provider_response_id="fake-response-1",
                input_tokens=max(1, len(request.prompt) // 4),
                output_tokens=max(1, len(text) // 4),
                cached_tokens=0,
                finish_reason="stop",
            ),
        )


class OpenAIStreamingLLM:
    provider = "openai"

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self.model = model

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        arguments: dict = {
            "model": request.model,
            "instructions": request.system_prompt,
            "input": request.prompt,
            "stream": True,
            "store": False,
        }
        if request.effort:
            arguments["reasoning"] = {"effort": request.effort}

        stream = self._client.responses.create(**arguments)
        for event in stream:
            if event.type == "response.output_text.delta":
                yield LLMStreamEvent(type="delta", delta=event.delta)
            elif event.type == "response.completed":
                response = event.response
                usage = getattr(response, "usage", None)
                yield LLMStreamEvent(
                    type="completed",
                    completed=LLMCompleted(
                        provider_response_id=getattr(response, "id", None),
                        input_tokens=getattr(usage, "input_tokens", None),
                        output_tokens=getattr(usage, "output_tokens", None),
                        cached_tokens=getattr(usage, "input_tokens_details", None)
                        and getattr(usage.input_tokens_details, "cached_tokens", None),
                        finish_reason=getattr(response, "status", None),
                    ),
                )


class GeminiStreamingLLM:
    provider = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai

        self._client = genai.Client(api_key=api_key)
        self.model = model

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=request.system_prompt,
            temperature=request.temperature,
            response_mime_type="application/json",
        )
        last_chunk = None
        for chunk in self._client.models.generate_content_stream(
            model=request.model,
            contents=request.prompt,
            config=config,
        ):
            last_chunk = chunk
            delta = getattr(chunk, "text", None)
            if delta:
                yield LLMStreamEvent(type="delta", delta=delta)

        usage = getattr(last_chunk, "usage_metadata", None)
        candidates = getattr(last_chunk, "candidates", None) or []
        finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
        yield LLMStreamEvent(
            type="completed",
            completed=LLMCompleted(
                provider_response_id=getattr(last_chunk, "response_id", None),
                input_tokens=getattr(usage, "prompt_token_count", None),
                output_tokens=getattr(usage, "candidates_token_count", None),
                cached_tokens=getattr(usage, "cached_content_token_count", None),
                finish_reason=str(finish_reason) if finish_reason is not None else None,
            ),
        )
