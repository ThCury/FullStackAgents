from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.todo import Todo
from app.models.user import User
from app.schemas.todo import TodoCreate, TodoUpdate


def list_todos(current_user: User, session: Session) -> list[Todo]:
    return list(session.scalars(select(Todo).where(Todo.owner_id == current_user.id).order_by(Todo.id)))


def create_todo(current_user: User, payload: TodoCreate, session: Session) -> Todo:
    todo = Todo(title=payload.title.strip(), description=payload.description.strip(), scheduled_time=payload.scheduled_time, repeats_daily=payload.repeats_daily, owner_id=current_user.id)
    session.add(todo)
    session.commit()
    session.refresh(todo)
    return todo


def update_todo(todo_id: int, current_user: User, payload: TodoUpdate, session: Session) -> Todo:
    todo = _owned_todo(todo_id, current_user, session)
    for field in payload.model_fields_set:
        value = getattr(payload, field)
        setattr(todo, field, value.strip() if field in {"title", "description"} and value is not None else value)
    session.commit()
    session.refresh(todo)
    return todo


def delete_todo(todo_id: int, current_user: User, session: Session) -> None:
    session.delete(_owned_todo(todo_id, current_user, session))
    session.commit()


def _owned_todo(todo_id: int, current_user: User, session: Session) -> Todo:
    todo = session.get(Todo, todo_id)
    if todo is None or todo.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarefa não encontrada.")
    return todo
