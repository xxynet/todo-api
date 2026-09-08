from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import sys

from fastapi import FastAPI

from app import models  # noqa: F401
from app.api.categories import router as categories_router
from app.api.todos import router as todos_router
from app.api.users import router as users_router
from app.config import get_settings
from app.database import initialize_database


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    admin_password = initialize_database()
    if admin_password is not None:
        sys.stderr.write(
            "Created default user 'admin'. Store this one-time generated password securely: "
            f"{admin_password}\n"
        )
    yield


settings = get_settings()
app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(users_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(todos_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}
