from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from ..auth import hash_password
from ..db import SessionLocal
from ..models import (
    CustomerAccount,
    LicenseAuditLog,
    LicenseKey,
    LicenseProject,
    OwnerProfile,
    PartnerApplication,
    PanelUser,
    PlanCatalog,
)
from ..platform_auth import get_current_platform_user
from ..platform_models import AuditEvent, PlatformProject, ProviderResource, Tenant, TenantMembership
from ..platform_rbac import require_platform_role
from ..schemas import LicenseValidateRequest
from ..ops_admin_schemas import (
    AdminCustomerUpdate,
    AdminLicenseCreate,
    AdminLicenseValidation,
    AdminPartnerUpdate,
    AdminPlanUpdate,
    AdminProjectCreate,
    AdminProjectUpdate,
    AdminUserCreate,
    AdminUserUpdate,
    OwnerProfileAdminUpdate,
)

router = APIRouter(prefix="/v1/ops", tags=["operations-admin"])


# These routes are intentionally separate from routes.account/licenses/product.
# Legacy handlers remain available only through the operational hostname guard.
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


def _mutator(request: Request, db: Session = Depends(get_db)) -> PanelUser:
    user = _operator(request, db)
    if user.role not in {"owner", "platform_superadmin", "platform_operator"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mutation role required")
    return user


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _safe_datetime(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _request_id(request: Request) -> str | None:
    value = getattr(request.state, "request_id", None) or getattr(request.state, "trace_id", None)
    return str(value)[:80] if value else None


def _audit(
    db: Session,
    request: Request,
    actor: PanelUser,
    action: str,
    resource_type: str,
    resource_id: str | int | None,
    *,
    outcome: str = "success",
    reason: str | None = None,
    metadata: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            tenant_id=None,
            actor_user_id=actor.id,
            action=action,
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            outcome=outcome,
            request_id=_request_id(request),
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:512],
            reason=reason,
            metadata_json=metadata or {},
        )
    )


def _serialize_user(row: PanelUser) -> dict:
    return {
        "id": row.id,
        "email": row.email,
        "full_name": row.full_name,
        "phone": row.phone,
        "role": row.role,
        "is_active": row.is_active,
        "email_verified": row.email_verified,
        "mfa_enabled": row.mfa_enabled,
        "notes": row.notes,
        "created_at": _safe_datetime(row.created_at),
        "updated_at": _safe_datetime(row.updated_at),
    }


def _serialize_profile(row: OwnerProfile) -> dict:
    return {
        "display_name": row.display_name,
        "company_name": row.company_name,
        "email": row.email,
        "phone": row.phone,
        "bio": row.bio,
        "updated_at": _safe_datetime(row.updated_at),
    }


def _serialize_project(row: LicenseProject) -> dict:
    return {
        "id": row.id,
        "name": row.name,
        "slug": row.slug,
        "domain": row.domain,
        "description": row.description,
        "is_active": row.is_active,
        "created_at": _safe_datetime(row.created_at),
        "updated_at": _safe_datetime(row.updated_at),
    }


def _serialize_license(row: LicenseKey) -> dict:
    return {
        "id": row.id,
        "uuid": str(row.license_uuid),
        "label": row.label,
        "project_slug": row.project.slug if row.project else None,
        "scopes": list(row.scopes or []),
        "status": row.status,
        "expires_at": _safe_datetime(row.expires_at),
        "revoked_at": _safe_datetime(row.revoked_at),
        "last_used_at": _safe_datetime(row.last_used_at),
        "created_at": _safe_datetime(row.created_at),
    }


def _serialize_plan(row: PlanCatalog) -> dict:
    return {
        "slug": row.slug,
        "name": row.name,
        "subtitle": row.subtitle,
        "description": row.description,
        "price_cents": row.price_cents,
        "currency": row.currency,
        "trial_days": row.trial_days,
        "billing_period_days": row.billing_period_days,
        "max_instances": row.max_instances,
        "max_projects": row.max_projects,
        "max_keys": row.max_keys,
        "is_partner": row.is_partner,
        "is_active": row.is_active,
        "cta_label": row.cta_label,
        "features": list(row.features or []),
        "sort_order": row.sort_order,
        "created_at": _safe_datetime(row.created_at),
        "updated_at": _safe_datetime(row.updated_at),
    }


def _serialize_customer(row: CustomerAccount) -> dict:
    return {
        "id": row.id,
        "uuid": str(row.account_uuid),
        "email": row.email,
        "full_name": row.full_name,
        "company_name": row.company_name,
        "phone": row.phone,
        "website": row.website,
        "plan_slug": row.plan_slug,
        "status": row.status,
        "trial_ends_at": _safe_datetime(row.trial_ends_at),
        "activated_at": _safe_datetime(row.activated_at),
        "expires_at": _safe_datetime(row.expires_at),
        "license_project_id": row.license_project_id,
        "license_id": row.license_id,
        "notes": row.notes,
        "created_at": _safe_datetime(row.created_at),
        "updated_at": _safe_datetime(row.updated_at),
    }


