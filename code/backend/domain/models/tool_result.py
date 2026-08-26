from pydantic import BaseModel


class ToolResult(BaseModel):
    """Resultado devolvido ao modelo após executar uma ferramenta."""

    call_id: str
    name: str
    content: str
    is_error: bool = False
