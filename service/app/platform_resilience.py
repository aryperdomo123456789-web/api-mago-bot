from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .platform_models import ProviderCircuitState
from .providers.base import ProviderError


class ProviderCircuitOpen(Exception):
    def __init__(self, provider_type: str, resource_key: str, retry_after: int) -> None:
        self.provider_type = provider_type
        self.resource_key = resource_key
        self.retry_after = retry_after
        super().__init__(f"provider circuit open for {provider_type}")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _threshold() -> int:
    return max(1, int(os.getenv("PROVIDER_CIRCUIT_FAILURE_THRESHOLD", "5")))


def _cooldown() -> int:
    return max(5, int(os.getenv("PROVIDER_CIRCUIT_COOLDOWN_SECONDS", "30")))


def before_provider_call(db: Session, *, provider_type: str, resource_key: str) -> None:
    now = _now()
    state = db.scalar(
        select(ProviderCircuitState).where(
            ProviderCircuitState.provider_type == provider_type,
            ProviderCircuitState.resource_key == resource_key,
        )
    )
    if not state:
        state = ProviderCircuitState(provider_type=provider_type, resource_key=resource_key, state="closed")
        db.add(state)
        db.flush()
        return
    if state.state == "open":
        if state.opened_until and state.opened_until <= now:
            state.state = "half_open"
        else:
            retry_after = max(1, int(((state.opened_until or now) - now).total_seconds()))
            raise ProviderCircuitOpen(provider_type, resource_key, retry_after)
    elif state.state == "half_open":
        # A single request may probe the provider; concurrent probes remain blocked.
        state.state = "open"
        state.opened_until = now + timedelta(seconds=_cooldown())
        raise ProviderCircuitOpen(provider_type, resource_key, _cooldown())


def record_provider_success(db: Session, *, provider_type: str, resource_key: str) -> None:
    state = db.scalar(
        select(ProviderCircuitState).where(
            ProviderCircuitState.provider_type == provider_type,
            ProviderCircuitState.resource_key == resource_key,
        )
    )
    if not state:
        return
    state.state = "closed"
    state.failure_count = 0
    state.opened_until = None
    state.last_success_at = _now()
    db.flush()


def record_provider_failure(db: Session, *, provider_type: str, resource_key: str, retryable: bool) -> None:
    state = db.scalar(
        select(ProviderCircuitState).where(
            ProviderCircuitState.provider_type == provider_type,
            ProviderCircuitState.resource_key == resource_key,
        )
    )
    if not state:
        state = ProviderCircuitState(provider_type=provider_type, resource_key=resource_key, state="closed")
        db.add(state)
        db.flush()
    now = _now()
    state.last_failure_at = now
    state.failure_count = (state.failure_count or 0) + 1
    if retryable and state.failure_count >= _threshold():
        state.state = "open"
        state.opened_until = now + timedelta(seconds=_cooldown())
    db.flush()
