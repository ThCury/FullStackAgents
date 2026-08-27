from pydantic import BaseModel, Field, model_validator


class CreateProjectMessageCommand(BaseModel):
    content: str | None = Field(default=None, max_length=100_000)
    retry_run_id: str | None = Field(default=None, min_length=1)
    requested_by_id: str = Field(default="local-user", min_length=1)
    requested_by_name: str | None = Field(default="Usuário local", max_length=200)

    @model_validator(mode="after")
    def requires_message_or_retry(self) -> "CreateProjectMessageCommand":
        if bool(self.content and self.content.strip()) == bool(self.retry_run_id):
            raise ValueError("Informe somente content ou retry_run_id.")
        return self
