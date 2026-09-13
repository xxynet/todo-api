import time

from fastapi.testclient import TestClient

from app.models import AccessToken, RefreshToken
from app.security import hash_token
from tests.conftest import TEST_ADMIN_PASSWORD


def login(client: TestClient, password: str = TEST_ADMIN_PASSWORD) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"user_id": "admin", "password": password},
    )
    assert response.status_code == 200
    return response.json()


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


def test_login_issues_refresh_token_pair(client: TestClient) -> None:
    payload = login(client)
    assert payload["refresh_token"]
    assert payload["refresh_expires_at"]
    assert payload["refresh_expires_at"] > payload["expires_at"]


def test_refresh_rotates_token_pair(client: TestClient) -> None:
    payload = login(client)

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["access_token"] != payload["access_token"]
    assert body["refresh_token"] != payload["refresh_token"]
    assert body["user"]["id"] == "admin"

    headers = {"Authorization": f"Bearer {body['access_token']}"}
    assert client.get("/api/v1/users/me", headers=headers).status_code == 200

    # 旧刷新令牌一次性使用后作废
    replay = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert replay.status_code == 401
    assert replay.headers["www-authenticate"] == "Bearer"


def test_refresh_rejects_unknown_refresh_token(client: TestClient) -> None:
    response = client.post("/api/v1/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert response.status_code == 401


def test_refresh_rejects_expired_refresh_token(client: TestClient, test_db) -> None:
    payload = login(client)
    with test_db() as session:
        stored = session.get(RefreshToken, hash_token(payload["refresh_token"]))
        assert stored is not None
        stored.expires_at = int(time.time()) - 10
        session.commit()

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert response.status_code == 401


def test_expired_access_token_is_recovered_via_refresh(client: TestClient, test_db) -> None:
    payload = login(client)
    with test_db() as session:
        stored = session.get(AccessToken, hash_token(payload["access_token"]))
        assert stored is not None
        stored.expires_at = int(time.time()) - 10
        session.commit()

    expired_headers = {"Authorization": f"Bearer {payload['access_token']}"}
    assert client.get("/api/v1/users/me", headers=expired_headers).status_code == 401

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert refreshed.status_code == 200
    new_headers = {"Authorization": f"Bearer {refreshed.json()['access_token']}"}
    assert client.get("/api/v1/users/me", headers=new_headers).status_code == 200


def test_logout_revokes_paired_refresh_token(client: TestClient) -> None:
    payload = login(client)
    headers = {"Authorization": f"Bearer {payload['access_token']}"}

    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204

    response = client.post("/api/v1/auth/refresh", json={"refresh_token": payload["refresh_token"]})
    assert response.status_code == 401
