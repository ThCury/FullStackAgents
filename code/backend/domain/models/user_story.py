from pydantic import BaseModel, Field

from domain.models.priority import Priority


class UserStory(BaseModel):
    id: str
    title: str
    as_a: str
    i_want: str
    so_that: str
    requirement_ids: list[str] = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1, max_length=5)
    priority: Priority = "must"
