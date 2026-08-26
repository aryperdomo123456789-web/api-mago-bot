from __future__ import annotations

import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_models import AuditEvent, EmailDelivery, EmailSenderIdentity
from ..platform_rbac import require_platform_role

router = APIRouter(prefix="/v1/ops/email", tags=["email-operations"])
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SenderCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender_email: str = Field(min_length=5, max_length=255)
    sender_name: str = Field(default="Mago Bot", min_length=1, max_length=180)
    reply_to: str | None = Field(default=None, max_length=255)


class SenderUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender_name: str | None = Field(default=None, min_length=1, max_length=180)
    reply_to: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _mutator(request: Request, db: Session = Depends(get_db)) -> PanelUser:
    user = get_current_platform_user(request, db)
    return require_platform_role(user, "platform_superadmin", "platform_operator")


def _operator(request: Request, db: Session = Depends(get_db)) -> PanelUser:
    user = get_current_platform_user(request, db)
    return require_platform_role(user, "platform_superadmin", "platform_operator", "platform_support")


def _allowed_domains() -> set[str]:
    raw = os.getenv("EMAIL_ALLOWED_SENDER_DOMAINS", "app.mago-bot.com")
    return {item.strip().lower().lstrip("@") for item in raw.split(",") if item.strip()}


def _normalize(value: str, *, field: str) -> str:
    normalized = value.strip().lower()
    if not _EMAIL_RE.fullmatch(normalized):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"invalid {field}")
    return normalized


def _check_domain(email: str) -> None:
    domain = email.rsplit("@", 1)[1]
    if domain not in _allowed_domains():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="sender domain is not allowed")


def _safe_datetime(value: datetime | None) -> str | None:
    return value.astimezone(timezone.utc).isoformat() if value else None


def _serialize(row: EmailSenderIdentity, delivery_count: int = 0) -> dict:
    return {
        "id": row.id,
        "uuid": str(row.sender_uuid),
        "sender_email": row.sender_email,
        "sender_name": row.sender_name,
        "reply_to": row.reply_to,
        "purpose": row.purpose,
        "status": row.status,
        "delivery_count": delivery_count,
        "created_at": _safe_datetime(row.created_at),
        "updated_at": _safe_datetime(row.updated_at),
    }


def _audit(db: Session, request: Request, actor: PanelUser, action: str, resource_id: int, metadata: dict | None = None) -> None:
    db.add(AuditEvent(
        tenant_id=None,
        actor_user_id=actor.id,
        action=action,
        resource_type="email_sender_identity",
        resource_id=str(resource_id),
        outcome="success",
        request_id=str(getattr(request.state, "request_id", ""))[:80] or None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        metadata_json=metadata or {},
    ))


@router.get("/senders")
def list_senders(request: Request, db: Session = Depends(get_db)):
    _operator(request, db)
    rows = db.scalars(select(EmailSenderIdentity).order_by(EmailSenderIdentity.id.asc())).all()
    items = []
    for row in rows:
        count = db.scalar(select(EmailDelivery.id).where(EmailDelivery.sender_identity_id == row.id).order_by(EmailDelivery.id.desc()).limit(1))
        items.append(_serialize(row, 1 if count else 0))
    return {"items": items, "allowed_domains": sorted(_allowed_domains()), "dry_run": os.getenv("RESEND_DRY_RUN", "true").lower() in {"1", "true", "yes", "on"}}


@router.post("/senders", status_code=status.HTTP_201_CREATED)
def create_sender(payload: SenderCreateRequest, request: Request, db: Session = Depends(get_db)):
    actor = _mutator(request, db)
    email = _normalize(payload.sender_email, field="sender_email")
    _check_domain(email)
    reply_to = _normalize(payload.reply_to, field="reply_to") if payload.reply_to else None
    if db.scalar(select(EmailSenderIdentity.id).where(EmailSenderIdentity.tenant_id.is_(None), EmailSenderIdentity.sender_email == email, EmailSenderIdentity.status == "active")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="sender already exists")
    row = EmailSenderIdentity(
        tenant_id=None,
        sender_email=email,
        sender_name=payload.sender_name.strip(),
        reply_to=reply_to,
        purpose="transactional",
        status="active",
    )
    db.add(row)
    db.flush()
    _audit(db, request, actor, "ops.email_sender.create", row.id, {"sender_email": email})
    db.commit()
    db.refresh(row)
    return {"ok": True, "sender": _serialize(row)}


@router.patch("/senders/{sender_id}")
def update_sender(sender_id: int, payload: SenderUpdateRequest, request: Request, db: Session = Depends(get_db)):
    actor = _mutator(request, db)
    row = db.get(EmailSenderIdentity, sender_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sender not found")
    if payload.sender_name is not None:
        row.sender_name = payload.sender_name.strip()
    if payload.reply_to is not None:
        row.reply_to = _normalize(payload.reply_to, field="reply_to") if payload.reply_to else None
    if payload.status is not None:
        row.status = payload.status
    _audit(db, request, actor, "ops.email_sender.update", row.id, {"status": row.status})
    db.commit()
    db.refresh(row)
    return {"ok": True, "sender": _serialize(row)}


@router.delete("/senders/{sender_id}")
def disable_sender(sender_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _mutator(request, db)
    row = db.get(EmailSenderIdentity, sender_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sender not found")
    row.status = "disabled"
    _audit(db, request, actor, "ops.email_sender.disable", row.id, {"sender_email": row.sender_email})
    db.commit()
    return {"ok": True, "status": "disabled"}
