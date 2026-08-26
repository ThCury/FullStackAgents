from pydantic import BaseModel, Field

from domain.models.requirement import Requirement
from domain.models.user_story import UserStory


class ProductBacklog(BaseModel):
    summary: str
    requirements: list[Requirement] = Field(min_length=1)
    user_stories: list[UserStory] = Field(min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

