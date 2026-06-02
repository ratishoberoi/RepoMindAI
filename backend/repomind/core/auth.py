from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from secrets import compare_digest, token_urlsafe
from typing import Any
from urllib.parse import urlencode

import httpx
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException, Request, status
from repomind.core.config import get_settings
from repomind.core.security import audit_event, supplied_api_key_matches
from repomind.core.store import store


def hash_password(password: str, salt: bytes | None = None) -> str:
    if len(password) < 12:
        raise ValueError("Password must be at least 12 characters.")
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 310_000)
    return f"pbkdf2_sha256$310000${base64.urlsafe_b64encode(salt).decode()}${base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, encoded: str | None) -> bool:
    if not encoded:
        return False
    try:
        algorithm, iterations, salt_b64, digest_b64 = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        salt = base64.urlsafe_b64decode(salt_b64.encode())
        expected = base64.urlsafe_b64decode(digest_b64.encode())
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def create_session(user_id: str, org_id: str, roles: list[str]) -> dict[str, Any]:
    settings = get_settings()
    now = int(time.time())
    payload = {
        "sub": user_id,
        "org": org_id,
        "roles": roles,
        "iat": now,
        "exp": now + settings.session_ttl_seconds,
    }
    token = _sign_payload(payload)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": payload["exp"],
        "organization_id": org_id,
        "user_id": user_id,
        "roles": roles,
    }


def decode_session(token: str) -> dict[str, Any]:
    try:
        body, supplied_signature = token.rsplit(".", 1)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session."
        ) from exc
    expected = _signature(body)
    if not compare_digest(supplied_signature, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session.")
    try:
        payload = json.loads(base64.urlsafe_b64decode(_pad_base64(body)).decode())
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session."
        ) from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired.")
    return payload


def current_identity(request: Request) -> dict[str, Any]:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        payload = decode_session(header.split(" ", 1)[1].strip())
        user_id = payload["sub"]
        org_id = payload["org"]
        membership = store.assert_membership(user_id, org_id)
        identity = {
            "user_id": user_id,
            "org_id": org_id,
            "roles": payload.get("roles") or [membership["role"]],
            "auth_mode": "session",
        }
        request.state.identity = identity
        request.state.org_id = org_id
        request.state.user_id = user_id
        return identity
    if supplied_api_key_matches(request):
        settings = get_settings()
        org_id = "default"
        user_id = "local-admin"
        if settings.env.lower() not in {"production", "prod", "docker"}:
            org_id = request.headers.get("x-org-id") or org_id
            user_id = request.headers.get("x-user-id") or user_id
        identity = {
            "user_id": user_id,
            "org_id": org_id,
            "roles": ["owner"],
            "auth_mode": "api_key",
        }
        request.state.identity = identity
        request.state.org_id = org_id
        request.state.user_id = user_id
        return identity
    audit_event("auth_failed", request, status_code=status.HTTP_401_UNAUTHORIZED)
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")


def issue_oauth_state(provider: str, redirect_uri: str, request: Request | None = None) -> str:
    state = token_urlsafe(32)
    org_id = getattr(request.state, "org_id", None) if request else None
    user_id = getattr(request.state, "user_id", None) if request else None
    store.create_oauth_state(
        provider=provider,
        state=state,
        redirect_uri=redirect_uri,
        org_id=org_id,
        user_id=user_id,
        expires_at=time.time() + 600,
    )
    return state


def github_authorize_url(state: str, redirect_uri: str) -> str:
    settings = get_settings()
    if not settings.github_oauth_client_id:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")
    return "https://github.com/login/oauth/authorize?" + urlencode(
        {
            "client_id": settings.github_oauth_client_id,
            "redirect_uri": redirect_uri,
            "scope": "read:user user:email repo",
            "state": state,
        }
    )


def google_authorize_url(state: str, redirect_uri: str) -> str:
    settings = get_settings()
    if not settings.google_oauth_client_id:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(
        {
            "client_id": settings.google_oauth_client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "offline",
            "prompt": "consent",
        }
    )


async def complete_github_oauth(code: str, state: str) -> dict[str, Any]:
    settings = get_settings()
    oauth_state = store.pop_oauth_state("github", state)
    if not settings.github_oauth_client_id or not settings.github_oauth_client_secret:
        raise HTTPException(status_code=503, detail="GitHub OAuth is not configured.")
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"accept": "application/json"},
            data={
                "client_id": settings.github_oauth_client_id,
                "client_secret": settings.github_oauth_client_secret,
                "code": code,
                "redirect_uri": oauth_state["redirect_uri"],
                "state": state,
            },
        )
        token_response.raise_for_status()
        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub did not return an access token.")
        user_response = await client.get(
            f"{settings.github_api_url}/user",
            headers={"authorization": f"Bearer {access_token}", "accept": "application/json"},
        )
        user_response.raise_for_status()
        profile = user_response.json()
        emails_response = await client.get(
            f"{settings.github_api_url}/user/emails",
            headers={"authorization": f"Bearer {access_token}", "accept": "application/json"},
        )
        emails = emails_response.json() if emails_response.status_code == 200 else []
    email = _github_primary_email(profile, emails)
    account = _user_or_new_oauth_account(
        email=email,
        name=profile.get("name") or profile.get("login") or email,
        provider="github",
        provider_subject=str(profile["id"]),
    )
    org_id = oauth_state.get("org_id") or account["organization"]["id"]
    user_id = oauth_state.get("user_id") or account["user"]["id"]
    store.upsert_external_account(
        org_id=org_id,
        user_id=user_id,
        provider="github",
        provider_subject=str(profile["id"]),
        username=profile.get("login"),
        access_token_encrypted=encrypt_secret(access_token),
        scopes=[scope.strip() for scope in str(token_payload.get("scope", "")).split(",") if scope],
        metadata={"profile_url": profile.get("html_url")},
    )
    roles = [
        item["role"] for item in store.memberships_for_user(user_id) if item["org_id"] == org_id
    ]
    return _auth_response(user_id, org_id, roles or ["owner"])


