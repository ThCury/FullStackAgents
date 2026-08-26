from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.controllers import todo_controller
from app.database import get_session
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoResponse, TodoUpdate

router = APIRouter(prefix="/todos", tags=["todos"])


@router.get("", response_model=list[TodoResponse])
def list_todos(current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return todo_controller.list_todos(current_user, session)


@router.post("", response_model=TodoResponse, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return todo_controller.create_todo(current_user, payload, session)


@router.patch("/{todo_id}", response_model=TodoResponse)
def update_todo(todo_id: int, payload: TodoUpdate, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    return todo_controller.update_todo(todo_id, current_user, payload, session)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)) -> None:
    todo_controller.delete_todo(todo_id, current_user, session)
