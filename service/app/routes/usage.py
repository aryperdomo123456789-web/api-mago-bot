from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PlanCatalog
from ..platform_auth import get_current_platform_user
from ..platform_models import Subscription, UsageCounter, UsageLedgerEntry
from ..platform_rbac import require_tenant_permission

router = APIRouter(prefix="/v1/platform", tags=["usage-billing"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _window(metric: str) -> datetime:
    now = _utcnow()
    if metric.endswith("_per_minute"):
        return now.replace(second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


@router.get("/usage")
def usage(tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "usage:read")
    counters = {}
    for metric in ("messages_per_minute", "messages_per_day"):
        row = db.scalar(select(UsageCounter).where(UsageCounter.tenant_id == tenant_id, UsageCounter.metric == metric, UsageCounter.window_start == _window(metric)))
        counters[metric] = row.value if row else 0
    ledger_rows = db.execute(
        select(UsageLedgerEntry.metric, func.sum(UsageLedgerEntry.units))
        .where(UsageLedgerEntry.tenant_id == tenant_id, UsageLedgerEntry.created_at >= _window("messages_per_day"))
        .group_by(UsageLedgerEntry.metric)
    ).all()
    ledger = {metric: int(total or 0) for metric, total in ledger_rows}
    subscription = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id).order_by(Subscription.id.desc()))
    plan_slug = subscription.plan_slug if subscription else "start"
    plan = db.scalar(select(PlanCatalog).where(PlanCatalog.slug == plan_slug))
    from ..platform_limits import DEFAULT_LIMITS
    limits = DEFAULT_LIMITS.get(plan_slug, DEFAULT_LIMITS["start"])
    return {
        "tenant_id": tenant_id,
        "plan": {"slug": plan_slug, "name": plan.name if plan else plan_slug, "status": subscription.status if subscription else "trialing"},
        "usage": counters,
        "ledger": {"period": "current_day", "units": ledger},
        "limits": limits,
        "period_end": subscription.current_period_end if subscription else None,
    }


@router.get("/usage/ledger")
def usage_ledger(tenant_id: int, request: Request, limit: int = 100, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "usage:read")
    if limit < 1 or limit > 500:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 500")
    rows = db.scalars(
        select(UsageLedgerEntry)
        .where(UsageLedgerEntry.tenant_id == tenant_id)
        .order_by(desc(UsageLedgerEntry.created_at), desc(UsageLedgerEntry.id))
        .limit(limit)
    ).all()
    return {
        "items": [
            {
                "id": str(row.entry_uuid),
                "metric": row.metric,
                "units": row.units,
                "provider": row.provider_type,
                "source_type": row.source_type,
                "source_id": row.source_id,
                "cost_micros": row.cost_micros,
                "currency": row.currency,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.get("/billing")
def billing(tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "usage:read")
    subscription = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant_id).order_by(Subscription.id.desc()))
    if not subscription:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="subscription not found")
    return {
        "tenant_id": tenant_id,
        "plan_slug": subscription.plan_slug,
        "status": subscription.status,
        "current_period_start": subscription.current_period_start,
        "current_period_end": subscription.current_period_end,
        "external_customer_id": subscription.external_customer_id,
        "external_subscription_id": subscription.external_subscription_id,
    }
