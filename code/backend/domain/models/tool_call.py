from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """Pedido de execução de ferramenta emitido pelo modelo."""

    id: str
    name: str
    arguments: dict
    # O Gemini 3 exige que esta assinatura volte junto da mesma function call.
    # Ela serve apenas para continuar a conversa com o provedor e não é auditada.
    thought_signature: bytes | None = Field(default=None, exclude=True)
