from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..auth import clear_session_cookie, get_current_panel_user, hash_password, issue_session_token, set_session_cookie, verify_password
from ..db import SessionLocal
from ..models import OwnerProfile, PanelUser
from ..platform_models import AuditEvent
from ..schemas import (
    OwnerProfileResponse,
    OwnerProfileUpdate,
    PanelLoginRequest,
    PanelUserCreate,
    PanelUserResponse,
    PanelUserUpdate,
)

router = APIRouter(prefix="/v1", tags=["account"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_owner(user: PanelUser):
    if user.role != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="owner access required")


def _serialize_user(row: PanelUser) -> PanelUserResponse:
    return PanelUserResponse(
        id=row.id,
        email=row.email,
        full_name=row.full_name,
        role=row.role,
        is_active=row.is_active,
        notes=row.notes,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _serialize_profile(row: OwnerProfile) -> OwnerProfileResponse:
    return OwnerProfileResponse(
        display_name=row.display_name,
        company_name=row.company_name,
        email=row.email,
        phone=row.phone,
        bio=row.bio,
        updated_at=row.updated_at,
    )


@router.post("/auth/login")
def login(payload: PanelLoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.scalar(select(PanelUser).where(PanelUser.email == payload.email.strip().lower()))
    if not user or not user.is_active or not verify_password(payload.password, user.password_salt, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    set_session_cookie(response, user.id)
    return {"ok": True, "user": _serialize_user(user), "session_token": issue_session_token(user.id)}


@router.post("/auth/logout")
def logout(response: Response):
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/auth/me")
def me(request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    return {"user": _serialize_user(user)}


@router.get("/account")
def get_account(request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    _ensure_owner(user)
    profile = db.get(OwnerProfile, 1)
    if not profile:
        profile = OwnerProfile(id=1, display_name="Dono wp-api")
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return {"profile": _serialize_profile(profile), "owner": _serialize_user(user)}


@router.put("/account")
def update_account(payload: OwnerProfileUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    _ensure_owner(user)
    profile = db.get(OwnerProfile, 1)
    if not profile:
        profile = OwnerProfile(id=1)
        db.add(profile)
    profile.display_name = payload.display_name
    profile.company_name = payload.company_name
    profile.email = payload.email
    profile.phone = payload.phone
    profile.bio = payload.bio
    user.full_name = payload.display_name
    if payload.email:
        user.email = payload.email.strip().lower()
    db.add(AuditEvent(
        actor_user_id=user.id,
        action="legacy.account.update",
        resource_type="owner_profile",
        resource_id="1",
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        metadata_json={},
    ))
    db.commit()
    db.refresh(profile)
    return {"ok": True, "profile": _serialize_profile(profile)}


@router.get("/users")
def list_users(request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    _ensure_owner(user)
    rows = db.scalars(select(PanelUser).order_by(PanelUser.id.desc())).all()
    return {"items": [_serialize_user(row) for row in rows]}


@router.post("/users")
def create_user(payload: PanelUserCreate, request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    _ensure_owner(user)
    email = payload.email.strip().lower()
    if db.scalar(select(PanelUser).where(PanelUser.email == email)):
        raise HTTPException(status_code=409, detail="email already exists")
    salt, digest = hash_password(payload.password)
    row = PanelUser(
        email=email,
        password_salt=salt,
        password_hash=digest,
        full_name=payload.full_name,
        role=payload.role or "subscriber",
        notes=payload.notes,
    )
    db.add(row)
    db.flush()
    db.add(AuditEvent(
        actor_user_id=user.id,
        action="legacy.user.create",
        resource_type="panel_user",
        resource_id=str(row.id),
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        metadata_json={"role": row.role},
    ))
    db.commit()
    db.refresh(row)
    return {"ok": True, "user": _serialize_user(row)}


@router.put("/users/{user_id}")
def update_user(user_id: int, payload: PanelUserUpdate, request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    _ensure_owner(user)
    row = db.get(PanelUser, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    if payload.email is not None:
        row.email = payload.email.strip().lower()
    if payload.password:
        salt, digest = hash_password(payload.password)
        row.password_salt = salt
        row.password_hash = digest
    if payload.full_name is not None:
        row.full_name = payload.full_name
    if payload.role is not None:
        row.role = payload.role
    if payload.is_active is not None:
        row.is_active = payload.is_active
    if payload.notes is not None:
        row.notes = payload.notes
    db.add(AuditEvent(
        actor_user_id=user.id,
        action="legacy.user.update",
        resource_type="panel_user",
        resource_id=str(row.id),
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        metadata_json={},
    ))
    db.commit()
    db.refresh(row)
    return {"ok": True, "user": _serialize_user(row)}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_panel_user(request, db)
    _ensure_owner(user)
    row = db.get(PanelUser, user_id)
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    if row.role == "owner":
        raise HTTPException(status_code=400, detail="owner cannot be deleted")
    db.add(AuditEvent(
        actor_user_id=user.id,
        action="legacy.user.delete",
        resource_type="panel_user",
        resource_id=str(row.id),
        outcome="success",
        request_id=getattr(request.state, "request_id", None),
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        metadata_json={},
    ))
    db.delete(row)
    db.commit()
    return {"ok": True}
