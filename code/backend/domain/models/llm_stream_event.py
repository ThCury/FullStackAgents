from pydantic import BaseModel, Field

from domain.models.llm_completed import LLMCompleted
from domain.models.tool_call import ToolCall


class LLMStreamEvent(BaseModel):
    type: str
    delta: str = ""
    completed: LLMCompleted | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
