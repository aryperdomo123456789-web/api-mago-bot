from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_crypto import decrypt_secret, encrypt_secret
from ..platform_models import AuditEvent, EvolutionInstance, PlatformProject, ProviderResource
from ..platform_rbac import require_platform_role
from ..platform_ssrf import UnsafeWebhookEndpoint, validate_webhook_endpoint
from ..providers.base import ProviderError
from ..providers.evolution_management import EvolutionManagementAdapter
from ..evolution_schemas import EvolutionActionResponse, EvolutionInstanceCreateRequest, EvolutionInstanceResponse, EvolutionPairRequest

router = APIRouter(prefix="/v1/ops/evolution", tags=["evolution-management"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _operator(request: Request, db: Session, *, write: bool = False) -> PanelUser:
    user = get_current_platform_user(request, db)
    if write:
        return require_platform_role(user, "platform_superadmin", "platform_operator")
    return require_platform_role(user, "platform_superadmin", "platform_operator", "platform_support")


def _audit(db: Session, request: Request, actor: PanelUser, instance: EvolutionInstance | None, action: str, outcome: str = "success", reason: str | None = None) -> None:
    db.add(AuditEvent(
        tenant_id=instance.tenant_id if instance else None,
        actor_user_id=actor.id,
        action=action,
        resource_type="evolution_instance",
        resource_id=str(instance.instance_uuid) if instance else None,
        outcome=outcome,
        request_id=str(getattr(request.state, "request_id", ""))[:80] or None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        reason=reason[:512] if reason else None,
        metadata_json={"provider_flavor": instance.provider_flavor} if instance else {},
    ))


def _serialize(row: EvolutionInstance) -> EvolutionInstanceResponse:
    return EvolutionInstanceResponse(
        id=row.id,
        uuid=row.instance_uuid,
        tenant_id=row.tenant_id,
        project_id=row.project_id,
        resource_id=row.resource_id,
        instance_name=row.instance_name,
        provider_flavor=row.provider_flavor,
        status=row.status,
        jid=row.jid,
        display_phone_number=row.display_phone_number,
        webhook_url=row.webhook_url,
        events=row.subscribed_events or [],
        last_status_check_at=row.last_status_check_at,
        last_connected_at=row.last_connected_at,
        last_sync_at=row.last_sync_at,
        qr_expires_at=row.qr_expires_at,
        last_error_code=row.last_error_code,
        last_error_message=row.last_error_message,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _get_instance(db: Session, instance_id: int) -> EvolutionInstance:
    row = db.get(EvolutionInstance, instance_id)
    if not row or row.status == "deleted":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evolution instance not found")
    return row


def _secret(row: EvolutionInstance) -> str | None:
    if not row.instance_token_encrypted:
        return None
    return decrypt_secret(row.instance_token_encrypted)


def _public_webhook_url(instance: EvolutionInstance) -> str | None:
    base = os.getenv("EVOLUTION_WEBHOOK_PUBLIC_URL", "").strip()
    if not base or not instance.webhook_secret_encrypted:
        return None
    base = base.rstrip("/") + "/"
    endpoint_secret = decrypt_secret(instance.webhook_secret_encrypted)
    return urljoin(base, f"v1/webhooks/evolution/{instance.instance_uuid}/{endpoint_secret}")


@router.get("/instances")
def list_instances(
    request: Request,
    tenant_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    _operator(request, db)
    query = select(EvolutionInstance).where(EvolutionInstance.status != "deleted")
    if tenant_id is not None:
        query = query.where(EvolutionInstance.tenant_id == tenant_id)
    rows = db.scalars(query.order_by(EvolutionInstance.id.desc())).all()
    return {"items": [_serialize(row) for row in rows]}


@router.post("/instances", status_code=status.HTTP_201_CREATED)
async def create_instance(
    payload: EvolutionInstanceCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    actor = _operator(request, db, write=True)
    project = db.scalar(select(PlatformProject).where(
        PlatformProject.id == payload.project_id,
        PlatformProject.tenant_id == payload.tenant_id,
        PlatformProject.status == "active",
    ))
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="active project not found")
    if db.scalar(select(EvolutionInstance.id).where(
        EvolutionInstance.project_id == payload.project_id,
        EvolutionInstance.instance_name == payload.instance_name,
        EvolutionInstance.status != "deleted",
    )):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="instance name already exists in project")
    webhook_url = payload.webhook_url
    if webhook_url:
        try:
            webhook_url = validate_webhook_endpoint(webhook_url)
        except UnsafeWebhookEndpoint as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsafe webhook URL") from exc

    instance_token = secrets.token_urlsafe(32)
    webhook_secret = secrets.token_urlsafe(32)
    resource = ProviderResource(
        tenant_id=payload.tenant_id,
        project_id=payload.project_id,
        provider_type="evolution",
        provider_resource_id=payload.instance_name,
        status="provisioning",
        display_name=payload.instance_name,
        metadata_json={"managed": True, "provider_flavor": payload.provider_flavor},
    )
    db.add(resource)
    db.flush()
    row = EvolutionInstance(
        tenant_id=payload.tenant_id,
        project_id=payload.project_id,
        resource_id=resource.id,
        instance_name=payload.instance_name,
        provider_flavor=payload.provider_flavor,
        instance_token_encrypted=encrypt_secret(instance_token),
        webhook_secret_encrypted=encrypt_secret(webhook_secret),
        webhook_url=webhook_url,
        subscribed_events=payload.events,
        status="provisioning",
        created_by=actor.id,
        metadata_json={"pairing_requested": bool(payload.pairing_phone)},
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    adapter = EvolutionManagementAdapter(payload.provider_flavor)
    try:
        created = await adapter.create_instance(payload.instance_name, instance_token)
        row.status = "created"
        resource = db.get(ProviderResource, row.resource_id) if row.resource_id else None
        if resource:
            resource.status = "active"
        if webhook_url:
            row.webhook_url = webhook_url
        db.commit()
        db.refresh(row)
    except ProviderError as exc:
        db.rollback()
        row = db.get(EvolutionInstance, row.id)
        if row:
            row.status = "failed"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
            resource = db.get(ProviderResource, resource.id)
            if resource:
                resource.status = "error"
            _audit(db, request, actor, row, "evolution.instance.create", "failure", str(exc))
            db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="instance could not be created") from exc
    _audit(db, request, actor, row, "evolution.instance.create")
    db.commit()
    return {"ok": True, "instance": _serialize(row), "provider": created.get("provider", {})}


@router.post("/instances/{instance_id}/connect", response_model=EvolutionActionResponse)
async def connect_instance(instance_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _operator(request, db, write=True)
    row = _get_instance(db, instance_id)
    token = _secret(row)
    try:
        provider = await EvolutionManagementAdapter(row.provider_flavor).connect(
            row.instance_name,
            token or "",
            webhook_url=row.webhook_url or _public_webhook_url(row),
            events=row.subscribed_events,
        )
        row.status = "qr_pending" if provider.get("qrcode") or provider.get("code") else "created"
        row.last_error_code = None
        row.last_error_message = None
        _audit(db, request, actor, row, "evolution.instance.connect")
        db.commit()
        db.refresh(row)
        return {"ok": True, "instance": _serialize(row), "provider": provider}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "evolution.instance.connect", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/instances/{instance_id}/qr")
async def get_qr(instance_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _operator(request, db, write=True)
    row = _get_instance(db, instance_id)
    try:
        result = await EvolutionManagementAdapter(row.provider_flavor).qr(row.instance_name, _secret(row))
        ttl = int(result.get("expires_in", 60))
        row.status = "qr_pending"
        row.qr_expires_at = _utcnow() + timedelta(seconds=min(max(ttl, 15), 300))
        row.last_error_code = None
        row.last_error_message = None
        _audit(db, request, actor, row, "evolution.instance.qr")
        db.commit()
        return {"ok": True, "instance_id": row.id, "expires_at": row.qr_expires_at, "qrcode": result.get("qrcode")}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "evolution.instance.qr", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/instances/{instance_id}/pair")
async def pair_instance(instance_id: int, payload: EvolutionPairRequest, request: Request, db: Session = Depends(get_db)):
    actor = _operator(request, db, write=True)
    row = _get_instance(db, instance_id)
    try:
        result = await EvolutionManagementAdapter(row.provider_flavor).pair(row.instance_name, _secret(row) or "", payload.phone)
        row.status = "pairing_pending"
        _audit(db, request, actor, row, "evolution.instance.pair")
        db.commit()
        return {"ok": True, "instance": _serialize(row), "pairing_code": result.get("pairing_code")}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "evolution.instance.pair", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/instances/{instance_id}/status")
async def refresh_status(instance_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _operator(request, db)
    row = _get_instance(db, instance_id)
    try:
        result = await EvolutionManagementAdapter(row.provider_flavor).status(row.instance_name, _secret(row))
        row.status = result.get("status") or "degraded"
        row.jid = result.get("jid") or row.jid
        row.display_phone_number = result.get("phone") or row.display_phone_number
        row.last_status_check_at = _utcnow()
        if row.status == "connected":
            row.last_connected_at = row.last_connected_at or _utcnow()
            row.last_error_code = None
            row.last_error_message = None
        _audit(db, request, actor, row, "evolution.instance.status")
        db.commit()
        return {"ok": True, "instance": _serialize(row), "provider": result.get("provider", {}), "provider_status": result.get("provider_status")}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_status_check_at = _utcnow()
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, "evolution.instance.status", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


async def _action(instance_id: int, request: Request, db: Session, action: str):
    actor = _operator(request, db, write=True)
    row = _get_instance(db, instance_id)
    try:
        adapter = EvolutionManagementAdapter(row.provider_flavor)
        if action == "reconnect":
            provider = await adapter.reconnect(row.instance_name, _secret(row))
            row.status = "created"
        elif action == "disconnect":
            provider = await adapter.disconnect(row.instance_name, _secret(row))
            row.status = "disconnected"
        elif action == "logout":
            provider = await adapter.logout(row.instance_name, _secret(row))
            row.status = "logged_out"
        else:
            raise RuntimeError("unsupported lifecycle action")
        _audit(db, request, actor, row, f"evolution.instance.{action}")
        db.commit()
        return {"ok": True, "instance": _serialize(row), "provider": provider}
    except ProviderError as exc:
        row.status = "degraded"
        row.last_error_code = exc.code
        row.last_error_message = str(exc)[:512]
        _audit(db, request, actor, row, f"evolution.instance.{action}", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc


@router.post("/instances/{instance_id}/reconnect")
async def reconnect_instance(instance_id: int, request: Request, db: Session = Depends(get_db)):
    return await _action(instance_id, request, db, "reconnect")


@router.post("/instances/{instance_id}/disconnect")
async def disconnect_instance(instance_id: int, request: Request, db: Session = Depends(get_db)):
    return await _action(instance_id, request, db, "disconnect")


@router.post("/instances/{instance_id}/logout")
async def logout_instance(instance_id: int, request: Request, db: Session = Depends(get_db)):
    return await _action(instance_id, request, db, "logout")


@router.delete("/instances/{instance_id}")
async def delete_instance(instance_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _operator(request, db, write=True)
    row = _get_instance(db, instance_id)
    try:
        provider = await EvolutionManagementAdapter(row.provider_flavor).delete(row.instance_name)
        resource = db.get(ProviderResource, row.resource_id) if row.resource_id else None
        if resource:
            resource.status = "suspended"
        row.status = "deleted"
        row.instance_token_encrypted = None
        row.webhook_secret_encrypted = None
        row.last_error_code = None
        row.last_error_message = None
        _audit(db, request, actor, row, "evolution.instance.delete")
        db.commit()
        return {"ok": True, "instance_id": instance_id, "provider": provider}
    except ProviderError as exc:
        _audit(db, request, actor, row, "evolution.instance.delete", "failure", str(exc))
        db.commit()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc
