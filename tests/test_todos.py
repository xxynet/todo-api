from fastapi.testclient import TestClient


def test_health(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_todo_crud(client: TestClient) -> None:
    create_response = client.post(
        "/api/v1/todos",
        json={"title": "Learn FastAPI", "description": "Build a TODO API"},
    )
    assert create_response.status_code == 201
    created = create_response.json()
    assert created["id"] == 1
    assert created["title"] == "Learn FastAPI"
    assert created["completed"] is False

    get_response = client.get("/api/v1/todos/1")
    assert get_response.status_code == 200
    assert get_response.json()["description"] == "Build a TODO API"

    update_response = client.patch("/api/v1/todos/1", json={"completed": True})
    assert update_response.status_code == 200
    assert update_response.json()["completed"] is True

    list_response = client.get("/api/v1/todos", params={"completed": True})
    assert list_response.status_code == 200
    assert [todo["id"] for todo in list_response.json()] == [1]

    delete_response = client.delete("/api/v1/todos/1")
    assert delete_response.status_code == 204
    assert delete_response.content == b""
    assert client.get("/api/v1/todos/1").status_code == 404


def test_create_rejects_empty_title(client: TestClient) -> None:
    response = client.post("/api/v1/todos", json={"title": ""})
    assert response.status_code == 422


def test_update_rejects_null_required_fields(client: TestClient) -> None:
    created = client.post("/api/v1/todos", json={"title": "Keep me"}).json()

    assert client.patch(f"/api/v1/todos/{created['id']}", json={"title": None}).status_code == 422
    assert client.patch(f"/api/v1/todos/{created['id']}", json={"completed": None}).status_code == 422

