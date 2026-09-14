from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import PurePath

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.types import Scope

from app import models  # noqa: F401
from app.api.auth import router as auth_router
from app.api.categories import router as categories_router
from app.api.setup import router as setup_router
from app.api.todos import router as todos_router
from app.api.users import router as users_router
from app.config import Settings, get_settings
from app.database import initialize_database


class SPAStaticFiles(StaticFiles):
    """Serve a built single-page app while preserving missing asset 404 responses."""

    module_media_types = {
        ".cjs": "application/javascript",
        ".js": "application/javascript",
        ".mjs": "application/javascript",
        ".wasm": "application/wasm",
    }

    def file_response(self, full_path, stat_result, scope: Scope, status_code: int = 200):
        response = super().file_response(full_path, stat_result, scope, status_code)
        media_type = self.module_media_types.get(PurePath(full_path).suffix.lower())
        if media_type and response.status_code != 304:
            response.headers["content-type"] = media_type
        return response

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            path_parts = PurePath(path).parts
            if (
                exc.status_code == 404
                and (not path_parts or path_parts[0] != "api")
                and "." not in PurePath(path).name
            ):
                return await super().get_response("index.html", scope)
            raise


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    initialize_database()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(setup_router, prefix="/api/v1")
    app.include_router(users_router, prefix="/api/v1")
    app.include_router(categories_router, prefix="/api/v1")
    app.include_router(todos_router, prefix="/api/v1")

    @app.get("/api/v1/health", tags=["health"])
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist_dir = settings.frontend_dist_dir.expanduser().resolve()
    if settings.serve_frontend and frontend_dist_dir.is_dir() and (frontend_dist_dir / "index.html").is_file():
        app.mount("/", SPAStaticFiles(directory=frontend_dist_dir, html=True), name="frontend")

    return app


app = create_app()
