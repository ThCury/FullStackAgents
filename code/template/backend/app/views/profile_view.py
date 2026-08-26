from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers import profile_controller
from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import ProfileUpdate, UserResponse

router = APIRouter(tags=["profile"])


@router.get("/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/profile", response_model=UserResponse)
def update_profile(payload: ProfileUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> User:
    return profile_controller.update_profile(current_user, payload, session)
