from app.security import hash_access_token, verify_password


def test_malformed_password_hash_is_rejected() -> None:
    assert verify_password("password", "malformed") is False


def test_access_tokens_are_hashed_deterministically() -> None:
    assert hash_access_token("example-token") == hash_access_token("example-token")
    assert hash_access_token("example-token") != hash_access_token("different-token")
