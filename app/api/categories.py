from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.api.users import get_user_or_404, is_admin, require_admin
from app.database import get_db
from app.models import Category, CategoryPermission, User
from app.schemas import (
    CategoryCreate,
    CategoryPermissionRead,
    CategoryPermissionUpsert,
    CategoryRead,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["categories"])
DbSession = Annotated[Session, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_category_or_404(category_id: int, db: Session) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def get_category_permission(category_id: int, user_id: str, db: Session) -> CategoryPermission | None:
    return db.get(CategoryPermission, {"category_id": category_id, "user_id": user_id})


def can_view_category(category_id: int, current_user: User, db: Session) -> bool:
    return is_admin(current_user) or get_category_permission(category_id, current_user.id, db) is not None


def can_edit_category(category_id: int, current_user: User, db: Session) -> bool:
    if is_admin(current_user):
        return True
    permission = get_category_permission(category_id, current_user.id, db)
    return permission is not None and permission.role == "edit"


def get_viewable_category_or_404(category_id: int, current_user: User, db: Session) -> Category:
    category = get_category_or_404(category_id, db)
    if not can_view_category(category.id, current_user, db):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


def require_category_editor(category_id: int, current_user: User, db: Session) -> Category:
    category = get_viewable_category_or_404(category_id, current_user, db)
    if not can_edit_category(category.id, current_user, db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Edit permission is required for this category")
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
def create_category(payload: CategoryCreate, current_user: CurrentUser, db: DbSession) -> Category:
    require_admin(current_user)
    category = Category(**payload.model_dump())
    db.add(category)
    return commit_category(db, category)


@router.get("", response_model=list[CategoryRead])
def list_categories(current_user: CurrentUser, db: DbSession) -> list[Category]:
    statement = select(Category).order_by(Category.name, Category.id)
    if not is_admin(current_user):
        statement = statement.join(CategoryPermission).where(CategoryPermission.user_id == current_user.id)
    return list(db.scalars(statement))


@router.get("/{category_id}/permissions", response_model=list[CategoryPermissionRead])
def list_category_permissions(category_id: int, current_user: CurrentUser, db: DbSession) -> list[CategoryPermission]:
    require_admin(current_user)
    get_category_or_404(category_id, db)
    return list(
        db.scalars(
            select(CategoryPermission)
            .where(CategoryPermission.category_id == category_id)
            .order_by(CategoryPermission.user_id)
        )
    )


@router.put("/{category_id}/permissions/{user_id}", response_model=CategoryPermissionRead)
def set_category_permission(
    category_id: int,
    user_id: str,
    payload: CategoryPermissionUpsert,
    current_user: CurrentUser,
    db: DbSession,
) -> CategoryPermission:
    require_admin(current_user)
    get_category_or_404(category_id, db)
    get_user_or_404(user_id, db)
    permission = get_category_permission(category_id, user_id, db)
    if permission is None:
        permission = CategoryPermission(category_id=category_id, user_id=user_id, role=payload.role)
        db.add(permission)
    else:
        permission.role = payload.role
    db.commit()
    db.refresh(permission)
    return permission


@router.delete("/{category_id}/permissions/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category_permission(category_id: int, user_id: str, current_user: CurrentUser, db: DbSession) -> Response:
    require_admin(current_user)
    permission = get_category_permission(category_id, user_id, db)
    if permission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category permission not found")
    db.delete(permission)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, current_user: CurrentUser, db: DbSession) -> Category:
    return get_viewable_category_or_404(category_id, current_user, db)


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(category_id: int, payload: CategoryUpdate, current_user: CurrentUser, db: DbSession) -> Category:
    require_admin(current_user)
    category = get_category_or_404(category_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("name") is None and "name" in changes:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Name cannot be null")
    for field, value in changes.items():
        setattr(category, field, value)
    return commit_category(db, category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, current_user: CurrentUser, db: DbSession) -> Response:
    require_admin(current_user)
    category = get_category_or_404(category_id, db)
    db.delete(category)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
