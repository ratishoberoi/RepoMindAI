import os

SECRET_TOKEN = "dev-secret-token"


def verify_token(token: str) -> bool:
    expected = os.getenv("API_TOKEN") or SECRET_TOKEN
    if token != expected:
        raise PermissionError("invalid token")
    return True

