from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TODO API"
    database_url: str = "sqlite:///./data/data.db"
    port: int = Field(default=8000, ge=1, le=65535)
    allow_registration: bool = True
    access_token_ttl_minutes: int = Field(default=30, ge=5, le=1440)
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
        return origins or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
