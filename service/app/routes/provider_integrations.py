from __future__ import annotations

import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_crypto import encrypt_secret
from ..platform_models import AuditEvent, PlatformProject, ProviderIntegration, ProviderResource, Tenant, TenantMembership
from ..provider_integration_schemas import ProviderIntegrationCreateRequest

router = APIRouter(prefix="/v1/integrations", tags=["provider-integrations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(request: Request, db: Session) -> PanelUser:
    return get_current_platform_user(request, db)


def _membership(db: Session, user_id: int, tenant_id: int) -> TenantMembership:
    membership = db.scalar(select(TenantMembership).where(
        TenantMembership.user_id == user_id,
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.status == "active",
    ))
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
    if membership.role not in {"tenant_owner", "tenant_admin", "tenant_developer"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="integration management is not allowed")
    return membership


def _project(db: Session, tenant_id: int, project_id: int) -> PlatformProject:
    row = db.scalar(select(PlatformProject).where(
        PlatformProject.id == project_id,
        PlatformProject.tenant_id == tenant_id,
        PlatformProject.status == "active",
    ))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return row


def _view(row: ProviderIntegration, tenant: Tenant) -> dict:
    return {
        "id": str(row.integration_uuid),
        "organization_id": str(tenant.tenant_uuid),
        "project_id": str(row.project_id),
        "provider_type": row.provider_type,
        "display_name": row.display_name,
        "external_resource_id": row.external_resource_id,
        "status": row.status,
        "is_primary": row.is_primary,
        "credentials_configured": bool(row.credentials_encrypted),
        "last_tested_at": row.last_tested_at,
        "last_error": row.last_error,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _audit(db: Session, request: Request, actor: PanelUser, tenant_id: int, action: str, resource_id: str, outcome: str = "success", reason: str | None = None) -> None:
    db.add(AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor.id,
        action=action,
        resource_type="provider_integration",
        resource_id=resource_id,
        outcome=outcome,
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=(request.headers.get("user-agent") or "")[:512],
        reason=reason,
        metadata_json={"secrets": "redacted"},
    ))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_integration(
    payload: ProviderIntegrationCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = _user(request, db)
    _membership(db, actor.id, payload.tenant_id)
    project = _project(db, payload.tenant_id, payload.project_id)
    credentials = payload.credential_payload()
    required_key = "access_token" if payload.provider_type == "meta_cloud" else "instance_token"
    if required_key not in credentials:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{required_key} is required")
    if payload.provider_type == "meta_cloud" and not payload.external_resource_id.isdigit():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Meta external_resource_id must be a numeric Phone Number ID")
    if payload.provider_type == "evolution" and payload.external_resource_id != payload.external_resource_id.strip():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid Evolution instance id")
    existing = db.scalar(select(ProviderIntegration).where(
        ProviderIntegration.project_id == project.id,
        ProviderIntegration.provider_type == payload.provider_type,
        ProviderIntegration.external_resource_id == payload.external_resource_id,
        ProviderIntegration.status != "disabled",
    ))
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="integration already exists")
    resource = db.scalar(select(ProviderResource).where(
        ProviderResource.tenant_id == payload.tenant_id,
        ProviderResource.project_id == payload.project_id,
        ProviderResource.provider_type == payload.provider_type,
        ProviderResource.provider_resource_id == payload.external_resource_id,
        ProviderResource.status == "active",
    ))
    if not resource:
        resource = ProviderResource(
            tenant_id=payload.tenant_id,
            project_id=payload.project_id,
            provider_type=payload.provider_type,
            provider_resource_id=payload.external_resource_id,
            status="active",
            display_name=payload.display_name,
            metadata_json={"managed_integration": True},
        )
        db.add(resource)
        db.flush()
    integration = ProviderIntegration(
        tenant_id=payload.tenant_id,
        project_id=payload.project_id,
        provider_type=payload.provider_type,
        display_name=payload.display_name,
        external_resource_id=payload.external_resource_id,
        credentials_encrypted=encrypt_secret(json.dumps(credentials, separators=(",", ":"))),
        status="active",
        is_primary=True,
        created_by=actor.id,
        metadata_json={"api_version": payload.api_version, "resource_id": resource.id, "secrets": "encrypted"},
    )
    db.add(integration)
    try:
        db.flush()
        _audit(db, request, actor, payload.tenant_id, "provider.integration.create", str(integration.integration_uuid))
        db.commit()
        db.refresh(integration)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="integration could not be created") from exc
    tenant = db.get(Tenant, payload.tenant_id)
    return {"ok": True, "integration": _view(integration, tenant)}


@router.delete("/{integration_uuid}")
def disable_integration(integration_uuid: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    row = db.scalar(select(ProviderIntegration).where(ProviderIntegration.integration_uuid == integration_uuid))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="integration not found")
    _membership(db, actor.id, row.tenant_id)
    row.status = "disabled"
    row.is_primary = False
    row.updated_at = _now()
    _audit(db, request, actor, row.tenant_id, "provider.integration.disable", str(row.integration_uuid))
    db.commit()
    return {"ok": True, "status": "disabled", "id": str(row.integration_uuid)}
