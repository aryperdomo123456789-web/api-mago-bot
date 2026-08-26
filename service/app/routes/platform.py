from __future__ import annotations

import hashlib
import os
import secrets
import re
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import hash_password, verify_password
from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import (
    clear_platform_session_cookie,
    get_current_platform_session,
    get_current_platform_user,
    hash_session_token,
    issue_platform_session,
    revoke_all_platform_sessions,
    revoke_current_platform_session,
    set_platform_session_cookie,
)
from ..platform_models import AuthToken, PlatformProject, Subscription, Tenant, TenantMembership
from ..platform_rbac import PLATFORM_ROLES, get_membership, require_platform_role, require_tenant_permission
from ..surface_auth import enforce_login_surface, require_customer_surface
from ..platform_crypto import decrypt_secret
from ..platform_mfa import consume_recovery_code, verify_totp
from ..owner_welcome import enqueue_owner_welcome
from ..platform_schemas import (
    MembershipResponse,
    PasswordResetConfirmRequest,
    PasswordResetRequest,
    PlatformLoginRequest,
    PlatformSignupRequest,
    PlatformUserResponse,
    ProjectCreateRequest,
    ProjectResponse,
    TenantResponse,
    VerifyEmailRequest,
)

router = APIRouter(prefix="/v1/platform", tags=["platform"])
TOKEN_TTL_HOURS = 24


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _allow_test_tokens() -> bool:
    return os.getenv("PLATFORM_EXPOSE_TEST_TOKENS", "false").lower() == "true"


def _mfa_enforced_for(user: PanelUser) -> bool:
    enforced = os.getenv("MFA_ENFORCE_PLATFORM", "false").lower() == "true"
    return enforced and user.role in PLATFORM_ROLES


def _issue_auth_token(db: Session, user_id: int, purpose: str) -> str:
    raw_token = secrets.token_urlsafe(48)
    db.add(
        AuthToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=_token_hash(raw_token),
            expires_at=_now() + timedelta(hours=TOKEN_TTL_HOURS),
        )
    )
    return raw_token


def _serialize_user(user: PanelUser) -> PlatformUserResponse:
    return PlatformUserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        email_verified=user.email_verified,
        mfa_enabled=user.mfa_enabled,
    )


def _serialize_tenant(tenant: Tenant) -> TenantResponse:
    return TenantResponse(
        id=tenant.id,
        uuid=tenant.tenant_uuid,
        slug=tenant.slug,
        legal_name=tenant.legal_name,
        status=tenant.status,
        plan_slug=tenant.plan_slug,
        created_at=tenant.created_at,
    )


def _serialize_project(project: PlatformProject) -> ProjectResponse:
    return ProjectResponse(
        id=project.id,
        uuid=project.project_uuid,
        tenant_id=project.tenant_id,
        name=project.name,
        slug=project.slug,
        status=project.status,
        provider_type=project.provider_type,
        description=project.description,
        created_at=project.created_at,
    )


def _slugify_company(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug[:80] or "tenant"


def _unique_tenant_slug(db: Session, requested: str | None, company_name: str) -> str:
    base = requested or _slugify_company(company_name)
    candidate = base
    suffix = 2
    while db.scalar(select(Tenant.id).where(Tenant.slug == candidate)) is not None:
        suffix_text = f"-{suffix}"
        candidate = f"{base[:80-len(suffix_text)]}{suffix_text}"
        suffix += 1
    return candidate


@router.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: PlatformSignupRequest, request: Request, db: Session = Depends(get_db)):
    require_customer_surface(request)
    email = payload.email
    if db.scalar(select(PanelUser.id).where(PanelUser.email == email)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="account already exists")

    salt, password_digest = hash_password(payload.password)
    user = PanelUser(
        email=email,
        password_salt=salt,
        password_hash=password_digest,
        full_name=payload.full_name.strip(),
        phone=payload.phone.strip() if payload.phone else None,
        whatsapp_opt_in=payload.whatsapp_opt_in,
        whatsapp_opt_in_source=payload.whatsapp_opt_in_source.strip()[:180] if payload.whatsapp_opt_in_source else None,
        whatsapp_opt_in_at=_now() if payload.whatsapp_opt_in else None,
        role="customer_common",
        is_active=True,
        email_verified=False,
    )
    tenant = Tenant(
        slug=_unique_tenant_slug(db, payload.tenant_slug, payload.company_name),
        legal_name=payload.company_name.strip(),
        billing_email=email,
        plan_slug="start",
        status="pending_verification",
    )
    db.add_all([user, tenant])
    try:
        db.flush()
        db.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role="tenant_owner", status="active"))
        now = _now()
        db.add(Subscription(
            tenant_id=tenant.id,
            plan_slug="start",
            status="trialing",
            current_period_start=now,
            current_period_end=now + timedelta(days=7),
        ))
        verification_token = _issue_auth_token(db, user.id, "email_verification")
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="account already exists") from exc

    result = {
        "ok": True,
        "verification_required": True,
        "message": "check your email to activate the account",
        "tenant": _serialize_tenant(tenant),
    }
    if _allow_test_tokens():
        result["verification_token"] = verification_token
    return result


