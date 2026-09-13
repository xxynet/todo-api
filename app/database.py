from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


def _ensure_sqlite_directory(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return

    database_path = database_url.removeprefix(prefix)
    if database_path == ":memory:":
        return

    Path(database_path).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


def build_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False, "timeout": 30} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)

    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    return engine


settings = get_settings()
_ensure_sqlite_directory(settings.database_url)
engine = build_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def _migrate_legacy_schema(database_engine: Engine) -> None:
    """create_all 只建缺失的表，不会修改已存在的表；旧库需要补列"""
    inspector = inspect(database_engine)
    if "access_tokens" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("access_tokens")}
    if "refresh_token_hash" in columns:
        return
    with database_engine.begin() as connection:
        connection.execute(text("ALTER TABLE access_tokens ADD COLUMN refresh_token_hash VARCHAR(64)"))
        connection.execute(
            text("CREATE INDEX ix_access_tokens_refresh_token_hash ON access_tokens (refresh_token_hash)")
        )


def initialize_database(database_engine: Engine = engine) -> None:
    """Create the database schema without provisioning application users."""
    Base.metadata.create_all(bind=database_engine)
    _migrate_legacy_schema(database_engine)


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
