from datetime import datetime, timezone
import secrets
import time
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AccessToken, RefreshToken, User
from app.schemas import RefreshRequest, TokenPairRead, LoginRequest
from app.security import hash_token, verify_password


router = APIRouter(prefix="/auth", tags=["auth"])
DbSession = Annotated[Session, Depends(get_db)]
bearer_security = HTTPBearer(auto_error=False)


def authentication_error(detail: str = "Authentication is required") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticate_user(user_id: str, password: str, db: Session) -> User | None:
    user = db.get(User, user_id)
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def get_access_token(credentials: HTTPAuthorizationCredentials | None, db: Session) -> AccessToken:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise authentication_error("Bearer access token is required")

    access_token = db.get(AccessToken, hash_token(credentials.credentials))
    if access_token is None or access_token.expires_at <= int(time.time()):
        raise authentication_error("Invalid or expired access token")
    return access_token


def get_current_user(
    bearer_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_security)],
    db: DbSession,
) -> User:
    return get_access_token(bearer_credentials, db).user


def issue_token_pair(user: User, db: Session) -> TokenPairRead:
    """签发一对新的访问/刷新令牌并落库（仅存哈希）"""
    now = int(time.time())
    settings = get_settings()
    access_expires_at = now + settings.access_token_ttl_minutes * 60
    refresh_expires_at = now + settings.refresh_token_ttl_days * 86_400

    raw_access_token = secrets.token_urlsafe(32)
    raw_refresh_token = secrets.token_urlsafe(48)
    refresh_token_hash = hash_token(raw_refresh_token)
    db.add(
        AccessToken(
            token_hash=hash_token(raw_access_token),
            user_id=user.id,
            expires_at=access_expires_at,
            refresh_token_hash=refresh_token_hash,
        )
    )
    db.add(RefreshToken(token_hash=refresh_token_hash, user_id=user.id, expires_at=refresh_expires_at))
    db.commit()

    return TokenPairRead(
        access_token=raw_access_token,
        expires_at=datetime.fromtimestamp(access_expires_at, tz=timezone.utc),
        refresh_token=raw_refresh_token,
        refresh_expires_at=datetime.fromtimestamp(refresh_expires_at, tz=timezone.utc),
        user=user,
    )


@router.post("/login", response_model=TokenPairRead)
def login(payload: LoginRequest, db: DbSession) -> TokenPairRead:
    user = authenticate_user(payload.user_id, payload.password, db)
    if user is None:
        raise authentication_error("Incorrect user ID or password")

    now = int(time.time())
    db.execute(delete(AccessToken).where(AccessToken.expires_at <= now))
    db.execute(delete(RefreshToken).where(RefreshToken.expires_at <= now))
    return issue_token_pair(user, db)


@router.post("/refresh", response_model=TokenPairRead)
def refresh(payload: RefreshRequest, db: DbSession) -> TokenPairRead:
    stored_refresh_token = db.get(RefreshToken, hash_token(payload.refresh_token))
    now = int(time.time())
    if stored_refresh_token is None or stored_refresh_token.expires_at <= now:
        raise authentication_error("Invalid or expired refresh token")

    user = stored_refresh_token.user
    # 轮换：刷新令牌一次性使用，旧令牌作废并换发新令牌对
    db.delete(stored_refresh_token)
    return issue_token_pair(user, db)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    bearer_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_security)],
    db: DbSession,
) -> Response:
    access_token = get_access_token(bearer_credentials, db)
    if access_token.refresh_token_hash is not None:
        paired_refresh_token = db.get(RefreshToken, access_token.refresh_token_hash)
        if paired_refresh_token is not None:
            db.delete(paired_refresh_token)
    db.delete(access_token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
