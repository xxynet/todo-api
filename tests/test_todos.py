from fastapi.testclient import TestClient


PASSWORD = "safe-password-123"


def credentials(user_id: str) -> tuple[str, str]:
    return user_id, PASSWORD


def register_user(client: TestClient, user_id: str = "caleb", nickname: str = "Caleb") -> dict:
    response = client.post(
        "/api/v1/users/register",
        json={"id": user_id, "nickname": nickname, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_user_registration_and_default_admin(client: TestClient) -> None:
    admin_response = client.get("/api/v1/users/admin")
    assert admin_response.status_code == 200
    assert admin_response.json()["nickname"] == "Administrator"

    user = register_user(client)
    assert user["id"] == "caleb"
    assert user["nickname"] == "Caleb"
    assert "password" not in user
    assert client.get("/api/v1/users/me", auth=credentials("caleb")).json()["id"] == "caleb"
    assert client.get("/api/v1/users/me", auth=("caleb", "incorrect-password")).status_code == 401
    assert client.post(
        "/api/v1/users/register",
        json={"id": "caleb", "nickname": "Another", "password": PASSWORD},
    ).status_code == 409
    assert client.post(
        "/api/v1/users/register",
        json={"id": "bad id", "nickname": "Bad", "password": PASSWORD},
    ).status_code == 422


def test_registration_can_be_disabled(client: TestClient, monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    get_settings.cache_clear()
    response = client.post(
        "/api/v1/users/register",
        json={"id": "blocked", "nickname": "Blocked", "password": PASSWORD},
    )
    assert response.status_code == 403
    monkeypatch.undo()
    get_settings.cache_clear()


def test_category_crud(client: TestClient) -> None:
    create_response = client.post("/api/v1/categories", json={"name": "Work"})
    assert create_response.status_code == 201
    category = create_response.json()
    assert category["id"] == 1
    assert category["name"] == "Work"

    assert client.post("/api/v1/categories", json={"name": "Work"}).status_code == 409

    update_response = client.patch("/api/v1/categories/1", json={"name": "Office"})
    assert update_response.status_code == 200
    assert update_response.json()["name"] == "Office"

    list_response = client.get("/api/v1/categories")
    assert list_response.status_code == 200
    assert [item["name"] for item in list_response.json()] == ["Office"]


def test_todo_crud_with_authentication_and_user_isolation(client: TestClient) -> None:
    user = register_user(client)
    other_user = register_user(client, "bob", "Bob")
    category = client.post("/api/v1/categories", json={"name": "Learning"}).json()

    assert client.get("/api/v1/todos").status_code == 401
    assert client.post(
        "/api/v1/todos", json={"user_id": user["id"], "title": "Unauthenticated"}
    ).status_code == 401
    assert client.post(
        "/api/v1/todos", auth=credentials(other_user["id"]), json={"user_id": user["id"], "title": "Forbidden"}
    ).status_code == 403

    create_response = client.post(
        "/api/v1/todos",
        auth=credentials(user["id"]),
        json={
            "user_id": user["id"],
            "title": "Learn FastAPI",
            "description": "Build a TODO API",
            "category_id": category["id"],
            "tags": ["fastapi", " backend ", "FastAPI"],
            "scheduled_start_at": "2026-09-08T09:00:00Z",
            "scheduled_end_at": "2026-09-08T10:30:00Z",
        },
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1
    assert created["user_id"] == "caleb"
    assert created["category"]["name"] == "Learning"
    assert created["tags"] == ["backend", "fastapi"]

    assert client.get("/api/v1/todos/1", auth=credentials(other_user["id"])).status_code == 404
    assert client.patch("/api/v1/todos/1", auth=credentials(other_user["id"]), json={"completed": True}).status_code == 404
    assert client.delete("/api/v1/todos/1", auth=credentials(other_user["id"])).status_code == 404
    assert client.get("/api/v1/todos", auth=credentials(other_user["id"])).json() == []

    update_response = client.patch(
        "/api/v1/todos/1", auth=credentials(user["id"]), json={"completed": True, "tags": ["api", "python"]}
    )
    assert update_response.status_code == 200
    assert update_response.json()["completed"] is True
    assert update_response.json()["tags"] == ["api", "python"]

    list_response = client.get(
        "/api/v1/todos", auth=credentials(user["id"]), params={"completed": True, "category_id": category["id"]}
    )
    assert [todo["id"] for todo in list_response.json()] == [1]

    clear_tags_response = client.patch("/api/v1/todos/1", auth=credentials(user["id"]), json={"tags": []})
    assert clear_tags_response.status_code == 200
    assert clear_tags_response.json()["tags"] == []

    delete_category_response = client.delete(f"/api/v1/categories/{category['id']}")
    assert delete_category_response.status_code == 204
    assert client.get("/api/v1/todos/1", auth=credentials(user["id"])).json()["category"] is None

    delete_response = client.delete("/api/v1/todos/1", auth=credentials(user["id"]))
    assert delete_response.status_code == 204
    assert client.get("/api/v1/todos/1", auth=credentials(user["id"])).status_code == 404


def test_time_point_and_time_validation(client: TestClient) -> None:
    user = register_user(client)
    time_point = client.post(
        "/api/v1/todos",
        auth=credentials(user["id"]),
        json={"user_id": user["id"], "title": "Stand-up", "scheduled_start_at": "2026-09-08T09:00:00Z"},
    )
    assert time_point.status_code == 201
    assert time_point.json()["scheduled_end_at"] is None

    assert client.post(
        "/api/v1/todos",
        auth=credentials(user["id"]),
        json={"user_id": user["id"], "title": "Invalid", "scheduled_end_at": "2026-09-08T10:00:00Z"},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/todos/{time_point.json()['id']}",
        auth=credentials(user["id"]),
        json={"scheduled_end_at": "2026-09-08T08:00:00Z"},
    ).status_code == 422


def test_create_rejects_invalid_values(client: TestClient) -> None:
    user = register_user(client)
    assert client.post("/api/v1/todos", auth=credentials(user["id"]), json={"title": "Missing user"}).status_code == 422
    assert client.post(
        "/api/v1/todos", auth=credentials(user["id"]), json={"user_id": "unknown", "title": "Unknown user"}
    ).status_code == 403
    assert client.post(
        "/api/v1/todos", auth=credentials(user["id"]), json={"user_id": user["id"], "title": "Unknown", "category_id": 99}
    ).status_code == 404
    assert client.post(
        "/api/v1/todos", auth=credentials(user["id"]), json={"user_id": user["id"], "title": "Bad tag", "tags": ["   "]}
    ).status_code == 422


def test_update_rejects_null_required_fields(client: TestClient) -> None:
    user = register_user(client)
    created = client.post(
        "/api/v1/todos", auth=credentials(user["id"]), json={"user_id": user["id"], "title": "Keep me"}
    ).json()

    assert client.patch(
        f"/api/v1/todos/{created['id']}", auth=credentials(user["id"]), json={"title": None}
    ).status_code == 422
    assert client.patch(
        f"/api/v1/todos/{created['id']}", auth=credentials(user["id"]), json={"completed": None}
    ).status_code == 422
