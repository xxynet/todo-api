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
from app.models import AccessToken, User
from app.schemas import AccessTokenRead, LoginRequest
from app.security import hash_access_token, verify_password


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

    access_token = db.get(AccessToken, hash_access_token(credentials.credentials))
    if access_token is None or access_token.expires_at <= int(time.time()):
        raise authentication_error("Invalid or expired access token")
    return access_token


def get_current_user(
    bearer_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_security)],
    db: DbSession,
) -> User:
    return get_access_token(bearer_credentials, db).user


@router.post("/login", response_model=AccessTokenRead)
def login(payload: LoginRequest, db: DbSession) -> AccessTokenRead:
    user = authenticate_user(payload.user_id, payload.password, db)
    if user is None:
        raise authentication_error("Incorrect user ID or password")

    now = int(time.time())
    expires_at = now + get_settings().access_token_ttl_minutes * 60
    db.execute(delete(AccessToken).where(AccessToken.expires_at <= now))

    raw_token = secrets.token_urlsafe(32)
    db.add(AccessToken(token_hash=hash_access_token(raw_token), user_id=user.id, expires_at=expires_at))
    db.commit()

    return AccessTokenRead(
        access_token=raw_token,
        expires_at=datetime.fromtimestamp(expires_at, tz=timezone.utc),
        user=user,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    bearer_credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_security)],
    db: DbSession,
) -> Response:
    access_token = get_access_token(bearer_credentials, db)
    db.delete(access_token)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
