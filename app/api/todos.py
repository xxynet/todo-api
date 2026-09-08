from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.categories import get_category_or_404
from app.api.users import get_user_or_404
from app.database import get_db
from app.models import Tag, Todo
from app.schemas import TodoCreate, TodoRead, TodoUpdate, validate_schedule

router = APIRouter(prefix="/todos", tags=["todos"])
DbSession = Annotated[Session, Depends(get_db)]


def get_todo_or_404(todo_id: int, db: Session) -> Todo:
    statement = (
        select(Todo)
        .options(selectinload(Todo.category), selectinload(Todo.tags))
        .where(Todo.id == todo_id)
    )
    todo = db.scalar(statement)
    if todo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todo not found")
    return todo


def get_or_create_tags(tag_names: list[str], db: Session) -> list[Tag]:
    if not tag_names:
        return []

    existing_tags = {
        tag.name: tag for tag in db.scalars(select(Tag).where(Tag.name.in_(tag_names)))
    }
    tags: list[Tag] = []
    for tag_name in tag_names:
        tag = existing_tags.get(tag_name)
        if tag is None:
            tag = Tag(name=tag_name)
            db.add(tag)
        tags.append(tag)
    return tags


def validate_category(category_id: int | None, db: Session) -> None:
    if category_id is not None:
        get_category_or_404(category_id, db)


def validate_user(user_id: str, db: Session) -> None:
    get_user_or_404(user_id, db)


def validate_todo_schedule(start_at, end_at) -> None:
    try:
        validate_schedule(start_at, end_at)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)) from error


@router.post("", response_model=TodoRead, status_code=status.HTTP_201_CREATED)
def create_todo(payload: TodoCreate, db: DbSession) -> Todo:
    validate_user(payload.user_id, db)
    validate_category(payload.category_id, db)
    todo_data = payload.model_dump()
    tag_names = todo_data.pop("tags")
    todo = Todo(**todo_data, tags=get_or_create_tags(tag_names, db))
    db.add(todo)
    db.commit()
    return get_todo_or_404(todo.id, db)


@router.get("", response_model=list[TodoRead])
def list_todos(
    db: DbSession,
    user_id: Annotated[str | None, Query()] = None,
    completed: Annotated[bool | None, Query()] = None,
    category_id: Annotated[int | None, Query()] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Todo]:
    statement = select(Todo).options(selectinload(Todo.category), selectinload(Todo.tags)).order_by(
        Todo.created_at.desc(), Todo.id.desc()
    ).offset(offset).limit(limit)
    if user_id is not None:
        statement = statement.where(Todo.user_id == user_id)
    if completed is not None:
        statement = statement.where(Todo.completed == completed)
    if category_id is not None:
        statement = statement.where(Todo.category_id == category_id)
    return list(db.scalars(statement))


@router.get("/{todo_id}", response_model=TodoRead)
def get_todo(todo_id: int, db: DbSession) -> Todo:
    return get_todo_or_404(todo_id, db)


@router.patch("/{todo_id}", response_model=TodoRead)
def update_todo(todo_id: int, payload: TodoUpdate, db: DbSession) -> Todo:
    todo = get_todo_or_404(todo_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("title") is None and "title" in changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Title cannot be null")
    if changes.get("completed") is None and "completed" in changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Completed cannot be null")
    if "category_id" in changes:
        validate_category(changes["category_id"], db)
    if "tags" in changes:
        todo.tags = get_or_create_tags(changes.pop("tags"), db)

    start_at = changes.get("scheduled_start_at", todo.scheduled_start_at)
    end_at = changes.get("scheduled_end_at", todo.scheduled_end_at)
    validate_todo_schedule(start_at, end_at)

    for field, value in changes.items():
        setattr(todo, field, value)

    db.commit()
    return get_todo_or_404(todo.id, db)


@router.delete("/{todo_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_todo(todo_id: int, db: DbSession) -> Response:
    todo = get_todo_or_404(todo_id, db)
    db.delete(todo)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
