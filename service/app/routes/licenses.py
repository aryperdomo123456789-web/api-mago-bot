from datetime import datetime, timezone
import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..auth import get_current_panel_user
from ..core.config import Settings
from ..db import SessionLocal
from ..models import LicenseAuditLog, LicenseKey, LicenseProject
from ..schemas import (
    LicenseCreate,
    LicenseResponse,
    LicenseValidateRequest,
    LicenseValidationResponse,
    ProjectCreate,
)

router = APIRouter(prefix="/v1/licenses", tags=["licenses"])
settings = Settings()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _require_admin(request: Request, db: Session):
    if not settings.api_admin_token:
        get_current_panel_user(request, db)
        return
    if request.headers.get("x-admin-token", "").strip() == settings.api_admin_token:
        return
    try:
        user = get_current_panel_user(request, db)
        if user.role == "owner":
            return
    except HTTPException:
        pass
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid admin token")


def _now():
    return datetime.now(timezone.utc)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _token_payload() -> str:
    return secrets.token_urlsafe(36)


def _serialize_license(row: LicenseKey) -> LicenseResponse:
    return LicenseResponse(
        id=row.id,
        uuid=row.license_uuid,
        label=row.label,
        project_slug=row.project.slug if row.project else "",
        scopes=list(row.scopes or []),
        status=row.status,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        last_used_at=row.last_used_at,
    )


def _serialize_project(row: LicenseProject):
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "domain": row.domain,
        "description": row.description,
        "is_active": row.is_active,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.post("/projects")
def create_project(payload: ProjectCreate, request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    existing = db.scalar(select(LicenseProject).where(LicenseProject.slug == payload.slug))
    if existing:
        raise HTTPException(status_code=409, detail="project slug already exists")

    project = LicenseProject(
        name=payload.name,
        slug=payload.slug,
        domain=payload.domain,
        description=payload.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"ok": True, "project": {"id": project.id, "slug": project.slug}}


@router.post("")
def issue_license(payload: LicenseCreate, request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    project = db.scalar(select(LicenseProject).where(LicenseProject.slug == payload.project_slug))
    if not project:
        raise HTTPException(status_code=404, detail="project not found")

    token = _token_payload()
    row = LicenseKey(
        license_uuid=uuid.uuid4(),
        label=payload.label,
        project_id=project.id,
        project=project,
        token_hash=_hash_token(token),
        scopes=payload.scopes,
        status="active",
        expires_at=payload.expires_at,
        created_by=payload.created_by,
        notes=payload.notes,
        extra_metadata=payload.metadata,
    )
    db.add(row)
    db.flush()
    db.add(
        LicenseAuditLog(
            license_id=row.id,
            action="issued",
            status_before=None,
            status_after="active",
            actor=payload.created_by or "system",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            payload={"project_slug": project.slug, "scopes": payload.scopes},
        )
    )
    db.commit()
    db.refresh(row)
    return {"ok": True, "token": token, "license": _serialize_license(row)}


@router.post("/validate", response_model=LicenseValidationResponse)
def validate_license(payload: LicenseValidateRequest, request: Request, db: Session = Depends(get_db)):
    token_hash = _hash_token(payload.token)
    row = db.scalar(
        select(LicenseKey)
        .options(selectinload(LicenseKey.project))
        .join(LicenseProject)
        .where(LicenseKey.token_hash == token_hash)
    )
    if not row:
        return LicenseValidationResponse(valid=False, status="not_found", reason="license not found")

    now = _now()
    if row.status != "active":
        return LicenseValidationResponse(valid=False, status=row.status, reason="license inactive", license=_serialize_license(row))
    if row.revoked_at:
        return LicenseValidationResponse(valid=False, status="revoked", reason="license revoked", license=_serialize_license(row))
    if row.expires_at and row.expires_at <= now:
        return LicenseValidationResponse(valid=False, status="expired", reason="license expired", license=_serialize_license(row))
    if payload.project_slug and row.project.slug != payload.project_slug:
        return LicenseValidationResponse(valid=False, status="project_mismatch", reason="project mismatch", license=_serialize_license(row))
    if payload.domain and row.project.domain and row.project.domain != payload.domain:
        return LicenseValidationResponse(valid=False, status="domain_mismatch", reason="domain mismatch", license=_serialize_license(row))
    if payload.scope and payload.scope not in (row.scopes or []):
        return LicenseValidationResponse(valid=False, status="scope_denied", reason="scope denied", license=_serialize_license(row))

    row.last_used_at = now
    db.add(
        LicenseAuditLog(
            license_id=row.id,
            action="validated",
            status_before=row.status,
            status_after=row.status,
            actor="client",
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            payload={"scope": payload.scope, "project_slug": payload.project_slug, "domain": payload.domain},
        )
    )
    db.commit()
    return LicenseValidationResponse(valid=True, status="active", license=_serialize_license(row))


@router.get("/projects")
def list_projects(request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    rows = db.scalars(select(LicenseProject).order_by(LicenseProject.id.desc())).all()
    return {"items": [_serialize_project(row) for row in rows]}


@router.get("")
def list_licenses(
    request: Request,
    db: Session = Depends(get_db),
    project_slug: str | None = None,
    status_filter: str | None = None,
    limit: int = 200,
):
    _require_admin(request, db)
    stmt = select(LicenseKey).options(selectinload(LicenseKey.project)).order_by(LicenseKey.id.desc()).limit(max(1, min(int(limit), 500)))
    if project_slug:
        stmt = stmt.join(LicenseProject).where(LicenseProject.slug == project_slug)
    if status_filter:
        stmt = stmt.where(LicenseKey.status == status_filter)
    rows = db.scalars(stmt).all()
    return {"items": [_serialize_license(row) for row in rows]}


@router.get("/{license_id}")
def get_license(license_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    row = db.scalar(
        select(LicenseKey)
        .options(selectinload(LicenseKey.project))
        .where(LicenseKey.id == license_id)
    )
    if not row:
        raise HTTPException(status_code=404, detail="license not found")
    return {"license": _serialize_license(row)}


@router.post("/{license_id}/revoke")
def revoke_license(license_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    row = db.get(LicenseKey, license_id)
    if not row:
        raise HTTPException(status_code=404, detail="license not found")
    previous = row.status
    row.status = "revoked"
    row.revoked_at = _now()
    db.add(
        LicenseAuditLog(
            license_id=row.id,
            action="revoked",
            status_before=previous,
            status_after=row.status,
            actor=request.headers.get("x-actor", "admin"),
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            payload={},
        )
    )
    db.commit()
    return {"ok": True, "license": _serialize_license(row)}


@router.post("/{license_id}/touch")
def touch_license(license_id: int, db: Session = Depends(get_db)):
    row = db.get(LicenseKey, license_id)
    if not row:
        raise HTTPException(status_code=404, detail="license not found")
    row.last_used_at = _now()
    db.commit()
    return {"ok": True}
