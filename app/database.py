from collections.abc import Generator
from pathlib import Path
import secrets

from sqlalchemy import Engine, create_engine, event
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


def initialize_database(
    database_engine: Engine = engine, session_factory: sessionmaker[Session] | None = None
) -> str | None:
    """Create the schema and return the one-time admin password when it is created."""
    from app.models import User
    from app.security import hash_password

    Base.metadata.create_all(bind=database_engine)
    factory = session_factory or sessionmaker(bind=database_engine, autoflush=False, expire_on_commit=False)
    with factory() as session:
        if session.get(User, "admin") is not None:
            return None

        password = secrets.token_urlsafe(18)
        session.add(User(id="admin", nickname="Administrator", password_hash=hash_password(password)))
        session.commit()
        return password


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
