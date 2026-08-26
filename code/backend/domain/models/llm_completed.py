from pydantic import BaseModel


class LLMCompleted(BaseModel):
    provider_response_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_tokens: int | None = None
    finish_reason: str | None = None

