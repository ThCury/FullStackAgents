from pydantic import BaseModel, Field

from domain.models.tool_call import ToolCall
from domain.models.tool_result import ToolResult


class LLMMessage(BaseModel):
    """Turno da conversa. `tool_results` só aparece em mensagens de role `tool`."""

    role: str
    content: str = ""
    tool_calls: list[ToolCall] = Field(default_factory=list)
    tool_results: list[ToolResult] = Field(default_factory=list)
