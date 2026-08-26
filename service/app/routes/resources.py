from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_models import PlatformProject, ProviderResource
from ..platform_rbac import require_tenant_permission
from ..platform_schemas import ResourceCreateRequest, ResourceResponse

router = APIRouter(prefix="/v1/platform", tags=["platform-resources"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _serialize_resource(row: ProviderResource) -> ResourceResponse:
    return ResourceResponse(
        id=row.id,
        uuid=row.resource_uuid,
        tenant_id=row.tenant_id,
        project_id=row.project_id,
        provider_type=row.provider_type,
        provider_resource_id=row.provider_resource_id,
        status=row.status,
        display_name=row.display_name,
        created_at=row.created_at,
    )


def _get_project(db: Session, project_id: int, tenant_id: int) -> PlatformProject:
    project = db.scalar(select(PlatformProject).where(PlatformProject.id == project_id, PlatformProject.tenant_id == tenant_id))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


@router.get("/projects/{project_id}/resources")
def list_resources(project_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "resource:read")
    project = _get_project(db, project_id, tenant_id)
    rows = db.scalars(
        select(ProviderResource)
        .where(ProviderResource.tenant_id == tenant_id, ProviderResource.project_id == project.id)
        .order_by(ProviderResource.id.desc())
    ).all()
    return {"items": [_serialize_resource(row) for row in rows]}


@router.post("/projects/{project_id}/resources", status_code=status.HTTP_201_CREATED)
def create_resource(
    project_id: int,
    payload: ResourceCreateRequest,
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "resource:provision")
    project = _get_project(db, project_id, tenant_id)
    provider_type = payload.provider_type.strip().lower()
    if provider_type not in {"meta_cloud", "evolution", "dry_run"}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="provider type is not supported")
    if provider_type == "dry_run" and os.getenv("ALLOW_DRY_RUN_PROVIDER", "false").lower() != "true":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="dry_run provider is staging-only")
    resource = ProviderResource(
        tenant_id=tenant_id,
        project_id=project.id,
        provider_type=provider_type,
        provider_resource_id=payload.provider_resource_id.strip(),
        status="active",
        display_name=payload.display_name.strip(),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {"ok": True, "resource": _serialize_resource(resource)}


@router.post("/resources/{resource_id}/suspend")
def suspend_resource(resource_id: int, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "resource:operate")
    resource = db.scalar(select(ProviderResource).where(ProviderResource.id == resource_id, ProviderResource.tenant_id == tenant_id))
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    resource.status = "suspended"
    db.commit()
    return {"ok": True, "resource": _serialize_resource(resource)}
