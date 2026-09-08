from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


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


def test_todo_crud_with_category_time_range_and_tags(client: TestClient) -> None:
    category = client.post("/api/v1/categories", json={"name": "Learning"}).json()
    create_response = client.post(
        "/api/v1/todos",
        json={
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
    assert created["category"]["name"] == "Learning"
    assert created["tags"] == ["backend", "fastapi"]
    assert created["scheduled_end_at"] == "2026-09-08T10:30:00Z"

    get_response = client.get("/api/v1/todos/1")
    assert get_response.status_code == 200
    assert get_response.json()["description"] == "Build a TODO API"

    update_response = client.patch("/api/v1/todos/1", json={"completed": True, "tags": ["api", "python"]})
    assert update_response.status_code == 200
    assert update_response.json()["completed"] is True
    assert update_response.json()["tags"] == ["api", "python"]

    list_response = client.get("/api/v1/todos", params={"completed": True, "category_id": category["id"]})
    assert list_response.status_code == 200
    assert [todo["id"] for todo in list_response.json()] == [1]

    clear_tags_response = client.patch("/api/v1/todos/1", json={"tags": []})
    assert clear_tags_response.status_code == 200
    assert clear_tags_response.json()["tags"] == []

    delete_category_response = client.delete(f"/api/v1/categories/{category['id']}")
    assert delete_category_response.status_code == 204
    assert client.get("/api/v1/todos/1").json()["category"] is None

    delete_response = client.delete("/api/v1/todos/1")
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert client.get("/api/v1/todos/1").status_code == 404


def test_time_point_and_time_validation(client: TestClient) -> None:
    time_point = client.post(
        "/api/v1/todos",
        json={"title": "Stand-up", "scheduled_start_at": "2026-09-08T09:00:00Z"},
    )
    assert time_point.status_code == 201
    assert time_point.json()["scheduled_end_at"] is None

    assert client.post(
        "/api/v1/todos",
        json={"title": "Invalid", "scheduled_end_at": "2026-09-08T10:00:00Z"},
    ).status_code == 422
    assert client.patch(
        f"/api/v1/todos/{time_point.json()['id']}",
        json={"scheduled_end_at": "2026-09-08T08:00:00Z"},
    ).status_code == 422


def test_create_rejects_invalid_values(client: TestClient) -> None:
    assert client.post("/api/v1/todos", json={"title": ""}).status_code == 422
    assert client.post("/api/v1/todos", json={"title": "Unknown", "category_id": 99}).status_code == 404
    assert client.post("/api/v1/todos", json={"title": "Bad tag", "tags": ["   "]}).status_code == 422


def test_update_rejects_null_required_fields(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Keep me"}).json()

    assert client.patch(f"/api/v1/todos/{created['id']}", json={"title": None}).status_code == 422
    assert client.patch(f"/api/v1/todos/{created['id']}", json={"completed": None}).status_code == 422
