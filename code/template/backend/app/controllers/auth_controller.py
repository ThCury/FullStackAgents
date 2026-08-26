from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.auth import Credentials, Token
from app.security import create_access_token, password_hash


def register(credentials: Credentials, session: Session) -> Token:
    email = credentials.email.lower()
    if session.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado.")
    user = User(email=email, name=email.split("@", maxsplit=1)[0], password_hash=password_hash.hash(credentials.password))
    session.add(user)
    session.commit()
    session.refresh(user)
    return Token(access_token=create_access_token(user.id))


def login(credentials: Credentials, session: Session) -> Token:
    user = session.scalar(select(User).where(User.email == credentials.email.lower()))
    if user is None or not password_hash.verify(credentials.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="E-mail ou senha inválidos.")
    return Token(access_token=create_access_token(user.id))
