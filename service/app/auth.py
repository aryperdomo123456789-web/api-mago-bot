from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import time

from fastapi import HTTPException, Request, status

from .core.config import Settings


settings = Settings()
SESSION_COOKIE = "pd_panel_session"
SESSION_TTL_SECONDS = int(os.getenv("LICENSE_PANEL_SESSION_TTL", "604800"))
PBKDF2_ITERATIONS = int(os.getenv("LICENSE_PASSWORD_ITERATIONS", "210000"))


def _secret_key() -> bytes:
    secret = os.getenv("LICENSE_PANEL_SECRET", "") or settings.api_admin_token or "pd-api-panel-secret"
    return secret.encode("utf-8")


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ITERATIONS,
    ).hex()
    return salt, digest


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    _, digest = hash_password(password, salt)
    return hmac.compare_digest(digest, expected_hash)


def issue_session_token(user_id: int) -> str:
    expires_at = int(time.time()) + SESSION_TTL_SECONDS
    payload = f"{user_id}:{expires_at}".encode("utf-8")
    signature = hmac.new(_secret_key(), payload, hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(payload + b":" + signature.encode("utf-8")).decode("utf-8")
    return token


def parse_session_token(token: str) -> int:
    try:
        decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
        user_id_raw, expires_raw, signature = decoded.split(":", 2)
        payload = f"{user_id_raw}:{expires_raw}".encode("utf-8")
        expected = hmac.new(_secret_key(), payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid signature")
        if int(expires_raw) < int(time.time()):
            raise ValueError("expired")
        return int(user_id_raw)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid session") from exc


def set_session_cookie(response, user_id: int):
    response.set_cookie(
        SESSION_COOKIE,
        issue_session_token(user_id),
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=SESSION_TTL_SECONDS,
        path="/",
    )


def clear_session_cookie(response):
    response.delete_cookie(SESSION_COOKIE, path="/")


def get_current_panel_user(request: Request, db):
    from .models import PanelUser

    token = request.cookies.get(SESSION_COOKIE) or request.headers.get("x-panel-session")
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    user_id = parse_session_token(token)
    user = db.get(PanelUser, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user inactive")
    return user
