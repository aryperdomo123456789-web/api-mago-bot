from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PanelUser
from .platform_models import PlatformSession
from .surface_auth import enforce_authenticated_surface

PLATFORM_SESSION_COOKIE = os.getenv("PLATFORM_SESSION_COOKIE", "__Host-mago_platform_session")
PLATFORM_SESSION_TTL_SECONDS = int(os.getenv("PLATFORM_SESSION_TTL", "28800"))
PLATFORM_SESSION_IDLE_SECONDS = int(os.getenv("PLATFORM_SESSION_IDLE", "1800"))
PLATFORM_COOKIE_SECURE = os.getenv("PLATFORM_COOKIE_SECURE", "true").lower() == "true"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _session_secret() -> bytes:
    secret = os.getenv("PLATFORM_SESSION_SECRET") or os.getenv("LICENSE_PANEL_SECRET")
    if not secret or len(secret) < 32:
        raise RuntimeError("PLATFORM_SESSION_SECRET must be set to at least 32 characters")
    return secret.encode("utf-8")


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str | None:
    client = request.client
    return client.host if client else None


def issue_platform_session(db: Session, user: PanelUser, request: Request) -> str:
    """Create a random opaque session; only its SHA-256 hash is persisted."""
    _session_secret()
    raw_token = secrets.token_urlsafe(48)
    now = _utcnow()
    db.add(
        PlatformSession(
            session_hash=hash_session_token(raw_token),
            user_id=user.id,
            expires_at=now + timedelta(seconds=PLATFORM_SESSION_TTL_SECONDS),
            last_seen_at=now,
            ip_address=_client_ip(request),
            user_agent=(request.headers.get("user-agent") or "")[:512] or None,
        )
    )
    db.commit()
    return raw_token


def set_platform_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        PLATFORM_SESSION_COOKIE,
        token,
        httponly=True,
        secure=PLATFORM_COOKIE_SECURE,
        samesite="lax",
        max_age=PLATFORM_SESSION_TTL_SECONDS,
        path="/",
    )


def clear_platform_session_cookie(response: Response) -> None:
    response.delete_cookie(PLATFORM_SESSION_COOKIE, path="/")


def get_current_platform_session(request: Request, db: Session) -> PlatformSession:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")

    now = _utcnow()
    session = db.scalar(select(PlatformSession).where(PlatformSession.session_hash == hash_session_token(token)))
    if not session or session.revoked_at is not None or session.expires_at <= now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session expired")

    if session.last_seen_at and session.last_seen_at + timedelta(seconds=PLATFORM_SESSION_IDLE_SECONDS) <= now:
        session.revoked_at = now
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="session idle timeout")

    session.last_seen_at = now
    db.commit()
    return session


def get_current_platform_user(request: Request, db: Session) -> PanelUser:
    session = get_current_platform_session(request, db)
    user = db.get(PanelUser, session.user_id)
    if not user or not user.is_active:
        session.revoked_at = _utcnow()
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user inactive")
    enforce_authenticated_surface(request, user.role)
    return user


def revoke_current_platform_session(request: Request, db: Session) -> None:
    token = request.cookies.get(PLATFORM_SESSION_COOKIE)
    if not token:
        return
    session = db.scalar(select(PlatformSession).where(PlatformSession.session_hash == hash_session_token(token)))
    if session and session.revoked_at is None:
        session.revoked_at = _utcnow()
        db.commit()


def revoke_all_platform_sessions(db: Session, user_id: int) -> int:
    now = _utcnow()
    sessions = db.scalars(
        select(PlatformSession).where(
            PlatformSession.user_id == user_id,
            PlatformSession.revoked_at.is_(None),
        )
    ).all()
    for session in sessions:
        session.revoked_at = now
    db.commit()
    return len(sessions)
