from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .db import SessionLocal
from .platform_models import ServiceApiKey, UsageCounter


def _get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)

DEFAULT_LIMITS = {
    "start": {"messages_per_minute": 60, "messages_per_day": 1000},
    "pro": {"messages_per_minute": 600, "messages_per_day": 10000},
    "elite": {"messages_per_minute": 3000, "messages_per_day": 100000},
}


class QuotaExceeded(Exception):
    def __init__(self, metric: str, limit: int) -> None:
        self.metric = metric
        self.limit = limit
        super().__init__(f"quota exceeded for {metric}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _window_start(now: datetime, metric: str) -> datetime:
    if metric.endswith("_per_minute"):
        return now.replace(second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def consume_quota(db: Session, tenant_id: int, plan_slug: str, metric: str, amount: int = 1) -> int:
    limit = DEFAULT_LIMITS.get(plan_slug, DEFAULT_LIMITS["start"]).get(metric)
    if limit is None:
        return 0
    if amount < 1 or amount > limit:
        raise QuotaExceeded(metric, limit)

    window_start = _window_start(_utcnow(), metric)
    statement = (
        pg_insert(UsageCounter)
        .values(tenant_id=tenant_id, window_start=window_start, metric=metric, value=amount)
        .on_conflict_do_update(
            constraint="uq_usage_counter_tenant_window_metric",
            set_={"value": UsageCounter.value + amount},
            where=UsageCounter.value + amount <= limit,
        )
        .returning(UsageCounter.value)
    )
    current_value = db.execute(statement).scalar_one_or_none()
    if current_value is None:
        raise QuotaExceeded(metric, limit)
    return int(current_value)


def _token_from_headers(x_api_key: str | None, authorization: str | None) -> str | None:
    if x_api_key and x_api_key.strip():
        return x_api_key.strip()
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return None


def get_service_api_key(
    db: Session = Depends(_get_db),
    x_api_key: str | None = Security(api_key_header),
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> ServiceApiKey:
    authorization = f"{bearer.scheme} {bearer.credentials}" if bearer else None
    raw_token = _token_from_headers(x_api_key, authorization)
    if not raw_token or len(raw_token) < 32:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="api key required")
    key = db.scalar(select(ServiceApiKey).where(ServiceApiKey.token_hash == hashlib.sha256(raw_token.encode("utf-8")).hexdigest()))
    now = _utcnow()
    if not key or key.status != "active" or key.revoked_at is not None or (key.expires_at and key.expires_at <= now):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key")
    key.last_used_at = now
    db.commit()
    return key


def issue_service_api_key() -> tuple[str, str]:
    raw = "mb_live_" + secrets.token_urlsafe(32)
    return raw, hashlib.sha256(raw.encode("utf-8")).hexdigest()


def require_key_scope(key: ServiceApiKey, scope: str) -> None:
    if scope not in set(key.scopes or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="api key scope required")
