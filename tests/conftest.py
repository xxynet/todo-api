from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base, get_db, initialize_database
from app.main import app
from app.models import User
from app.security import hash_password


TEST_ADMIN_PASSWORD = "admin-password-123"


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    database_path = tmp_path / "test.db"
    test_engine = create_engine(
        f"sqlite:///{database_path.as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(test_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    test_session = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)
    initialize_database(test_engine, test_session)
    with test_session() as session:
        admin = session.get(User, "admin")
        assert admin is not None
        admin.password_hash = hash_password(TEST_ADMIN_PASSWORD)
        session.commit()

    def override_get_db() -> Generator[Session, None, None]:
        with test_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    test_engine.dispose()