@router.post("/auth/verify-email")
def verify_email(payload: VerifyEmailRequest, request: Request, db: Session = Depends(get_db)):
    require_customer_surface(request)
    token = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == _token_hash(payload.token),
            AuthToken.purpose == "email_verification",
            AuthToken.used_at.is_(None),
        )
    )
    if not token or token.expires_at <= _now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid or expired verification token")

    user = db.get(PanelUser, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid verification token")
    user.email_verified = True
    token.used_at = _now()
    tenant = db.scalar(
        select(Tenant)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .where(TenantMembership.user_id == user.id)
        .order_by(Tenant.id)
    )
    if tenant and tenant.status == "pending_verification":
        tenant.status = "active"
    enqueue_owner_welcome(
        db,
        source_type="platform_signup",
        source_id=str(user.id),
        recipient_phone=user.phone,
        recipient_name=user.full_name,
        opt_in=bool(user.whatsapp_opt_in),
        opt_in_source=user.whatsapp_opt_in_source,
    )
    db.commit()
    return {"ok": True, "email_verified": True}


@router.post("/auth/login")
def login(payload: PlatformLoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(PanelUser).where(PanelUser.email == payload.email))
    valid = bool(user and user.is_active and verify_password(payload.password, user.password_salt, user.password_hash))
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    enforce_login_surface(request, user.role if user else None)
    if not user.email_verified and user.role not in {"owner", "platform_superadmin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="email verification required")

    if user.mfa_enabled:
        if not payload.mfa_code:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="mfa code required")
        if not user.mfa_secret_encrypted:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="mfa unavailable")
        try:
            secret = decrypt_secret(user.mfa_secret_encrypted)
        except RuntimeError as exc:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="mfa unavailable") from exc
        factor_valid, counter = verify_totp(secret, payload.mfa_code)
        if factor_valid:
            if counter is None or user.mfa_last_used_counter == counter:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="mfa code already used")
            user.mfa_last_used_counter = counter
        else:
            consumed, remaining = consume_recovery_code(payload.mfa_code, list(user.mfa_recovery_hashes or []))
            if not consumed:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid mfa code")
            user.mfa_recovery_hashes = remaining
        db.commit()
    elif _mfa_enforced_for(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="mfa enrollment required")

    token = issue_platform_session(db, user, request)
    set_platform_session_cookie(response, token)
    memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == user.id, TenantMembership.status == "active")).all()
    return {
        "ok": True,
        "user": _serialize_user(user),
        "memberships": [MembershipResponse.model_validate(item) for item in memberships],
    }


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    revoke_current_platform_session(request, db)
    clear_platform_session_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    memberships = db.scalars(select(TenantMembership).where(TenantMembership.user_id == user.id, TenantMembership.status == "active")).all()
    return {
        "user": _serialize_user(user),
        "memberships": [MembershipResponse.model_validate(item) for item in memberships],
    }


@router.post("/auth/password-reset/request")
def password_reset_request(payload: PasswordResetRequest, request: Request, db: Session = Depends(get_db)):
    require_customer_surface(request)
    user = db.scalar(select(PanelUser).where(PanelUser.email == payload.email))
    result = {"ok": True, "message": "if the account exists, a reset email will be sent"}
    if user and user.is_active:
        reset_token = _issue_auth_token(db, user.id, "password_reset")
        db.commit()
        if _allow_test_tokens():
            result["reset_token"] = reset_token
    return result


@router.post("/auth/password-reset/confirm")
def password_reset_confirm(payload: PasswordResetConfirmRequest, request: Request, db: Session = Depends(get_db)):
    require_customer_surface(request)
    token = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == _token_hash(payload.token),
            AuthToken.purpose == "password_reset",
            AuthToken.used_at.is_(None),
        )
    )
    if not token or token.expires_at <= _now():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid or expired reset token")
    user = db.get(PanelUser, token.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid reset token")
    salt, digest = hash_password(payload.password)
    user.password_salt = salt
    user.password_hash = digest
    user.password_changed_at = _now()
    token.used_at = _now()
    db.commit()
    revoked = revoke_all_platform_sessions(db, user.id)
    return {"ok": True, "sessions_revoked": revoked}


@router.get("/tenants/me")
def current_tenants(request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    tenants = db.scalars(
        select(Tenant)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .where(TenantMembership.user_id == user.id, TenantMembership.status == "active")
        .order_by(Tenant.id)
    ).all()
    return {"items": [_serialize_tenant(item) for item in tenants]}


@router.get("/tenants")
def list_tenants(request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_platform_role(user, "platform_superadmin", "platform_operator", "platform_support")
    tenants = db.scalars(select(Tenant).order_by(Tenant.id.desc())).all()
    return {"items": [_serialize_tenant(item) for item in tenants]}


def _authorized_tenant_id(request: Request, db: Session, user: PanelUser, tenant_id: int) -> int:
    require_tenant_permission(db, user, tenant_id, "project:read")
    return tenant_id


@router.get("/projects")
def list_projects(tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    _authorized_tenant_id(request, db, user, tenant_id)
    projects = db.scalars(
        select(PlatformProject).where(PlatformProject.tenant_id == tenant_id).order_by(PlatformProject.id.desc())
    ).all()
    return {"items": [_serialize_project(item) for item in projects]}


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreateRequest, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "project:write")
    if db.scalar(select(PlatformProject.id).where(PlatformProject.tenant_id == tenant_id, PlatformProject.slug == payload.slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="project slug already exists")
    project = PlatformProject(
        tenant_id=tenant_id,
        name=payload.name.strip(),
        slug=payload.slug,
        provider_type=payload.provider_type,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"ok": True, "project": _serialize_project(project)}