async def complete_google_oauth(code: str, state: str) -> dict[str, Any]:
    settings = get_settings()
    oauth_state = store.pop_oauth_state("google", state)
    if not settings.google_oauth_client_id or not settings.google_oauth_client_secret:
        raise HTTPException(status_code=503, detail="Google OAuth is not configured.")
    async with httpx.AsyncClient(timeout=15) as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": settings.google_oauth_client_id,
                "client_secret": settings.google_oauth_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": oauth_state["redirect_uri"],
            },
        )
        token_response.raise_for_status()
        token_payload = token_response.json()
        access_token = token_payload.get("access_token")
        if not access_token:
            raise HTTPException(status_code=400, detail="Google did not return an access token.")
        user_response = await client.get(
            "https://openidconnect.googleapis.com/v1/userinfo",
            headers={"authorization": f"Bearer {access_token}"},
        )
        user_response.raise_for_status()
        profile = user_response.json()
    email = profile.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Google profile did not include email.")
    account = _user_or_new_oauth_account(
        email=email,
        name=profile.get("name") or email,
        provider="google",
        provider_subject=str(profile["sub"]),
    )
    org_id = oauth_state.get("org_id") or account["organization"]["id"]
    user_id = oauth_state.get("user_id") or account["user"]["id"]
    store.upsert_external_account(
        org_id=org_id,
        user_id=user_id,
        provider="google",
        provider_subject=str(profile["sub"]),
        username=email,
        access_token_encrypted=encrypt_secret(access_token),
        refresh_token_encrypted=encrypt_secret(token_payload.get("refresh_token"))
        if token_payload.get("refresh_token")
        else None,
        scopes=["openid", "email", "profile"],
        metadata={"picture": profile.get("picture")},
    )
    roles = [
        item["role"] for item in store.memberships_for_user(user_id) if item["org_id"] == org_id
    ]
    return _auth_response(user_id, org_id, roles or ["owner"])


def encrypt_secret(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode()


def decrypt_secret(value: str) -> str:
    try:
        return _fernet().decrypt(value.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Stored secret could not be decrypted.") from exc


def _auth_response(user_id: str, org_id: str, roles: list[str]) -> dict[str, Any]:
    user = store.get_user(user_id)
    session = create_session(user_id, org_id, roles)
    return {
        **session,
        "user": {"id": user["id"], "email": user["email"], "name": user["name"]},
        "organization": {"id": org_id},
    }


def _user_or_new_oauth_account(
    email: str, name: str, provider: str, provider_subject: str
) -> dict[str, Any]:
    try:
        user = store.get_user_by_email(email)
        memberships = store.memberships_for_user(user["id"])
        org_id = memberships[0]["org_id"] if memberships else "default"
        return {"user": user, "organization": {"id": org_id}}
    except KeyError:
        return store.create_user_with_org(
            email=email,
            name=name,
            password_hash=None,
            auth_provider=provider,
            provider_subject=provider_subject,
        )


def _github_primary_email(profile: dict[str, Any], emails: list[dict[str, Any]]) -> str:
    for item in emails:
        if item.get("primary") and item.get("verified") and item.get("email"):
            return str(item["email"])
    if profile.get("email"):
        return str(profile["email"])
    raise HTTPException(status_code=400, detail="GitHub profile did not include a public email.")


def _sign_payload(payload: dict[str, Any]) -> str:
    body = _b64(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
    return f"{body}.{_signature(body)}"


def _signature(body: str) -> str:
    return _b64(hmac.new(_auth_secret(), body.encode(), hashlib.sha256).digest())


def _auth_secret() -> bytes:
    settings = get_settings()
    secret = settings.auth_secret or settings.api_key
    if not secret:
        secret = "development-only-repomind-auth-secret"
    return secret.encode()


def _fernet() -> Fernet:
    settings = get_settings()
    secret = settings.secret_key or settings.auth_secret or settings.api_key
    if not secret:
        secret = "development-only-repomind-secret-key"
    digest = hashlib.sha256(secret.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _pad_base64(value: str) -> bytes:
    return (value + "=" * (-len(value) % 4)).encode()
