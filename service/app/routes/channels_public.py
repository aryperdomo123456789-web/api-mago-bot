from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urljoin
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_crypto import decrypt_secret, encrypt_secret
from ..platform_models import AuditEvent, EvolutionInstance, PlatformProject, ProviderResource, Tenant
from ..platform_rbac import require_tenant_permission
from ..platform_ssrf import UnsafeWebhookEndpoint, validate_webhook_endpoint
from ..providers.base import ProviderError
from ..providers.evolution_management import EvolutionManagementAdapter

router = APIRouter(prefix="/v1", tags=["channels"])

_ALLOWED_FLAVORS = {"evolution_api", "evolution_go"}
_WRITE_PERMISSION = "resource:request"


class ChannelCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    display_name: str = Field(min_length=3, max_length=120)
    provider: Literal["evolution"] = "evolution"
    provider_flavor: Literal["evolution_api", "evolution_go"] = "evolution_api"
    webhook_url: AnyHttpUrl | None = None
    events: list[str] = Field(default_factory=lambda: ["MESSAGES_UPSERT", "CONNECTION_UPDATE"])
    pairing_phone: str | None = Field(default=None, min_length=8, max_length=24)


class ChannelActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    channel: dict
    provider: dict = Field(default_factory=dict)



def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _actor(request: Request, db: Session) -> PanelUser:
    return get_current_platform_user(request, db)


def _tenant_for_member(db: Session, actor: PanelUser, organization_id: UUID, *, write: bool) -> Tenant:
    tenant = db.scalar(select(Tenant).where(Tenant.tenant_uuid == organization_id, Tenant.status == "active"))
    if not tenant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
    require_tenant_permission(db, actor, tenant.id, _WRITE_PERMISSION if write else "resource:read")
    return tenant


def _project_for_member(db: Session, actor: PanelUser, tenant: Tenant, project_uuid: UUID) -> PlatformProject:
    project = db.scalar(select(PlatformProject).where(
        PlatformProject.project_uuid == project_uuid,
        PlatformProject.tenant_id == tenant.id,
        PlatformProject.status == "active",
    ))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project


