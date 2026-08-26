from pydantic import BaseModel


class Actor(BaseModel):
    type: str
    id: str
    role: str | None = None
    display_name: str | None = None

