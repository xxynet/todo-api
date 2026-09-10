from fastapi.testclient import TestClient

from tests.conftest import TEST_ADMIN_PASSWORD


def test_login_bearer_access_and_logout(client: TestClient) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "admin", "password": TEST_ADMIN_PASSWORD},
    )
    assert login_response.status_code == 200
    payload = login_response.json()
    assert payload["token_type"] == "bearer"
    assert payload["access_token"]
    assert payload["expires_at"]
    assert payload["user"]["id"] == "admin"
    assert payload["user"]["role"] == "admin"

    headers = {"Authorization": f"Bearer {payload['access_token']}"}
    profile_response = client.get("/api/v1/users/me", headers=headers)
    assert profile_response.status_code == 200
    assert profile_response.json()["id"] == "admin"

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/users/me", headers=headers).status_code == 401


def test_login_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "admin", "password": "incorrect-password"},
    )
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_basic_authentication_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/users/me", auth=("admin", TEST_ADMIN_PASSWORD))
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_admin_bootstrap_is_closed_after_initial_setup(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users/bootstrap-admin",
        json={
            "id": "another-admin",
            "nickname": "Another Administrator",
            "password": TEST_ADMIN_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 403


def test_admin_bootstrap_rejects_non_admin_role(client: TestClient) -> None:
    response = client.post(
        "/api/v1/users/bootstrap-admin",
        json={
            "id": "not-an-admin",
            "nickname": "Not an Administrator",
            "password": TEST_ADMIN_PASSWORD,
            "role": "user",
        },
    )
    assert response.status_code == 422


def test_setup_status_reports_admin_provisioning(client: TestClient) -> None:
    response = client.get("/api/v1/setup/status")
    assert response.status_code == 200
    assert response.json() == {"admin_provisioned": True}


def test_cors_preflight_allows_frontend_authorization_header(client: TestClient) -> None:
    response = client.options(
        "/api/v1/todos",
        headers={
            "Origin": "https://frontend.example",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "Authorization" in response.headers["access-control-allow-headers"]

def test_current_user_can_update_nickname_and_password(client: TestClient) -> None:
    login_response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "admin", "password": TEST_ADMIN_PASSWORD},
    )
    headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}

    response = client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"nickname": "Renamed Admin", "password": "new-admin-password-123"},
    )
    assert response.status_code == 200
    assert response.json()["nickname"] == "Renamed Admin"
    assert response.json()["role"] == "admin"

    assert client.post(
        "/api/v1/auth/login",
        json={"user_id": "admin", "password": "new-admin-password-123"},
    ).status_code == 200


def test_current_user_profile_update_requires_authentication(client: TestClient) -> None:
    response = client.patch("/api/v1/users/me", json={"nickname": "Unauthorised"})
    assert response.status_code == 401
