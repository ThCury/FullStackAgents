from pydantic import BaseModel


class Requirement(BaseModel):
    id: str
    description: str
    priority: str = "must"

