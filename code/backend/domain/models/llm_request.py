from pydantic import BaseModel


class LLMRequest(BaseModel):
    prompt: str
    system_prompt: str
    model: str
    effort: str | None = None
    temperature: float = 0.2

