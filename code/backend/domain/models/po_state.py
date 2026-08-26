from pydantic import BaseModel

from domain.models.product_backlog import ProductBacklog


class POState(BaseModel):
    run_id: str
    user_prompt: str
    backlog: ProductBacklog | None = None
    raw_response: str = ""

