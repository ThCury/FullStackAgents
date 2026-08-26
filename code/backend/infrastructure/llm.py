from __future__ import annotations

import json
from collections.abc import Iterator

from domain.models.llm_completed import LLMCompleted
from domain.models.llm_message import LLMMessage
from domain.models.llm_request import LLMRequest
from domain.models.llm_stream_event import LLMStreamEvent
from domain.models.product_backlog import REJECTION_MESSAGE
from domain.models.tool_call import ToolCall


class FakeStreamingLLM:
    """Simula o loop de ferramentas sem rede.

    A decisão do que responder vem de `request.role` e do tamanho do histórico —
    nunca de um trecho do system prompt, para que reescrever um prompt não mude
    silenciosamente o comportamento dos testes.
    """

    provider = "fake"
    model = "fake-v1"

    def __init__(self, too_complex: bool = False) -> None:
        self._too_complex = too_complex

    def stream(self, request: LLMRequest) -> Iterator[LLMStreamEvent]:
        text, tool_calls = self._respond(request)
        for index in range(0, len(text), 80):
            yield LLMStreamEvent(type="delta", delta=text[index : index + 80])
        yield LLMStreamEvent(
            type="completed",
            tool_calls=tool_calls,
            completed=LLMCompleted(
                provider_response_id="fake-response-1",
                input_tokens=max(1, len(request.prompt) // 4),
                output_tokens=max(1, len(text) // 4),
                cached_tokens=0,
                finish_reason="tool_calls" if tool_calls else "stop",
            ),
        )

    def _respond(self, request: LLMRequest) -> tuple[str, list[ToolCall]]:
        turns = len(request.history)
        if request.role == "DEVELOPER":
            return self._developer(turns)
        if request.role == "CODER":
            return self._coder(turns)
        return json.dumps(self._backlog(request), ensure_ascii=False), []

    def _developer(self, turns: int) -> tuple[str, list[ToolCall]]:
        if turns == 0:
            return "", [ToolCall(id="tc_1", name="list_files", arguments={})]
        if turns == 2:
            return "", [
                ToolCall(
                    id="tc_2",
                    name="read_file",
                    arguments={"path": "docs/agent-manifest.md"},
                )
            ]
        plan = {
            "summary": "Plano inicial de implementação a partir do template.",
            "architecture_decisions": [
                {
                    "decision": "Manter a divisão MVC do backend do template.",
                    "rationale": "O backlog não exige camadas novas.",
                    "alternative_rejected": "Criar uma camada de serviços paralela.",
                }
            ],
            "implementation_steps": [
                {
                    "id": "ST-001",
                    "description": "Documentar a decisão de arquitetura no manifesto.",
                    "story_ids": ["US-001"],
                    "files": ["docs/agent-manifest.md"],
                }
            ],
            "files_to_create": ["docs/nota-do-coder.md"],
            "files_to_change": ["docs/agent-manifest.md"],
            "files_to_delete": [],
            "new_dependencies": [],
            "validation_commands": ["docker compose run --rm frontend npm run build"],
            "risks": [],
            "open_questions": [],
        }
        return json.dumps(plan, ensure_ascii=False), []

    def _coder(self, turns: int) -> tuple[str, list[ToolCall]]:
        if turns == 0:
            return "", [
                ToolCall(
                    id="tc_3",
                    name="write_file",
                    arguments={
                        "path": "docs/nota-do-coder.md",
                        "content": "# Nota do coder\n\nArquivo criado pelo agente.\n",
                    },
                )
            ]
        report = {
            "summary": "Nota de implementação criada conforme o plano.",
            "changes": [{"path": "docs/nota-do-coder.md", "action": "create"}],
            "steps_completed": ["ST-001"],
            "steps_skipped": [],
            "validation_commands": ["docker compose run --rm frontend npm run build"],
            "risks": [],
            "open_questions": [],
        }
        return json.dumps(report, ensure_ascii=False), []

    def _backlog(self, request: LLMRequest) -> dict:
        if self._too_complex:
            return {
                "status": "TOO_COMPLEX",
                "summary": "O pedido abrange muitos fluxos independentes.",
                "estimated_stories": 18,
                "rejection": REJECTION_MESSAGE,
                "requirements": [],
                "user_stories": [],
                "assumptions": [],
                "open_questions": [],
            }
        return {
            "status": "ACCEPTED",
            "summary": f"Entendimento inicial: {request.prompt.strip()}",
            "estimated_stories": 1,
            "rejection": None,
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
                    "requirement_ids": ["RF-001"],
                    "acceptance_criteria": [
                        "Dado um usuário autenticado, quando ele abre o fluxo principal, "
                        "então a funcionalidade descrita está disponível."
                    ],
                    "priority": "must",
                }
            ],
            "assumptions": ["O detalhamento será refinado em incrementos posteriores."],
            "open_questions": [],
        }


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
            "input": self._input_for(request),
            "stream": True,
            "store": False,
        }
        if request.effort:
            arguments["reasoning"] = {"effort": request.effort}
        if request.tools:
            arguments["tools"] = [
                {
                    "type": "function",
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in request.tools
            ]

        for event in self._client.responses.create(**arguments):
            if event.type == "response.output_text.delta":
                yield LLMStreamEvent(type="delta", delta=event.delta)
            elif event.type == "response.completed":
                yield self._completed_event(event.response)

    def _completed_event(self, response) -> LLMStreamEvent:
        usage = getattr(response, "usage", None)
        details = getattr(usage, "input_tokens_details", None)
        return LLMStreamEvent(
            type="completed",
            tool_calls=self._tool_calls_from(response),
            completed=LLMCompleted(
                provider_response_id=getattr(response, "id", None),
                input_tokens=getattr(usage, "input_tokens", None),
                output_tokens=getattr(usage, "output_tokens", None),
                cached_tokens=getattr(details, "cached_tokens", None),
                finish_reason=getattr(response, "status", None),
            ),
        )

    @staticmethod
    def _tool_calls_from(response) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for item in getattr(response, "output", None) or []:
            if getattr(item, "type", None) != "function_call":
                continue
            raw = getattr(item, "arguments", "") or "{}"
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                parsed = {}
            calls.append(
                ToolCall(
                    id=getattr(item, "call_id", None) or getattr(item, "id", ""),
                    name=getattr(item, "name", ""),
                    arguments=parsed if isinstance(parsed, dict) else {},
                )
            )
        return calls

    @staticmethod
    def _input_for(request: LLMRequest) -> list[dict]:
        items: list[dict] = [{"role": "user", "content": request.prompt}]
        for message in request.history:
            items.extend(OpenAIStreamingLLM._items_for(message))
        return items

    @staticmethod
    def _items_for(message: LLMMessage) -> list[dict]:
        if message.role == "tool":
            return [
                {
                    "type": "function_call_output",
                    "call_id": result.call_id,
                    "output": result.content,
                }
                for result in message.tool_results
            ]
        items: list[dict] = []
        if message.content:
            items.append({"role": "assistant", "content": message.content})
        items.extend(
            {
                "type": "function_call",
                "call_id": call.id,
                "name": call.name,
                "arguments": json.dumps(call.arguments, ensure_ascii=False),
            }
            for call in message.tool_calls
        )
        return items


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
            **self._output_config(request, types),
        )
        last_chunk = None
        tool_calls: list[ToolCall] = []
        for chunk in self._client.models.generate_content_stream(
            model=request.model,
            contents=self._contents_for(request, types),
            config=config,
        ):
            last_chunk = chunk
            for part in self._parts_of(chunk):
                if getattr(part, "function_call", None):
                    tool_calls.append(
                        self._tool_call_from(
                            part.function_call,
                            len(tool_calls),
                            getattr(part, "thought_signature", None),
                        )
                    )
                elif getattr(part, "text", None):
                    yield LLMStreamEvent(type="delta", delta=part.text)

        yield LLMStreamEvent(
            type="completed",
            tool_calls=tool_calls,
            completed=self._completed_from(last_chunk),
        )

    @staticmethod
    def _output_config(request: LLMRequest, types) -> dict:
        """O Gemini recusa response_mime_type JSON junto de function_declarations,
        então o JSON só é imposto quando o agente responde sem ferramentas."""
        if request.tools:
            return {
                "tools": [
                    types.Tool(
                        function_declarations=[
                            types.FunctionDeclaration(
                                name=tool.name,
                                description=tool.description,
                                parameters=tool.parameters,
                            )
                            for tool in request.tools
                        ]
                    )
                ]
            }
        if request.expects_json:
            return {"response_mime_type": "application/json"}
        return {}

    @staticmethod
    def _contents_for(request: LLMRequest, types) -> list:
        contents = [
            types.Content(role="user", parts=[types.Part.from_text(text=request.prompt)])
        ]
        for message in request.history:
            if message.role == "tool":
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part.from_function_response(
                                name=result.name, response={"output": result.content}
                            )
                            for result in message.tool_results
                        ],
                    )
                )
                continue
            parts = []
            if message.content:
                parts.append(types.Part.from_text(text=message.content))
            parts.extend(
                types.Part(
                    function_call=types.FunctionCall(name=call.name, args=call.arguments),
                    thought_signature=call.thought_signature,
                )
                for call in message.tool_calls
            )
            if parts:
                contents.append(types.Content(role="model", parts=parts))
        return contents

    @staticmethod
    def _parts_of(chunk) -> list:
        candidates = getattr(chunk, "candidates", None) or []
        if not candidates:
            return []
        content = getattr(candidates[0], "content", None)
        return getattr(content, "parts", None) or []

    @staticmethod
    def _tool_call_from(function_call, index: int, thought_signature: bytes | None) -> ToolCall:
        arguments = getattr(function_call, "args", None) or {}
        return ToolCall(
            id=getattr(function_call, "id", None) or f"gemini_tc_{index}",
            name=getattr(function_call, "name", ""),
            arguments=dict(arguments),
            thought_signature=thought_signature,
        )

    @staticmethod
    def _completed_from(last_chunk) -> LLMCompleted:
        usage = getattr(last_chunk, "usage_metadata", None)
        candidates = getattr(last_chunk, "candidates", None) or []
        finish_reason = getattr(candidates[0], "finish_reason", None) if candidates else None
        return LLMCompleted(
            provider_response_id=getattr(last_chunk, "response_id", None),
            input_tokens=getattr(usage, "prompt_token_count", None),
            output_tokens=getattr(usage, "candidates_token_count", None),
            cached_tokens=getattr(usage, "cached_content_token_count", None),
            finish_reason=str(finish_reason) if finish_reason is not None else None,
        )
