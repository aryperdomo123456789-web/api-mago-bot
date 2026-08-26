from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_models import PlatformProject, ProviderResource, Subscription, Tenant, TenantMembership, WebhookSubscription
from ..onboarding_schemas import OnboardingSimulationRequest

router = APIRouter(prefix="/v1/onboarding", tags=["onboarding"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user(request: Request, db: Session) -> PanelUser:
    return get_current_platform_user(request, db)


def _tenant_membership(db: Session, user_id: int, tenant_id: int) -> TenantMembership:
    row = db.scalar(select(TenantMembership).where(
        TenantMembership.user_id == user_id,
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.status == "active",
    ))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
    return row


def _tenant_from_project(db: Session, project_id: int, user_id: int) -> tuple[Tenant, PlatformProject]:
    project = db.scalar(select(PlatformProject).where(PlatformProject.id == project_id, PlatformProject.status == "active"))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    _tenant_membership(db, user_id, project.tenant_id)
    tenant = db.get(Tenant, project.tenant_id)
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
    return tenant, project


@router.get("")
def onboarding_state(request: Request, project_id: int, db: Session = Depends(get_db)):
    user = _user(request, db)
    tenant, project = _tenant_from_project(db, project_id, user.id)
    resources = db.scalars(select(ProviderResource).where(
        ProviderResource.tenant_id == tenant.id,
        ProviderResource.project_id == project.id,
        ProviderResource.status == "active",
    )).all()
    subscription = db.scalar(select(Subscription).where(Subscription.tenant_id == tenant.id).order_by(Subscription.created_at.desc()))
    webhook = db.scalar(select(WebhookSubscription).where(
        WebhookSubscription.tenant_id == tenant.id,
        WebhookSubscription.project_id == project.id,
        WebhookSubscription.status == "active",
    ))
    steps = [
        {"key": "organization", "label": "Organização criada", "status": "complete"},
        {"key": "plan", "label": "Plano definido", "status": "complete" if subscription else "pending"},
        {"key": "channel", "label": "Canal conectado", "status": "complete" if resources else "pending"},
        {"key": "webhook", "label": "Webhook configurado", "status": "complete" if webhook else "pending"},
        {"key": "simulation", "label": "Primeiro teste simulado", "status": "pending", "action": "POST /v1/onboarding/simulate"},
    ]
    completed = sum(step["status"] == "complete" for step in steps)
    return {
        "organization": {"id": str(tenant.tenant_uuid), "name": tenant.legal_name, "plan": tenant.plan_slug},
        "project": {"id": str(project.project_uuid), "name": project.name, "provider": project.provider_type},
        "progress": {"completed": completed, "total": len(steps), "percent": round(completed / len(steps) * 100)},
        "steps": steps,
        "next_action": next((step for step in steps if step["status"] != "complete"), None),
    }


@router.post("/simulate")
def simulate_first_value(payload: OnboardingSimulationRequest, request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    tenant, project = _tenant_from_project(db, payload.project_id, user.id)
    if payload.provider_type not in {"evolution", "meta_cloud", "dry_run"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported provider type")
    resource = db.scalar(select(ProviderResource).where(
        ProviderResource.tenant_id == tenant.id,
        ProviderResource.project_id == project.id,
        ProviderResource.provider_type == payload.provider_type,
        ProviderResource.status == "active",
    ))
    return {
        "ok": True,
        "mode": "simulation",
        "would_send": False,
        "project_id": str(project.project_uuid),
        "provider": payload.provider_type,
        "resource_configured": bool(resource),
        "recipient_masked": payload.recipient[:3] + "***" + payload.recipient[-2:],
        "message_preview": payload.body[:160],
        "next_step": "Configure um resource ativo e use a API de mensagens com X-Idempotency-Key para envio real.",
    }
