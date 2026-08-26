from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..core.config import Settings
from ..db import SessionLocal
from ..models import CustomerAccount, LicenseKey, LicenseProject, PartnerApplication, PlanCatalog
from ..schemas import (
    CustomerAccountResponse,
    PartnerApplicationCreate,
    PartnerApplicationResponse,
    PlanCatalogResponse,
    TrialActivationRequest,
    TrialCreateRequest,
)
from .licenses import (
    _require_admin,
    create_project as admin_create_project,
    get_license as admin_get_license,
    issue_license as admin_issue_license,
    list_licenses as admin_list_licenses,
    list_projects as admin_list_projects,
    revoke_license as admin_revoke_license,
    validate_license as admin_validate_license,
)
from ..schemas import LicenseCreate, LicenseValidateRequest, ProjectCreate

router = APIRouter(prefix="/v1", tags=["product"])
settings = Settings()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


def _short_code() -> str:
    return secrets.token_urlsafe(8).replace("-", "").replace("_", "")[:10].upper()


def _serialize_plan(row: PlanCatalog) -> PlanCatalogResponse:
    return PlanCatalogResponse(
        slug=row.slug,
        name=row.name,
        subtitle=row.subtitle,
        description=row.description,
        price_cents=row.price_cents,
        currency=row.currency,
        trial_days=row.trial_days,
        billing_period_days=row.billing_period_days,
        max_instances=row.max_instances,
        max_projects=row.max_projects,
        max_keys=row.max_keys,
        is_partner=row.is_partner,
        is_active=row.is_active,
        cta_label=row.cta_label,
        features=list(row.features or []),
        sort_order=row.sort_order,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _serialize_account(row: CustomerAccount) -> CustomerAccountResponse:
    return CustomerAccountResponse(
        id=row.id,
        account_uuid=row.account_uuid,
        email=row.email,
        full_name=row.full_name,
        company_name=row.company_name,
        phone=row.phone,
        website=row.website,
        plan_slug=row.plan_slug,
        status=row.status,
        activation_code_hint=row.activation_code_hint,
        trial_ends_at=row.trial_ends_at,
        activated_at=row.activated_at,
        expires_at=row.expires_at,
        license_project_id=row.license_project_id,
        license_id=row.license_id,
        notes=row.notes,
        metadata=dict(getattr(row, "extra_metadata", {}) or {}),
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _serialize_partner_application(row: PartnerApplication) -> PartnerApplicationResponse:
    return PartnerApplicationResponse(
        id=row.id,
        company_name=row.company_name,
        full_name=row.full_name,
        email=row.email,
        phone=row.phone,
        website=row.website,
        monthly_volume=row.monthly_volume,
        message=row.message,
        status=row.status,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_plan(db: Session, slug: str) -> PlanCatalog:
    plan = db.scalar(select(PlanCatalog).where(PlanCatalog.slug == slug, PlanCatalog.is_active.is_(True)))
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    return plan


def _ensure_unique_email(db: Session, email: str):
    existing = db.scalar(select(CustomerAccount).where(CustomerAccount.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="customer already exists")


@router.get("/plans")
def public_plans(db: Session = Depends(get_db)):
    rows = db.scalars(select(PlanCatalog).where(PlanCatalog.is_active.is_(True)).order_by(PlanCatalog.sort_order.asc(), PlanCatalog.id.asc())).all()
    return {"items": [_serialize_plan(row) for row in rows]}


@router.post("/trials")
def create_trial(payload: TrialCreateRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    _ensure_unique_email(db, email)
    plan = _get_plan(db, payload.plan_slug)
    if plan.is_partner:
        raise HTTPException(status_code=400, detail="partner plans require sales approval")

    activation_code = _short_code()
    trial_days = max(1, int(plan.trial_days or 7))
    expires_at = _now() + timedelta(days=trial_days)

    account = CustomerAccount(
        email=email,
        full_name=payload.full_name.strip(),
        company_name=payload.company_name.strip() if payload.company_name else None,
        phone=payload.phone.strip() if payload.phone else None,
        website=payload.website.strip() if payload.website else None,
        plan_slug=plan.slug,
        status="trialing",
        activation_code_hash=_hash_code(activation_code),
        activation_code_hint=activation_code[-4:],
        trial_ends_at=expires_at,
        expires_at=expires_at,
        notes=payload.notes,
        extra_metadata={"source": "public_home", "plan": plan.slug},
    )
    db.add(account)
    db.flush()

    project = LicenseProject(
        name=f"{payload.full_name.strip()} • {plan.name}",
        slug=f"{plan.slug}-{account.id}-{_short_code().lower()}",
        domain=payload.website.strip() if payload.website else None,
        description=f"Conta de teste para {payload.full_name.strip()}",
    )
    db.add(project)
    db.flush()

    token = secrets.token_urlsafe(36)
    license_row = LicenseKey(
        license_uuid=uuid.uuid4(),
        label=f"Trial {plan.name} / {payload.full_name.strip()}",
        project_id=project.id,
        project=project,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        scopes=list(settings.allowed_scopes),
        status="active",
        expires_at=expires_at,
        created_by="trial",
        notes=payload.notes,
        extra_metadata={"plan_slug": plan.slug, "trial": True},
    )
    db.add(license_row)
    db.flush()

    account.license_project_id = project.id
    account.license_id = license_row.id
    db.commit()
    db.refresh(account)
    db.refresh(license_row)

    return {
        "ok": True,
        "trial": _serialize_account(account),
        "project": {"id": project.id, "slug": project.slug, "name": project.name},
        "license": {
            "id": license_row.id,
            "uuid": license_row.license_uuid,
            "token": token,
            "status": license_row.status,
            "expires_at": license_row.expires_at,
            "scopes": list(license_row.scopes or []),
        },
        "activation_code": activation_code,
        "next_step": "use the token to validate the trial, then confirm activation with the code",
    }


@router.post("/trials/activate")
def activate_trial(payload: TrialActivationRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    account = db.scalar(select(CustomerAccount).where(CustomerAccount.email == email))
    if not account:
        raise HTTPException(status_code=404, detail="customer account not found")
    if not account.activation_code_hash or not secrets.compare_digest(account.activation_code_hash, _hash_code(payload.activation_code.strip().upper())):
        raise HTTPException(status_code=401, detail="invalid activation code")

    plan = _get_plan(db, account.plan_slug)
    now = _now()
    account.status = "active"
    account.activated_at = now
    account.expires_at = now + timedelta(days=max(1, int(plan.billing_period_days or 30)))

    if account.license_id:
        license_row = db.get(LicenseKey, account.license_id)
        if license_row:
            license_row.expires_at = account.expires_at
            license_row.status = "active"
            license_row.last_used_at = now
    db.commit()
    db.refresh(account)
    return {"ok": True, "account": _serialize_account(account)}


@router.post("/partners/apply")
def apply_partner(payload: PartnerApplicationCreate, db: Session = Depends(get_db)):
    row = PartnerApplication(
        company_name=payload.company_name.strip(),
        full_name=payload.full_name.strip(),
        email=payload.email.strip().lower(),
        phone=payload.phone.strip() if payload.phone else None,
        website=payload.website.strip() if payload.website else None,
        monthly_volume=payload.monthly_volume.strip() if payload.monthly_volume else None,
        message=payload.message,
        status="pending",
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"ok": True, "application": _serialize_partner_application(row)}


@router.get("/plans/catalog")
def admin_plan_catalog(request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    rows = db.scalars(select(PlanCatalog).order_by(PlanCatalog.sort_order.asc(), PlanCatalog.id.asc())).all()
    return {"items": [_serialize_plan(row) for row in rows]}


@router.get("/trials")
def list_trials(request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    rows = db.scalars(select(CustomerAccount).order_by(CustomerAccount.id.desc()).limit(200)).all()
    return {"items": [_serialize_account(row) for row in rows]}


@router.get("/partners/applications")
def list_partner_applications(request: Request, db: Session = Depends(get_db)):
    _require_admin(request, db)
    rows = db.scalars(select(PartnerApplication).order_by(PartnerApplication.id.desc()).limit(200)).all()
    return {"items": [_serialize_partner_application(row) for row in rows]}


# Compatibility wrappers for the existing licensing API naming.
@router.post("/projects")
def create_project_public(payload: ProjectCreate, request: Request, db: Session = Depends(get_db)):
    return admin_create_project(payload, request, db)


@router.get("/projects")
def list_projects_public(request: Request, db: Session = Depends(get_db)):
    return admin_list_projects(request, db)


@router.post("/keys")
def issue_license_public(payload: LicenseCreate, request: Request, db: Session = Depends(get_db)):
    return admin_issue_license(payload, request, db)


@router.post("/keys/validate")
def validate_license_public(payload: LicenseValidateRequest, request: Request, db: Session = Depends(get_db)):
    return admin_validate_license(payload, request, db)


@router.get("/keys")
def list_licenses_public(
    request: Request,
    db: Session = Depends(get_db),
    project_slug: str | None = None,
    status_filter: str | None = None,
    limit: int = 200,
):
    return admin_list_licenses(request, db, project_slug, status_filter, limit)


@router.get("/keys/{license_id}")
def get_license_public(license_id: int, request: Request, db: Session = Depends(get_db)):
    return admin_get_license(license_id, request, db)


@router.post("/keys/{license_id}/revoke")
def revoke_license_public(license_id: int, request: Request, db: Session = Depends(get_db)):
    return admin_revoke_license(license_id, request, db)
