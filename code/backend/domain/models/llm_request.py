from pydantic import BaseModel, Field

from domain.models.llm_message import LLMMessage
from domain.models.tool_definition import ToolDefinition


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: str
    model: str
    role: str = "PRODUCT_OWNER"
    effort: str | None = None
    temperature: float = 0.2
    tools: list[ToolDefinition] = Field(default_factory=list)
    history: list[LLMMessage] = Field(default_factory=list)
    expects_json: bool = True
