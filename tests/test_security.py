from app.security import hash_token, verify_password


def test_malformed_password_hash_is_rejected() -> None:
    assert verify_password("password", "malformed") is False


def test_tokens_are_hashed_deterministically() -> None:
    assert hash_token("example-token") == hash_token("example-token")
    assert hash_token("example-token") != hash_token("different-token")
