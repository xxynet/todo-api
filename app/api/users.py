from datetime import datetime, time, timedelta, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.config import get_settings
from app.database import get_db
from app.models import AdminBootstrap, Todo, User
from app.schemas import ActivityDayRead, AdminBootstrapCreate, UserActivityRead, UserCreate, UserRead, UserUpdate
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


@router.post("/bootstrap-admin", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(payload: AdminBootstrapCreate, db: DbSession) -> User:
    if db.scalar(select(User.id).where(User.role == ADMIN_ROLE).limit(1)) is not None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="The initial admin account has already been provisioned")
    if db.get(User, payload.id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="A user with this id already exists")

    user = User(id=payload.id, nickname=payload.nickname, role=payload.role, password_hash=hash_password(payload.password))
    db.add(user)
    try:
        db.flush()
        db.add(AdminBootstrap(id=1, admin_user_id=user.id))
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The initial admin account has already been provisioned",
        ) from error
    db.refresh(user)
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


@router.patch("/me", response_model=UserRead)
def update_current_user_profile(
    payload: UserUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> User:
    changes = payload.model_dump(exclude_unset=True)
    if "nickname" in changes:
        current_user.nickname = changes["nickname"]
    if "password" in changes:
        current_user.password_hash = hash_password(changes["password"])
    db.commit()
    db.refresh(current_user)
    return current_user

@router.get("/me/activity", response_model=UserActivityRead)
def get_my_activity(
    current_user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
    days: Annotated[int, Query(ge=7, le=400)] = 364,
    tz: Annotated[int, Query(ge=-840, le=840)] = 0,
) -> UserActivityRead:
    """按用户本地日历日聚合最近 days 天新建的待办数。

    created_at 以无时区标记的 UTC 存储；tz 为本地时区相对 UTC 的偏移分钟数（东八区为 480）。
    """
    local_end = datetime.now(timezone.utc).astimezone(timezone(timedelta(minutes=tz))).date()
    local_start = local_end - timedelta(days=days - 1)
    utc_start = datetime.combine(local_start, time.min) - timedelta(minutes=tz)

    day_expr = func.date(Todo.created_at, f"{tz:+d} minutes")
    counts = dict(
        db.execute(
            select(day_expr, func.count())
            .where(Todo.user_id == current_user.id, Todo.created_at >= utc_start)
            .group_by(day_expr)
        ).all()
    )

    day_list: list[ActivityDayRead] = []
    for offset in range(days):
        day = local_start + timedelta(days=offset)
        day_list.append(ActivityDayRead(date=day, count=counts.get(day.isoformat(), 0)))
    return UserActivityRead(days=day_list)


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: str, db: DbSession) -> User:
    return get_user_or_404(user_id, db)
