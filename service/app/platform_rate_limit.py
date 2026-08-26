from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .platform_models import RateLimitBucket


class DistributedRateLimitExceeded(Exception):
    def __init__(self, namespace: str, limit: int, retry_after: int) -> None:
        self.namespace = namespace
        self.limit = limit
        self.retry_after = retry_after
        super().__init__(f"distributed rate limit exceeded for {namespace}")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def enforce_distributed_limit(
    db: Session,
    *,
    namespace: str,
    subject: str,
    limit: int,
    window_seconds: int = 60,
) -> int:
    if limit < 1 or window_seconds < 1:
        raise ValueError("rate limit parameters must be positive")
    now = _utcnow()
    epoch = int(now.timestamp())
    window_epoch = epoch - (epoch % window_seconds)
    window_start = datetime.fromtimestamp(window_epoch, tz=timezone.utc)
    statement = (
        pg_insert(RateLimitBucket)
        .values(namespace=namespace, subject=subject, window_start=window_start, count=1)
        .on_conflict_do_update(
            constraint="uq_rate_limit_bucket_window",
            set_={"count": RateLimitBucket.count + 1, "updated_at": now},
            where=RateLimitBucket.count < limit,
        )
        .returning(RateLimitBucket.count)
    )
    current = db.execute(statement).scalar_one_or_none()
    if current is None:
        retry_after = max(1, int((window_start + timedelta(seconds=window_seconds) - now).total_seconds()))
        raise DistributedRateLimitExceeded(namespace, limit, retry_after)
    return int(current)
