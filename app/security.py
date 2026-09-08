import base64
import hashlib
import hmac
import secrets


PASSWORD_ITERATIONS = 600_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS)
    return "$".join(
        (
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(password_hash).decode("ascii"),
        )
    )


def verify_password(password: str, stored_password_hash: str) -> bool:
    try:
        algorithm, iterations, encoded_salt, encoded_hash = stored_password_hash.split("$", maxsplit=3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(encoded_salt.encode("ascii"))
        expected_hash = base64.urlsafe_b64decode(encoded_hash.encode("ascii"))
        actual_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError, binascii.Error):
        return False
    return hmac.compare_digest(actual_hash, expected_hash)
