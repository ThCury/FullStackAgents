from pydantic import BaseModel, Field


class UserStory(BaseModel):
    id: str
    title: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: list[str] = Field(min_length=1)
    priority: str = "must"

