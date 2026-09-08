from fastapi.testclient import TestClient

from tests.conftest import TEST_ADMIN_PASSWORD


PASSWORD = "safe-password-123"


def credentials(user_id: str, password: str = PASSWORD) -> tuple[str, str]:
    return user_id, password


def admin_credentials() -> tuple[str, str]:
    return credentials("admin", TEST_ADMIN_PASSWORD)


def register_user(client: TestClient, user_id: str = "caleb", nickname: str = "Caleb") -> dict:
    response = client.post(
        "/api/v1/users/register",
        json={"id": user_id, "nickname": nickname, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def create_category(client: TestClient, name: str = "Work") -> dict:
    response = client.post("/api/v1/categories", auth=admin_credentials(), json={"name": name})
    assert response.status_code == 201
    return response.json()


def set_category_permission(client: TestClient, category_id: int, user_id: str, role: str) -> dict:
    response = client.put(
        f"/api/v1/categories/{category_id}/permissions/{user_id}",
        auth=admin_credentials(),
        json={"role": role},
    )
    assert response.status_code == 200
    return response.json()


def test_health(client: TestClient) -> None:
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_user_registration_and_roles(client: TestClient) -> None:
    admin_response = client.get("/api/v1/users/me", auth=admin_credentials())
    assert admin_response.status_code == 200
    assert admin_response.json()["role"] == "admin"

    user = register_user(client)
    assert user["role"] == "user"
    assert "password" not in user
    assert client.get("/api/v1/users/me", auth=credentials("caleb")).json()["id"] == "caleb"
    assert client.get("/api/v1/users/me", auth=credentials("caleb", "incorrect-password")).status_code == 401
    assert client.post(
        "/api/v1/users/register", json={"id": "caleb", "nickname": "Another", "password": PASSWORD}
    ).status_code == 409


def test_registration_can_be_disabled(client: TestClient, monkeypatch) -> None:
    from app.config import get_settings

    monkeypatch.setenv("ALLOW_REGISTRATION", "false")
    get_settings.cache_clear()
    assert client.post(
        "/api/v1/users/register", json={"id": "blocked", "nickname": "Blocked", "password": PASSWORD}
    ).status_code == 403
    monkeypatch.undo()
    get_settings.cache_clear()


def test_category_admin_management_and_permissions(client: TestClient) -> None:
    user = register_user(client)
    category = create_category(client)

    assert client.get("/api/v1/categories").status_code == 401
    assert client.post("/api/v1/categories", auth=credentials(user["id"]), json={"name": "Blocked"}).status_code == 403
    assert client.get("/api/v1/categories", auth=credentials(user["id"])).json() == []

    permission = set_category_permission(client, category["id"], user["id"], "view")
    assert permission == {"category_id": category["id"], "user_id": "caleb", "role": "view", "created_at": permission["created_at"]}
    assert client.get("/api/v1/categories", auth=credentials(user["id"])).json()[0]["id"] == category["id"]
    assert client.get(f"/api/v1/categories/{category['id']}", auth=credentials(user["id"])).status_code == 200
    assert client.get(f"/api/v1/categories/{category['id']}/permissions", auth=credentials(user["id"])).status_code == 403

    updated_permission = set_category_permission(client, category["id"], user["id"], "edit")
    assert updated_permission["role"] == "edit"
    listed_permissions = client.get(
        f"/api/v1/categories/{category['id']}/permissions", auth=admin_credentials()
    ).json()
    assert [(item["user_id"], item["role"]) for item in listed_permissions] == [("caleb", "edit")]
    assert client.put(
        f"/api/v1/categories/{category['id']}/permissions/missing", auth=admin_credentials(), json={"role": "view"}
    ).status_code == 404
    assert client.put(
        f"/api/v1/categories/{category['id']}/permissions/{user['id']}", auth=admin_credentials(), json={"role": "owner"}
    ).status_code == 422


def test_todo_collaboration_permissions(client: TestClient) -> None:
    editor = register_user(client, "caleb", "Caleb")
    viewer = register_user(client, "bob", "Bob")
    outsider = register_user(client, "eve", "Eve")
    category = create_category(client, "Learning")
    set_category_permission(client, category["id"], editor["id"], "edit")
    set_category_permission(client, category["id"], viewer["id"], "view")

    assert client.get("/api/v1/todos").status_code == 401
    assert client.post(
        "/api/v1/todos",
        auth=credentials(viewer["id"]),
        json={"user_id": viewer["id"], "category_id": category["id"], "title": "Viewer cannot create"},
    ).status_code == 403

    create_response = client.post(
        "/api/v1/todos",
        auth=credentials(editor["id"]),
        json={
            "user_id": editor["id"],
            "title": "Learn FastAPI",
            "description": "Build a TODO API",
            "category_id": category["id"],
            "tags": ["fastapi", " backend ", "FastAPI"],
            "scheduled_start_at": "2026-09-08T09:00:00Z",
            "scheduled_end_at": "2026-09-08T10:30:00Z",
        },
    )
    assert create_response.status_code == 201
    todo = create_response.json()
    assert todo["tags"] == ["backend", "fastapi"]

    assert client.get(f"/api/v1/todos/{todo['id']}", auth=credentials(viewer["id"])).status_code == 200
    assert client.get("/api/v1/todos", auth=credentials(viewer["id"])).json()[0]["id"] == todo["id"]
    assert client.patch(
        f"/api/v1/todos/{todo['id']}", auth=credentials(viewer["id"]), json={"completed": True}
    ).status_code == 403
    assert client.delete(f"/api/v1/todos/{todo['id']}", auth=credentials(viewer["id"])).status_code == 403

    update_response = client.patch(
        f"/api/v1/todos/{todo['id']}", auth=credentials(editor["id"]), json={"completed": True, "tags": ["api"]}
    )
    assert update_response.status_code == 200
    assert update_response.json()["completed"] is True
    assert client.get(f"/api/v1/todos/{todo['id']}", auth=credentials(outsider["id"])).status_code == 404

    personal_todo = client.post(
        "/api/v1/todos",
        auth=credentials(editor["id"]),
        json={"user_id": editor["id"], "title": "Private"},
    ).json()
    assert client.get(f"/api/v1/todos/{personal_todo['id']}", auth=credentials(viewer["id"])).status_code == 404

    assert client.delete(
        f"/api/v1/categories/{category['id']}/permissions/{viewer['id']}", auth=admin_credentials()
    ).status_code == 204
    assert client.get(f"/api/v1/todos/{todo['id']}", auth=credentials(viewer["id"])).status_code == 404


def test_time_and_invalid_values(client: TestClient) -> None:
    user = register_user(client)
    time_point = client.post(
        "/api/v1/todos",
        auth=credentials(user["id"]),
        json={"user_id": user["id"], "title": "Stand-up", "scheduled_start_at": "2026-09-08T09:00:00Z"},
    )
    assert time_point.status_code == 201
    assert client.post(
        "/api/v1/todos",
        auth=credentials(user["id"]),
        json={"user_id": user["id"], "title": "Invalid", "scheduled_end_at": "2026-09-08T10:00:00Z"},
    ).status_code == 422
    assert client.post(
        "/api/v1/todos", auth=credentials(user["id"]), json={"title": "Missing user"}
    ).status_code == 422
    assert client.post(
        "/api/v1/todos", auth=credentials(user["id"]), json={"user_id": user["id"], "title": "Bad tag", "tags": [" "]}
    ).status_code == 422
