from pydantic import BaseModel, Field


class CreateRunCommand(BaseModel):
    prompt: str = Field(min_length=1, max_length=100_000)
    requested_by_id: str = Field(default="local-user", min_length=1)
    requested_by_name: str | None = Field(default="Usuário local", max_length=200)

