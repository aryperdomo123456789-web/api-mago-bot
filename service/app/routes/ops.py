from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_models import (
    AuditEvent,
    Conversation,
    EmailDelivery,
    OwnerWelcomeDelivery,
    PlatformProject,
    ProviderResource,
    ProviderCircuitState,
    ServiceApiKey,
    Subscription,
    Tenant,
    UsageLedgerEntry,
    WebhookDelivery,
    WebhookEvent,
)
from ..platform_rbac import require_platform_role

router = APIRouter(prefix="/v1/ops", tags=["operations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _operator(request: Request, db: Session = Depends(get_db)) -> PanelUser:
    user = get_current_platform_user(request, db)
    return require_platform_role(
        user,
        "platform_superadmin",
        "platform_operator",
        "platform_support",
    )


def _count(db: Session, model, *criteria) -> int:
    statement = select(func.count()).select_from(model)
    if criteria:
        statement = statement.where(*criteria)
    return int(db.scalar(statement) or 0)


def _safe_datetime(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


@router.get("/overview")
def overview(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "services": {
            "control_plane": "online",
            "meta_cloud": "adapter_ready",
            "evolution": "provider_separate",
            "manager": "private_target",
        },
        "counts": {
            "tenants": _count(db, Tenant),
            "projects": _count(db, PlatformProject),
            "resources": _count(db, ProviderResource),
            "active_api_keys": _count(db, ServiceApiKey, ServiceApiKey.status == "active"),
            "conversations": _count(db, Conversation),
            "usage_entries": _count(db, UsageLedgerEntry),
            "webhook_events": _count(db, WebhookEvent),
            "webhook_deliveries_pending": _count(db, WebhookDelivery, WebhookDelivery.status.in_(("pending", "retrying"))),
            "welcome_pending": _count(db, OwnerWelcomeDelivery, OwnerWelcomeDelivery.status.in_(("pending", "retrying"))),
            "email_pending": _count(db, EmailDelivery, EmailDelivery.status.in_(("pending", "sending"))),
            "email_failed": _count(db, EmailDelivery, EmailDelivery.status.in_(("failed", "dead_letter", "bounced", "complained"))),
            "subscriptions_active": _count(db, Subscription, Subscription.status.in_(("trialing", "active"))),
        },
        "security": {
            "tenant_scoped": True,
            "secrets_to_browser": False,
            "audit_append_only": True,
            "mfa": "pending_gate",
        },
    }


@router.get("/tenants")
def list_tenants(
    _: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
):
    rows = db.scalars(select(Tenant).order_by(Tenant.created_at.desc()).limit(limit)).all()
    return {
        "items": [
            {
                "uuid": str(row.tenant_uuid),
                "slug": row.slug,
                "legal_name": row.legal_name,
                "status": row.status,
                "plan_slug": row.plan_slug,
                "created_at": _safe_datetime(row.created_at),
            }
            for row in rows
        ]
    }


@router.get("/audit")
def list_audit(
    _: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=200),
):
    rows = db.scalars(select(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(limit)).all()
    return {
        "items": [
            {
                "uuid": str(row.event_uuid),
                "action": row.action,
                "resource_type": row.resource_type,
                "resource_id": row.resource_id,
                "outcome": row.outcome,
                "request_id": row.request_id,
                "tenant_id": row.tenant_id,
                "created_at": _safe_datetime(row.created_at),
            }
            for row in rows
        ]
    }


@router.get("/alerts")
def alerts(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    failed_webhooks = _count(db, WebhookDelivery, WebhookDelivery.status.in_(("failed", "dead_letter")))
    failed_welcome = _count(db, OwnerWelcomeDelivery, OwnerWelcomeDelivery.status.in_(("failed", "dead_letter")))
    failed_email = _count(db, EmailDelivery, EmailDelivery.status.in_(("failed", "dead_letter", "bounced", "complained")))
    open_circuits = _count(db, ProviderCircuitState, ProviderCircuitState.state == "open")
    items = []
    if failed_webhooks:
        items.append({"severity": "warning", "code": "webhook_delivery_failures", "count": failed_webhooks, "action": "inspect webhook DLQ"})
    if failed_welcome:
        items.append({"severity": "warning", "code": "owner_welcome_failures", "count": failed_welcome, "action": "inspect welcome DLQ"})
    if failed_email:
        items.append({"severity": "warning", "code": "email_delivery_failures", "count": failed_email, "action": "inspect email delivery DLQ and suppression"})
    if open_circuits:
        items.append({"severity": "critical", "code": "provider_circuit_open", "count": open_circuits, "action": "check provider health and cooldown"})
    return {"status": "alert" if items else "ok", "items": items, "generated_at": datetime.now(timezone.utc).isoformat()}


@router.get("/queues")
def queues(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    return {
        "webhooks": {
            "pending": _count(db, WebhookDelivery, WebhookDelivery.status.in_(("pending", "retrying"))),
            "failed": _count(db, WebhookDelivery, WebhookDelivery.status.in_(("failed", "dead_letter"))),
        },
        "owner_welcome": {
            "pending": _count(db, OwnerWelcomeDelivery, OwnerWelcomeDelivery.status.in_(("pending", "retrying"))),
            "failed": _count(db, OwnerWelcomeDelivery, OwnerWelcomeDelivery.status.in_(("failed", "dead_letter"))),
        },
        "email": {
            "pending": _count(db, EmailDelivery, EmailDelivery.status.in_(("pending", "sending"))),
            "sent": _count(db, EmailDelivery, EmailDelivery.status.in_(("sent", "delivered"))),
            "failed": _count(db, EmailDelivery, EmailDelivery.status.in_(("failed", "dead_letter", "bounced", "complained"))),
        },
        "note": "Provider operations remain behind adapters; no global token is returned.",
    }