def _serialize_partner(row: PartnerApplication) -> dict:
    return {
        "id": row.id,
        "company_name": row.company_name,
        "full_name": row.full_name,
        "email": row.email,
        "phone": row.phone,
        "website": row.website,
        "monthly_volume": row.monthly_volume,
        "message": row.message,
        "status": row.status,
        "reviewed_by": row.reviewed_by,
        "reviewed_at": _safe_datetime(row.reviewed_at),
        "created_at": _safe_datetime(row.created_at),
        "updated_at": _safe_datetime(row.updated_at),
    }


@router.get("/owner/profile")
def get_owner_profile(actor: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    profile = db.get(OwnerProfile, 1)
    if not profile:
        profile = OwnerProfile(id=1, display_name=actor.full_name, email=actor.email)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return {"profile": _serialize_profile(profile), "owner": _serialize_user(actor)}


@router.put("/owner/profile")
def update_owner_profile(
    payload: OwnerProfileAdminUpdate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    profile = db.get(OwnerProfile, 1)
    if not profile:
        profile = OwnerProfile(id=1)
        db.add(profile)
    profile.display_name = payload.display_name
    profile.company_name = payload.company_name
    profile.email = payload.email.strip().lower() if payload.email else None
    profile.phone = payload.phone
    profile.bio = payload.bio
    actor.full_name = payload.display_name
    _audit(db, request, actor, "owner.profile.update", "owner_profile", 1)
    db.commit()
    db.refresh(profile)
    return {"ok": True, "profile": _serialize_profile(profile)}


@router.get("/users")
def list_admin_users(
    _: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=500),
):
    rows = db.scalars(select(PanelUser).order_by(PanelUser.id.desc()).limit(limit)).all()
    return {"items": [_serialize_user(row) for row in rows]}


@router.post("/users", status_code=status.HTTP_201_CREATED)
def create_admin_user(
    payload: AdminUserCreate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    email = payload.email.strip().lower()
    if db.scalar(select(PanelUser).where(PanelUser.email == email)):
        raise HTTPException(status_code=409, detail="email already exists")
    salt, digest = hash_password(payload.password)
    row = PanelUser(
        email=email,
        password_salt=salt,
        password_hash=digest,
        full_name=payload.full_name.strip(),
        phone=payload.phone,
        role="customer_common",
        is_active=True,
        email_verified=False,
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    _audit(db, request, actor, "user.create", "panel_user", row.id, metadata={"role": row.role})
    db.commit()
    db.refresh(row)
    return {"ok": True, "user": _serialize_user(row)}


@router.patch("/users/{user_id}")
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.get(PanelUser, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    if row.role == "owner" and actor.role != "owner":
        raise HTTPException(status_code=403, detail="owner protected")
    if payload.role and payload.role != row.role and actor.role not in {"owner", "platform_superadmin"}:
        raise HTTPException(status_code=403, detail="role change requires superadmin")
    if payload.email is not None:
        normalized = payload.email.strip().lower()
        conflict = db.scalar(select(PanelUser).where(PanelUser.email == normalized, PanelUser.id != row.id))
        if conflict:
            raise HTTPException(status_code=409, detail="email already exists")
        row.email = normalized
    if payload.full_name is not None:
        row.full_name = payload.full_name.strip()
    if payload.password:
        row.password_salt, row.password_hash = hash_password(payload.password)
        row.password_changed_at = _now()
    if payload.phone is not None:
        row.phone = payload.phone
    if payload.role is not None:
        row.role = payload.role
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.notes is not None:
        row.notes = payload.notes
    _audit(db, request, actor, "user.update", "panel_user", row.id)
    db.commit()
    db.refresh(row)
    return {"ok": True, "user": _serialize_user(row)}


@router.delete("/users/{user_id}")
def delete_admin_user(
    user_id: int,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.get(PanelUser, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    if row.role == "owner":
        raise HTTPException(status_code=400, detail="owner cannot be deleted")
    _audit(db, request, actor, "user.delete", "panel_user", row.id)
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/license-projects")
def list_admin_license_projects(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    rows = db.scalars(select(LicenseProject).order_by(LicenseProject.id.desc())).all()
    return {"items": [_serialize_project(row) for row in rows]}


@router.post("/license-projects", status_code=status.HTTP_201_CREATED)
def create_admin_license_project(
    payload: AdminProjectCreate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    if db.scalar(select(LicenseProject).where(LicenseProject.slug == payload.slug)):
        raise HTTPException(status_code=409, detail="project slug already exists")
    row = LicenseProject(
        name=payload.name.strip(),
        slug=payload.slug,
        domain=payload.domain,
        description=payload.description,
    )
    db.add(row)
    db.flush()
    _audit(db, request, actor, "license_project.create", "license_project", row.id)
    db.commit()
    db.refresh(row)
    return {"ok": True, "project": _serialize_project(row)}


@router.patch("/license-projects/{project_id}")
def update_admin_license_project(
    project_id: int,
    payload: AdminProjectUpdate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.get(LicenseProject, project_id)
    if not row:
        raise HTTPException(status_code=404, detail="project not found")
    if payload.name is not None:
        row.name = payload.name.strip()
    if payload.domain is not None:
        row.domain = payload.domain
    if payload.description is not None:
        row.description = payload.description
    if payload.is_active is not None:
        row.is_active = payload.is_active
    _audit(db, request, actor, "license_project.update", "license_project", row.id)
    db.commit()
    db.refresh(row)
    return {"ok": True, "project": _serialize_project(row)}


@router.get("/licenses")
def list_admin_licenses(
    _: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
    project_slug: str | None = None,
    status_filter: str | None = None,
    limit: int = Query(default=200, ge=1, le=500),
):
    statement = select(LicenseKey).options(selectinload(LicenseKey.project)).order_by(LicenseKey.id.desc()).limit(limit)
    if project_slug:
        statement = statement.join(LicenseProject).where(LicenseProject.slug == project_slug)
    if status_filter:
        statement = statement.where(LicenseKey.status == status_filter)
    rows = db.scalars(statement).all()
    return {"items": [_serialize_license(row) for row in rows]}


@router.post("/licenses", status_code=status.HTTP_201_CREATED)
def create_admin_license(
    payload: AdminLicenseCreate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    project = db.scalar(select(LicenseProject).where(LicenseProject.slug == payload.project_slug))
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    token = secrets.token_urlsafe(36)
    row = LicenseKey(
        label=payload.label.strip(),
        project_id=project.id,
        project=project,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        scopes=payload.scopes,
        status="active",
        expires_at=payload.expires_at,
        created_by=payload.created_by or actor.email,
        notes=payload.notes,
        extra_metadata=payload.metadata,
    )
    db.add(row)
    db.flush()
    db.add(LicenseAuditLog(license_id=row.id, action="issued", status_before=None, status_after="active", actor=actor.email, ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"), payload={"project_slug": project.slug, "scopes": payload.scopes}))
    _audit(db, request, actor, "license.create", "license", row.id, metadata={"project_slug": project.slug})
    db.commit()
    db.refresh(row)
    return {"ok": True, "token": token, "license": _serialize_license(row)}


@router.post("/licenses/validate")
def validate_admin_license(
    payload: AdminLicenseValidation,
    request: Request,
    actor: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
):
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    row = db.scalar(select(LicenseKey).options(selectinload(LicenseKey.project)).where(LicenseKey.token_hash == token_hash))
    if not row:
        return {"valid": False, "status": "not_found", "reason": "license not found"}
    now = _now()
    valid = row.status == "active" and not row.revoked_at and (not row.expires_at or row.expires_at > now)
    if payload.project_slug and (not row.project or row.project.slug != payload.project_slug):
        valid = False
    if payload.domain and (not row.project or row.project.domain != payload.domain):
        valid = False
    if payload.scope and payload.scope not in (row.scopes or []):
        valid = False
    _audit(db, request, actor, "license.validate", "license", row.id, metadata={"valid": valid})
    db.commit()
    return {"valid": valid, "status": "active" if valid else row.status, "license": _serialize_license(row)}


@router.post("/licenses/{license_id}/revoke")
def revoke_admin_license(
    license_id: int,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.get(LicenseKey, license_id)
    if not row:
        raise HTTPException(status_code=404, detail="license not found")
    previous = row.status
    row.status = "revoked"
    row.revoked_at = _now()
    db.add(LicenseAuditLog(license_id=row.id, action="revoked", status_before=previous, status_after=row.status, actor=actor.email, ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"), payload={}))
    _audit(db, request, actor, "license.revoke", "license", row.id)
    db.commit()
    return {"ok": True, "license": _serialize_license(row)}


@router.get("/plans")
def list_admin_plans(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    rows = db.scalars(select(PlanCatalog).order_by(PlanCatalog.sort_order.asc(), PlanCatalog.id.asc())).all()
    return {"items": [_serialize_plan(row) for row in rows]}


@router.patch("/plans/{slug}")
def update_admin_plan(
    slug: str,
    payload: AdminPlanUpdate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.scalar(select(PlanCatalog).where(PlanCatalog.slug == slug))
    if not row:
        raise HTTPException(status_code=404, detail="plan not found")
    for field in payload.model_fields_set:
        setattr(row, field, getattr(payload, field))
    _audit(db, request, actor, "plan.update", "plan", row.slug)
    db.commit()
    db.refresh(row)
    return {"ok": True, "plan": _serialize_plan(row)}


@router.get("/customers")
def list_admin_customers(
    _: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=500),
):
    rows = db.scalars(select(CustomerAccount).order_by(CustomerAccount.id.desc()).limit(limit)).all()
    return {"items": [_serialize_customer(row) for row in rows]}


@router.patch("/customers/{customer_id}")
def update_admin_customer(
    customer_id: int,
    payload: AdminCustomerUpdate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.get(CustomerAccount, customer_id)
    if not row:
        raise HTTPException(status_code=404, detail="customer not found")
    if payload.plan_slug is not None:
        if not db.scalar(select(PlanCatalog).where(PlanCatalog.slug == payload.plan_slug)):
            raise HTTPException(status_code=404, detail="plan not found")
        row.plan_slug = payload.plan_slug
    if payload.status is not None:
        row.status = payload.status
    if payload.notes is not None:
        row.notes = payload.notes
    _audit(db, request, actor, "customer.update", "customer", row.id, metadata={"status": row.status, "plan_slug": row.plan_slug})
    db.commit()
    db.refresh(row)
    return {"ok": True, "customer": _serialize_customer(row)}


@router.get("/partners")
def list_admin_partners(
    _: PanelUser = Depends(_operator),
    db: Session = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=500),
):
    rows = db.scalars(select(PartnerApplication).order_by(PartnerApplication.id.desc()).limit(limit)).all()
    return {"items": [_serialize_partner(row) for row in rows]}


@router.patch("/partners/{partner_id}")
def update_admin_partner(
    partner_id: int,
    payload: AdminPartnerUpdate,
    request: Request,
    actor: PanelUser = Depends(_mutator),
    db: Session = Depends(get_db),
):
    row = db.get(PartnerApplication, partner_id)
    if not row:
        raise HTTPException(status_code=404, detail="partner application not found")
    row.status = payload.status
    row.reviewed_by = actor.email
    row.reviewed_at = _now()
    _audit(db, request, actor, "partner.update", "partner_application", row.id, reason=payload.reason)
    db.commit()
    db.refresh(row)
    return {"ok": True, "application": _serialize_partner(row)}


@router.get("/stats")
def admin_stats(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    return {
        "generated_at": _now().isoformat(),
        "legacy": {
            "users": int(db.scalar(select(func.count()).select_from(PanelUser)) or 0),
            "customers": int(db.scalar(select(func.count()).select_from(CustomerAccount)) or 0),
            "projects": int(db.scalar(select(func.count()).select_from(LicenseProject)) or 0),
            "licenses": int(db.scalar(select(func.count()).select_from(LicenseKey)) or 0),
            "plans": int(db.scalar(select(func.count()).select_from(PlanCatalog)) or 0),
            "partners": int(db.scalar(select(func.count()).select_from(PartnerApplication)) or 0),
        },
        "platform": {
            "tenants": int(db.scalar(select(func.count()).select_from(Tenant)) or 0),
            "projects": int(db.scalar(select(func.count()).select_from(PlatformProject)) or 0),
            "resources": int(db.scalar(select(func.count()).select_from(ProviderResource)) or 0),
            "memberships": int(db.scalar(select(func.count()).select_from(TenantMembership)) or 0),
        },
    }


@router.get("/providers/evolution")
def evolution_status(_: PanelUser = Depends(_operator)):
    return {
        "provider": "evolution",
        "status": "adapter_separate",
        "manager_public": False,
        "credentials_to_browser": False,
        "note": "Evolution remains a provider adapter; operational credentials are server-side only.",
    }


@router.get("/usage")
def admin_usage(_: PanelUser = Depends(_operator), db: Session = Depends(get_db)):
    # The detailed ledger remains tenant-safe; this central view exposes only aggregates.
    from ..platform_models import UsageLedgerEntry

    rows = db.execute(
        select(UsageLedgerEntry.metric, func.sum(UsageLedgerEntry.units), func.sum(UsageLedgerEntry.cost_micros))
        .group_by(UsageLedgerEntry.metric)
        .order_by(UsageLedgerEntry.metric.asc())
    ).all()
    return {"items": [{"metric": metric, "units": int(units or 0), "cost_micros": int(cost or 0)} for metric, units, cost in rows]}
