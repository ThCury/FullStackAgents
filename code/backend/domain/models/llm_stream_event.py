from pydantic import BaseModel

from domain.models.llm_completed import LLMCompleted


class LLMStreamEvent(BaseModel):
    type: str
    delta: str = ""
    completed: LLMCompleted | None = None