def _channel_for_member(db: Session, actor: PanelUser, channel_uuid: UUID, *, write: bool) -> EvolutionInstance:
    row = db.scalar(select(EvolutionInstance).where(
        EvolutionInstance.instance_uuid == channel_uuid,
        EvolutionInstance.status != "deleted",
    ))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")
    tenant = db.get(Tenant, row.tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")
    require_tenant_permission(db, actor, tenant.id, _WRITE_PERMISSION if write else "resource:read")
    return row


def _audit(db: Session, request: Request, actor: PanelUser, row: EvolutionInstance | None, action: str, outcome: str = "success", reason: str | None = None) -> None:
    db.add(AuditEvent(
        tenant_id=row.tenant_id if row else None,
        actor_user_id=actor.id,
        action=action,
        resource_type="evolution_instance",
        resource_id=str(row.instance_uuid) if row else None,
        outcome=outcome,
        request_id=str(getattr(request.state, "request_id", ""))[:80] or None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        reason=reason[:512] if reason else None,
        metadata_json={"customer_scoped": True, "provider_flavor": row.provider_flavor} if row else {"customer_scoped": True},
    ))


def _secret(row: EvolutionInstance) -> str | None:
    return decrypt_secret(row.instance_token_encrypted) if row.instance_token_encrypted else None


def _public_webhook(row: EvolutionInstance) -> str | None:
    base = ""
    from os import getenv
    base = getenv("EVOLUTION_WEBHOOK_PUBLIC_URL", "").strip()
    if not base or not row.webhook_secret_encrypted:
        return None
    endpoint_secret = decrypt_secret(row.webhook_secret_encrypted)
    return urljoin(base.rstrip("/") + "/", f"v1/webhooks/evolution/{row.instance_uuid}/{endpoint_secret}")


def _view(row: EvolutionInstance, tenant: Tenant, project: PlatformProject) -> dict:
    return {
        "id": str(row.instance_uuid),
        "organization_id": str(tenant.tenant_uuid),
        "project_id": str(project.project_uuid),
        "display_name": row.instance_name,
        "provider": "evolution",
        "provider_flavor": row.provider_flavor,
        "provider_instance_id": row.instance_name,
        "status": row.status,
        "phone_number": row.display_phone_number,
        "last_seen_at": row.last_status_check_at,
        "last_error": {"code": row.last_error_code, "message": row.last_error_message} if row.last_error_code else None,
        "capabilities": _capabilities(row.provider_flavor, row.status),
        "webhook_configured": bool(row.webhook_url or row.webhook_secret_encrypted),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _capabilities(flavor: str, state: str) -> list[str]:
    if state != "connected":
        base = ["status", "qr", "connect", "reconnect", "disconnect", "webhooks"]
        if flavor == "evolution_go":
            base.append("pairing_code")
        return base
    return ["text", "image", "video", "audio", "document", "sticker", "status", "webhooks", "reconnect", "media"]


def _serialize_with_context(db: Session, row: EvolutionInstance) -> dict:
    tenant = db.get(Tenant, row.tenant_id)
    project = db.get(PlatformProject, row.project_id)
    if not tenant or not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")
    return _view(row, tenant, project)


@router.get("/organizations/{organization_id}/channels")
def list_channels(organization_id: UUID, request: Request, project_id: UUID | None = Query(default=None), db: Session = Depends(get_db)):
    actor = _actor(request, db)
    tenant = _tenant_for_member(db, actor, organization_id, write=False)
    query = select(EvolutionInstance).where(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.status != "deleted")
    if project_id:
        project = _project_for_member(db, actor, tenant, project_id)
        query = query.where(EvolutionInstance.project_id == project.id)
    rows = db.scalars(query.order_by(EvolutionInstance.created_at.desc())).all()
    return {"items": [_serialize_with_context(db, row) for row in rows]}


@router.post("/organizations/{organization_id}/channels", response_model=ChannelActionResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(organization_id: UUID, payload: ChannelCreateRequest, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    tenant = _tenant_for_member(db, actor, organization_id, write=True)
    project = _project_for_member(db, actor, tenant, payload.project_id)
    if payload.provider_flavor not in _ALLOWED_FLAVORS:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported Evolution provider flavor")
    if db.scalar(select(EvolutionInstance.id).where(
        EvolutionInstance.tenant_id == tenant.id,
        EvolutionInstance.project_id == project.id,
        EvolutionInstance.instance_name == payload.display_name.strip(),
        EvolutionInstance.status != "deleted",
    )):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="channel already exists")
    webhook_url = str(payload.webhook_url) if payload.webhook_url else None
    if webhook_url:
        try:
            webhook_url = validate_webhook_endpoint(webhook_url)
        except UnsafeWebhookEndpoint as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsafe webhook URL") from exc
    instance_token = secrets.token_urlsafe(32)
    webhook_secret = secrets.token_urlsafe(32)
    resource = ProviderResource(
        tenant_id=tenant.id,
        project_id=project.id,
        provider_type="evolution",
        provider_resource_id=payload.display_name.strip(),
        status="provisioning",
        display_name=payload.display_name.strip(),
        metadata_json={"managed": True, "customer_scoped": True, "provider_flavor": payload.provider_flavor},
    )
    db.add(resource)
    db.flush()
    row = EvolutionInstance(
        tenant_id=tenant.id,
        project_id=project.id,
        resource_id=resource.id,
        instance_name=payload.display_name.strip(),
        provider_flavor=payload.provider_flavor,
        instance_token_encrypted=encrypt_secret(instance_token),
        webhook_secret_encrypted=encrypt_secret(webhook_secret),
        webhook_url=webhook_url,
        subscribed_events=payload.events[:50],
        status="provisioning",
        created_by=actor.id,
        metadata_json={"customer_scoped": True, "pairing_requested": bool(payload.pairing_phone)},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        created = await EvolutionManagementAdapter(row.provider_flavor).create_instance(row.instance_name, instance_token)
        row.status = "created"
        resource.status = "active"
        db.commit()
        db.refresh(row)
    except ProviderError as exc:
        db.rollback()
        row = db.get(EvolutionInstance, row.id)
        resource = db.get(ProviderResource, row.resource_id) if row and row.resource_id else None
        if row:
            row.status = "failed"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
            if resource:
                resource.status = "error"
            _audit(db, request, actor, row, "channel.create", "failure", str(exc))
            db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc
    _audit(db, request, actor, row, "channel.create")
    db.commit()
    return {"ok": True, "channel": _serialize_with_context(db, row), "provider": created.get("provider", {})}


@router.get("/channels/{channel_id}")
def get_channel(channel_id: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=False)
    return {"channel": _serialize_with_context(db, row)}


@router.post("/channels/{channel_id}/connect", response_model=ChannelActionResponse)
async def connect_channel(channel_id: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=True)
    try:
        provider = await EvolutionManagementAdapter(row.provider_flavor).connect(row.instance_name, _secret(row) or "", webhook_url=row.webhook_url or _public_webhook(row), events=row.subscribed_events)
        row.status = "qr_pending" if provider.get("qrcode") or provider.get("code") else "connecting"
        row.last_error_code = None
        row.last_error_message = None
        _audit(db, request, actor, row, "channel.connect")
        db.commit()
        db.refresh(row)
        return {"ok": True, "channel": _serialize_with_context(db, row), "provider": provider}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "channel.connect", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/channels/{channel_id}/qr")
async def channel_qr(channel_id: UUID, request: Request, response: Response, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=True)
    try:
        result = await EvolutionManagementAdapter(row.provider_flavor).qr(row.instance_name, _secret(row))
        ttl = int(result.get("expires_in", 60))
        row.status = "qr_pending"
        row.qr_expires_at = _now() + timedelta(seconds=min(max(ttl, 15), 300))
        row.last_error_code = None
        row.last_error_message = None
        _audit(db, request, actor, row, "channel.qr")
        db.commit()
        response.headers["Cache-Control"] = "no-store, private"
        return {"ok": True, "channel_id": row.instance_uuid, "expires_at": row.qr_expires_at, "qrcode": result.get("qrcode")}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "channel.qr", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/channels/{channel_id}/status")
async def channel_status(channel_id: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=False)
    try:
        checked = await EvolutionManagementAdapter(row.provider_flavor).status(row.instance_name, _secret(row))
        row.status = checked.get("status", "degraded")
        row.jid = checked.get("jid") or row.jid
        row.display_phone_number = checked.get("phone") or row.display_phone_number
        row.last_status_check_at = _now()
        row.last_error_code = None
        row.last_error_message = None
        db.commit()
        db.refresh(row)
        return {"channel": _serialize_with_context(db, row), "status": checked}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_status_check_at = _now()
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/channels/{channel_id}/reconnect", response_model=ChannelActionResponse)
async def reconnect_channel(channel_id: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=True)
    try:
        provider = await EvolutionManagementAdapter(row.provider_flavor).reconnect(row.instance_name, _secret(row))
        row.status = "connecting"
        _audit(db, request, actor, row, "channel.reconnect")
        db.commit()
        db.refresh(row)
        return {"ok": True, "channel": _serialize_with_context(db, row), "provider": provider}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "channel.reconnect", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/channels/{channel_id}/disconnect", response_model=ChannelActionResponse)
async def disconnect_channel(channel_id: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=True)
    try:
        provider = await EvolutionManagementAdapter(row.provider_flavor).disconnect(row.instance_name, _secret(row))
        row.status = "disconnected"
        _audit(db, request, actor, row, "channel.disconnect")
        db.commit()
        db.refresh(row)
        return {"ok": True, "channel": _serialize_with_context(db, row), "provider": provider}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "channel.disconnect", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.delete("/channels/{channel_id}")
async def delete_channel(channel_id: UUID, request: Request, db: Session = Depends(get_db)):
    actor = _actor(request, db)
    row = _channel_for_member(db, actor, channel_id, write=True)
    try:
        await EvolutionManagementAdapter(row.provider_flavor).delete(row.instance_name)
    except ProviderError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc
    row.status = "deleted"
    resource = db.get(ProviderResource, row.resource_id) if row.resource_id else None
    if resource:
        resource.status = "deleted"
    _audit(db, request, actor, row, "channel.delete")
    db.commit()
    return {"ok": True, "channel_id": channel_id, "status": "deleted"}
