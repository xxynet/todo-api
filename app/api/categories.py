from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Category
from app.schemas import CategoryCreate, CategoryRead, CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])
DbSession = Annotated[Session, Depends(get_db)]


def get_category_or_404(category_id: int, db: Session) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def commit_category(db: Session, category: Category) -> Category:
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="A category with this name already exists"
        ) from error
    db.refresh(category)
    return category


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(payload: CategoryCreate, db: DbSession) -> Category:
    category = Category(**payload.model_dump())
    db.add(category)
    return commit_category(db, category)


@router.get("", response_model=list[CategoryRead])
def list_categories(db: DbSession) -> list[Category]:
    return list(db.scalars(select(Category).order_by(Category.name, Category.id)))


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: DbSession) -> Category:
    return get_category_or_404(category_id, db)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, db: DbSession) -> Category:
    category = get_category_or_404(category_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name") is None and "name" in changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Name cannot be null")
    for field, value in changes.items():
        setattr(category, field, value)
    return commit_category(db, category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession) -> Response:
    category = get_category_or_404(category_id, db)
    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
