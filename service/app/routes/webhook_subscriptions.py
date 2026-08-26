from __future__ import annotations

import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..platform_auth import get_current_platform_user
from ..platform_crypto import encrypt_secret
from ..platform_models import PlatformProject, WebhookSubscription
from ..platform_rbac import require_tenant_permission
from ..platform_schemas import WebhookSubscriptionCreateRequest, WebhookSubscriptionResponse
from ..platform_ssrf import UnsafeWebhookEndpoint, validate_webhook_endpoint

router = APIRouter(prefix="/v1/platform", tags=["webhook-subscriptions"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _secret() -> str:
    return "whsec_" + secrets.token_urlsafe(32)


def _serialize(row: WebhookSubscription, secret: str | None = None) -> WebhookSubscriptionResponse:
    return WebhookSubscriptionResponse(
        id=row.id,
        uuid=row.subscription_uuid,
        tenant_id=row.tenant_id,
        project_id=row.project_id,
        endpoint_url=row.endpoint_url,
        events=row.events or [],
        status=row.status,
        failure_count=row.failure_count,
        last_delivery_at=row.last_delivery_at,
        created_at=row.created_at,
        secret=secret,
    )


def _project(db: Session, project_id: int, tenant_id: int) -> PlatformProject:
    project = db.scalar(select(PlatformProject).where(PlatformProject.id == project_id, PlatformProject.tenant_id == tenant_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


@router.post("/projects/{project_id}/webhooks", status_code=status.HTTP_201_CREATED)
def create_webhook(
    project_id: int,
    payload: WebhookSubscriptionCreateRequest,
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "webhook:manage")
    project = _project(db, project_id, tenant_id)
    try:
        endpoint_url = validate_webhook_endpoint(payload.endpoint_url)
    except UnsafeWebhookEndpoint as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "unsafe_webhook_endpoint", "message": str(exc)}) from exc
    raw_secret = _secret()
    row = WebhookSubscription(
        tenant_id=tenant_id,
        project_id=project.id,
        endpoint_url=endpoint_url,
        secret_encrypted=encrypt_secret(raw_secret),
        events=payload.events,
        status="active",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "webhook": _serialize(row, raw_secret), "secret_warning": "store this secret now; it will not be shown again"}


@router.get("/projects/{project_id}/webhooks")
def list_webhooks(project_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "webhook:read")
    project = _project(db, project_id, tenant_id)
    rows = db.scalars(
        select(WebhookSubscription)
        .where(WebhookSubscription.tenant_id == tenant_id, WebhookSubscription.project_id == project.id)
        .order_by(WebhookSubscription.id.desc())
    ).all()
    return {"items": [_serialize(row) for row in rows]}


@router.post("/webhooks/{webhook_id}/rotate")
def rotate_webhook(webhook_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "webhook:manage")
    row = db.scalar(select(WebhookSubscription).where(WebhookSubscription.id == webhook_id, WebhookSubscription.tenant_id == tenant_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="webhook not found")
    raw_secret = _secret()
    row.secret_encrypted = encrypt_secret(raw_secret)
    row.failure_count = 0
    row.status = "active"
    db.commit()
    return {"ok": True, "webhook": _serialize(row, raw_secret), "secret_warning": "store this secret now; it will not be shown again"}


@router.post("/webhooks/{webhook_id}/disable")
def disable_webhook(webhook_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "webhook:manage")
    row = db.scalar(select(WebhookSubscription).where(WebhookSubscription.id == webhook_id, WebhookSubscription.tenant_id == tenant_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="webhook not found")
    row.status = "disabled"
    db.commit()
    return {"ok": True, "webhook": _serialize(row)}
