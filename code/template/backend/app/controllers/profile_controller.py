from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.user import ProfileUpdate


def update_profile(current_user: User, payload: ProfileUpdate, session: Session) -> User:
    email = payload.email.lower()
    same_email_owner = session.scalar(select(User).where(User.email == email))
    if same_email_owner is not None and same_email_owner.id != current_user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado.")
    current_user.name = payload.name.strip()
    current_user.email = email
    session.commit()
    session.refresh(current_user)
    return current_user
