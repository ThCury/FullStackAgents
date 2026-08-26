from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    name: str


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
