from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserRead
from app.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])
DbSession = Annotated[Session, Depends(get_db)]
ADMIN_ROLE = "admin"


def is_admin(user: User) -> bool:
    return user.role == ADMIN_ROLE


def require_admin(user: User) -> None:
    if not is_admin(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator permission is required")


def get_user_or_404(user_id: str, db: Session) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register_user(payload: UserCreate, db: DbSession) -> User:
    if not get_settings().allow_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User registration is disabled")

    user = User(id=payload.id, nickname=payload.nickname, role="user", password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this id already exists") from error
    db.refresh(user)
    return user


@router.get("/me", response_model=UserRead)
def get_current_user_profile(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, db: DbSession) -> User:
    return get_user_or_404(user_id, db)
