from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.models import Todo
from tests.conftest import TEST_ADMIN_PASSWORD


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "admin", "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_todo(client: TestClient, headers: dict[str, str], title: str) -> int:
    response = client.post(
        "/api/v1/todos",
        json={"user_id": "admin", "title": title},
        headers=headers,
    )
    assert response.status_code == 201
    return int(response.json()["id"])


def test_activity_requires_authentication(client: TestClient) -> None:
    assert client.get("/api/v1/users/me/activity").status_code == 401


def test_activity_counts_todos_per_day(client: TestClient, test_db: sessionmaker[Session]) -> None:
    headers = _auth_headers(client)
    _create_todo(client, headers, "今天一")
    _create_todo(client, headers, "今天二")
    old_todo_id = _create_todo(client, headers, "三天前")

    created_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)
    with test_db() as session:
        todo = session.get(Todo, old_todo_id)
        assert todo is not None
        todo.created_at = created_at
        session.commit()

    response = client.get("/api/v1/users/me/activity?tz=0", headers=headers)
    assert response.status_code == 200
    days = response.json()["days"]
    assert len(days) == 364
    assert days[-1]["count"] == 2
    assert days[-4]["count"] == 1
    assert sum(day["count"] for day in days) == 3
    for previous, current in zip(days, days[1:]):
        assert datetime.fromisoformat(current["date"]) - datetime.fromisoformat(previous["date"]) == timedelta(days=1)


def test_activity_applies_timezone_offset(client: TestClient, test_db: sessionmaker[Session]) -> None:
    headers = _auth_headers(client)
    _create_todo(client, headers, "正午待办")

    # UTC 正午 ±8 小时都不会跨天，断言与运行时刻无关
    noon_utc = (datetime.now(timezone.utc) - timedelta(days=2)).replace(
        hour=12, minute=0, second=0, microsecond=0, tzinfo=None
    )
    with test_db() as session:
        todo = session.scalar(select(Todo))
        assert todo is not None
        todo.created_at = noon_utc
        session.commit()

    response = client.get("/api/v1/users/me/activity?tz=480", headers=headers)
    assert response.status_code == 200
    target = next(day for day in response.json()["days"] if day["date"] == noon_utc.date().isoformat())
    assert target["count"] == 1


def test_activity_validates_parameters(client: TestClient) -> None:
    headers = _auth_headers(client)
    assert client.get("/api/v1/users/me/activity?days=3", headers=headers).status_code == 422
    assert client.get("/api/v1/users/me/activity?tz=1000", headers=headers).status_code == 422
