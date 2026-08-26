from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers import auth_controller
from app.database import get_session
from app.schemas.auth import Credentials, Token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, session: Session = Depends(get_session)) -> Token:
    return auth_controller.register(credentials, session)


@router.post("/login", response_model=Token)
def login(credentials: Credentials, session: Session = Depends(get_session)) -> Token:
    return auth_controller.login(credentials, session)
