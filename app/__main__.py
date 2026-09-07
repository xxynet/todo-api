"""Run the API server using settings from the environment or .env file."""

import uvicorn

from app.config import get_settings


if __name__ == "__main__":
    settings = get_settings()
    uvicorn.run("app.main:app", host="127.0.0.1", port=settings.port)
