from google.genai import types

from domain.models.llm_message import LLMMessage
from domain.models.llm_request import LLMRequest
from domain.models.tool_call import ToolCall
from infrastructure.llm import GeminiStreamingLLM


def test_gemini_history_keeps_tool_thought_signature() -> None:
    signature = b"gemini-signature"
    request = LLMRequest(
        prompt="Liste os arquivos.",
        system_prompt="Você usa ferramentas.",
        model="gemini-3.6-flash",
        history=[
            LLMMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(
                        id="call-1",
                        name="list_files",
                        arguments={},
                        thought_signature=signature,
                    )
                ],
            )
        ],
    )

    contents = GeminiStreamingLLM._contents_for(request, types)
    part = contents[1].parts[0]

    assert part.function_call.name == "list_files"
    assert part.thought_signature == signature
