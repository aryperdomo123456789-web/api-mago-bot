from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_limits import issue_service_api_key
from ..platform_models import PlatformProject, ServiceApiKey
from ..platform_rbac import require_tenant_permission
from ..platform_schemas import ApiKeyCreateRequest, ApiKeyResponse

router = APIRouter(prefix="/v1/platform", tags=["platform-api-keys"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _serialize_key(row: ServiceApiKey, raw_token: str | None = None) -> ApiKeyResponse:
    return ApiKeyResponse(
        id=row.id,
        uuid=row.key_uuid,
        tenant_id=row.tenant_id,
        project_id=row.project_id,
        prefix=row.prefix,
        scopes=row.scopes or [],
        status=row.status,
        expires_at=row.expires_at,
        created_at=row.created_at,
        token=raw_token,
    )


def _get_project(db: Session, project_id: int, tenant_id: int) -> PlatformProject:
    project = db.scalar(select(PlatformProject).where(PlatformProject.id == project_id, PlatformProject.tenant_id == tenant_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


@router.post("/projects/{project_id}/keys", status_code=status.HTTP_201_CREATED)
def create_key(
    project_id: int,
    payload: ApiKeyCreateRequest,
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "key:manage")
    project = _get_project(db, project_id, tenant_id)
    if payload.expires_at and payload.expires_at <= _utcnow():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="expires_at must be in the future")

    raw_token, token_hash = issue_service_api_key()
    row = ServiceApiKey(
        tenant_id=tenant_id,
        project_id=project.id,
        prefix=raw_token[:16],
        token_hash=token_hash,
        scopes=payload.scopes or [
            "channels:read",
            "channels:write",
            "webhooks:read",
            "webhooks:write",
            "operations:read",
            "operations:write",
            "whatsapp:messages:send",
            "whatsapp:messages:read",
        ],
        expires_at=payload.expires_at,
        created_by=user.id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "key": _serialize_key(row, raw_token)}


@router.get("/projects/{project_id}/keys")
def list_keys(project_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "key:manage")
    project = _get_project(db, project_id, tenant_id)
    rows = db.scalars(
        select(ServiceApiKey)
        .where(ServiceApiKey.tenant_id == tenant_id, ServiceApiKey.project_id == project.id)
        .order_by(ServiceApiKey.id.desc())
    ).all()
    return {"items": [_serialize_key(row) for row in rows]}


@router.post("/keys/{key_id}/revoke")
def revoke_key(key_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "key:manage")
    row = db.scalar(select(ServiceApiKey).where(ServiceApiKey.id == key_id, ServiceApiKey.tenant_id == tenant_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="key not found")
    if row.status != "revoked":
        row.status = "revoked"
        row.revoked_at = _utcnow()
        db.commit()
    return {"ok": True, "key": _serialize_key(row)}
