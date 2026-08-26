from pydantic import BaseModel

from domain.models.priority import Priority


class Requirement(BaseModel):
    id: str
    description: str
    priority: Priority = "must"
