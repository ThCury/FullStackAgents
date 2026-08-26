from pydantic import BaseModel


class ToolDefinition(BaseModel):
    """Contrato de uma ferramenta oferecida ao modelo, agnóstico de provider."""

    name: str
    description: str
    parameters: dict
