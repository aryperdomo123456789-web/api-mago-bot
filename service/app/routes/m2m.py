from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import desc, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..m2m_schemas import (
    M2MChannelCreateRequest,
    M2MChannelListResponse,
    M2MChannelQrResponse,
    M2MChannelResponse,
    M2MChannelStatusResponse,
    M2MPairingRequest,
    M2MPairingResponse,
    M2MWebhookCreateRequest,
    M2MWebhookListResponse,
    M2MWebhookResponse,
    M2MWebhookView,
)
from ..platform_crypto import encrypt_secret
from ..qr_code import qr_svg_data
from ..platform_errors import error_body
from ..platform_limits import get_service_api_key_x_api_key, require_key_scope
from ..platform_models import (
    AuditEvent,
    EvolutionInstance,
    Operation,
    PlatformProject,
    ProviderResource,
    ServiceApiKey,
    Tenant,
    WebhookSubscription,
)
from ..platform_operations import (
    TERMINAL_OPERATION_STATES,
    canonical_request_hash,
    create_or_replay_operation,
    mark_operation_failed,
    mark_operation_running,
    mark_operation_succeeded,
    operation_view,
    require_idempotency_key,
)
from ..platform_ssrf import UnsafeWebhookEndpoint, validate_webhook_endpoint
from ..platform_webhook_events import allowed_subscription_events
from ..providers.base import ProviderError
from ..providers.evolution_management import EvolutionManagementAdapter

router = APIRouter(prefix="/v1", tags=["m2m"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_safe(value: Any) -> Any:
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value


def _strict_scope(api_key: ServiceApiKey, *scopes: str) -> None:
    if not set(api_key.scopes or []).intersection(scopes):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "api_key_scope_required",
                "message": f"A API key precisa de um dos scopes: {', '.join(scopes)}.",
                "reason": "PERMISSION_DENIED",
                "retryable": False,
            },
        )


def _project_for_key(db: Session, project_uuid: UUID, api_key: ServiceApiKey) -> PlatformProject:
    project = db.scalar(
        select(PlatformProject).where(
            PlatformProject.project_uuid == project_uuid,
            PlatformProject.tenant_id == api_key.tenant_id,
            PlatformProject.status == "active",
        )
    )
    if not project or (api_key.project_id is not None and api_key.project_id != project.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    tenant = db.get(Tenant, api_key.tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant inactive")
    return project


def _channel_for_key(db: Session, channel_uuid: UUID, api_key: ServiceApiKey) -> tuple[EvolutionInstance, PlatformProject, Tenant]:
    row = db.scalar(
        select(EvolutionInstance).where(
            EvolutionInstance.instance_uuid == channel_uuid,
            EvolutionInstance.tenant_id == api_key.tenant_id,
            EvolutionInstance.status != "deleted",
        )
    )
    if not row or (api_key.project_id is not None and api_key.project_id != row.project_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")
    project = db.scalar(select(PlatformProject).where(PlatformProject.id == row.project_id, PlatformProject.status == "active"))
    tenant = db.get(Tenant, row.tenant_id)
    if not project or not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="channel not found")
    return row, project, tenant


def _public_provider(value: Any) -> dict[str, Any]:
    blocked = {"token", "instanceToken", "instance_token", "apikey", "apiKey", "secret", "password", "qrcode", "qr", "code", "pairing_code", "pairingCode"}

    def clean(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(key): clean(child) for key, child in item.items() if str(key) not in blocked}
        if isinstance(item, list):
            return [clean(child) for child in item[:100]]
        if isinstance(item, (str, int, float, bool)) or item is None:
            return item
        return str(item)

    cleaned = clean(value)
    return cleaned if isinstance(cleaned, dict) else {"data": cleaned}


def _channel_view(row: EvolutionInstance, project: PlatformProject, tenant: Tenant) -> dict[str, Any]:
    return {
        "id": row.instance_uuid,
        "organization_id": tenant.tenant_uuid,
        "project_id": project.project_uuid,
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
        values = ["status", "qr", "connect", "reconnect", "disconnect", "webhooks"]
        if flavor == "evolution_go":
            values.append("pairing_code")
        return values
    return ["text", "image", "video", "audio", "document", "sticker", "status", "webhooks", "reconnect", "media"]


def _operation_public(db: Session, row: Operation) -> dict[str, Any]:
    project = db.get(PlatformProject, row.project_id)
    tenant = db.get(Tenant, row.tenant_id)
    return operation_view(
        row,
        organization_uuid=tenant.tenant_uuid if tenant else None,
        project_uuid=project.project_uuid if project else None,
    )


def _idempotency_key(request: Request) -> str:
    return require_idempotency_key(request.headers.get("X-Idempotency-Key") or request.headers.get("Idempotency-Key"))


def _audit(db: Session, request: Request, api_key: ServiceApiKey, tenant_id: int, action: str, resource_id: str | None = None, outcome: str = "success", reason: str | None = None) -> None:
    db.add(
        AuditEvent(
            tenant_id=tenant_id,
            actor_user_id=api_key.created_by,
            action=action,
            resource_type="m2m",
            resource_id=resource_id,
            outcome=outcome,
            request_id=str(getattr(request.state, "request_id", ""))[:80] or None,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:512],
            reason=reason[:512] if reason else None,
            metadata_json={"auth": "x-api-key", "api_key_uuid": str(api_key.key_uuid)},
        )
    )


def _provider_error(request: Request, exc: ProviderError) -> tuple[int, dict[str, Any]]:
    response_status = status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY
    retry_after = 30 if exc.retryable else None
    body = error_body(
        request,
        status_code=response_status,
        code=exc.code,
        message=str(exc),
        reason="PROVIDER_UNAVAILABLE" if exc.retryable else "PROVIDER_REJECTED",
        domain="api.mago-bot.com/providers/evolution",
        retryable=exc.retryable,
        retry_after_seconds=retry_after,
    )
    return response_status, body["error"]


def _raise_provider(request: Request, exc: ProviderError) -> None:
    response_status, error = _provider_error(request, exc)
    headers = {"Retry-After": str(error["retry_after_seconds"])} if error.get("retry_after_seconds") else None
    raise HTTPException(status_code=response_status, detail=error, headers=headers) from exc


def _replay_or_raise(db: Session, operation: Operation, replayed: bool, *, retry_after: int = 5) -> dict[str, Any] | None:
    if not replayed:
        return None
    if operation.status == "succeeded" and isinstance(operation.response_json, dict):
        return operation.response_json
    if operation.status in TERMINAL_OPERATION_STATES:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=operation.error_json or {"code": "operation_not_replayable", "message": "A operação anterior terminou sem resposta replayable."})
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "operation_in_progress",
            "message": "Já existe uma operação em andamento com esta chave de idempotência.",
            "reason": "ABORTED",
            "retryable": True,
            "retry_after_seconds": retry_after,
            "operation": f"operations/{operation.operation_uuid}",
        },
        headers={"Retry-After": str(retry_after)},
    )


@router.get("/projects/{project_uuid}/channels", response_model=M2MChannelListResponse, summary="Listar canais do projeto via API key")
def list_channels_m2m(
    project_uuid: UUID,
    request: Request,
    page_size: int = Query(default=50, ge=1, le=100),
    channel_status: str | None = Query(default=None, alias="status", max_length=32),
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key),
):
    _strict_scope(api_key, "channels:read", "channels:write")
    project = _project_for_key(db, project_uuid, api_key)
    query = select(EvolutionInstance).where(EvolutionInstance.tenant_id == api_key.tenant_id, EvolutionInstance.project_id == project.id, EvolutionInstance.status != "deleted")
    if channel_status:
        query = query.where(EvolutionInstance.status == channel_status)
    tenant = db.get(Tenant, api_key.tenant_id)
    rows = db.scalars(query.order_by(desc(EvolutionInstance.id)).limit(page_size)).all()
    return {"items": [_channel_view(row, project, tenant) for row in rows], "next_page_token": None}


@router.post("/projects/{project_uuid}/channels", response_model=M2MChannelResponse, status_code=status.HTTP_201_CREATED, summary="Criar canal Evolution via API key")
async def create_channel_m2m(
    project_uuid: UUID,
    payload: M2MChannelCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key),
):
    _strict_scope(api_key, "channels:write")
    project = _project_for_key(db, project_uuid, api_key)
    tenant = db.get(Tenant, api_key.tenant_id)
    key = _idempotency_key(request)
    request_hash = canonical_request_hash({"project_uuid": str(project_uuid), "payload": payload.model_dump(mode="json")})
    operation, replayed = create_or_replay_operation(
        db,
        tenant_id=tenant.id,
        project_id=project.id,
        kind="channel.create",
        idempotency_key=key,
        request_hash=request_hash,
        api_key_id=api_key.id,
        metadata={"resource": "channel", "provider": "evolution", "project_uuid": str(project_uuid)},
    )
    replay = _replay_or_raise(db, operation, replayed)
    if replay is not None:
        return replay
    if db.scalar(select(EvolutionInstance.id).where(EvolutionInstance.tenant_id == tenant.id, EvolutionInstance.project_id == project.id, EvolutionInstance.instance_name == payload.display_name, EvolutionInstance.status != "deleted")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="channel already exists")

    instance_token = secrets.token_urlsafe(32)
    webhook_secret = secrets.token_urlsafe(32)
    resource = ProviderResource(
        tenant_id=tenant.id,
        project_id=project.id,
        provider_type="evolution",
        provider_resource_id=payload.display_name,
        status="provisioning",
        display_name=payload.display_name,
        metadata_json={"managed": True, "customer_scoped": True, "auth": "x-api-key", "provider_flavor": payload.provider_flavor},
    )
    db.add(resource)
    db.flush()
    row = EvolutionInstance(
        tenant_id=tenant.id,
        project_id=project.id,
        resource_id=resource.id,
        instance_name=payload.display_name,
        provider_flavor=payload.provider_flavor,
        instance_token_encrypted=encrypt_secret(instance_token),
        webhook_secret_encrypted=encrypt_secret(webhook_secret),
        subscribed_events=["MESSAGES_UPSERT", "CONNECTION_UPDATE"],
        status="provisioning",
        created_by=api_key.created_by,
        metadata_json={"customer_scoped": True, "auth": "x-api-key", "pairing_requested": bool(payload.pairing_phone), "downstream_events": payload.events},
    )
    db.add(row)
    mark_operation_running(operation, metadata={"instance_name": payload.display_name})
    db.commit()
    db.refresh(row)
    try:
        created = await EvolutionManagementAdapter(payload.provider_flavor).create_instance(row.instance_name, instance_token)
        row.status = "created"
        resource.status = "active"
        response = {"ok": True, "channel": _channel_view(row, project, tenant), "provider": _public_provider(created.get("provider", {})), "operation": _operation_public(db, operation)}
        mark_operation_succeeded(operation, _json_safe(response), metadata={"channel_uuid": str(row.instance_uuid)})
        _audit(db, request, api_key, tenant.id, "m2m.channel.create", str(row.instance_uuid))
        db.commit()
        db.refresh(row)
        response["channel"] = _channel_view(row, project, tenant)
        response["operation"] = _operation_public(db, operation)
        return response
    except ProviderError as exc:
        db.rollback()
        row = db.get(EvolutionInstance, row.id)
        resource = db.get(ProviderResource, resource.id)
        if row:
            row.status = "failed"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
        if resource:
            resource.status = "error"
        response_status, error = _provider_error(request, exc)
        mark_operation_failed(operation, error)
        _audit(db, request, api_key, tenant.id, "m2m.channel.create", str(row.instance_uuid) if row else None, "failure", str(exc))
        db.commit()
        headers = {"Retry-After": str(error["retry_after_seconds"])} if error.get("retry_after_seconds") else None
        raise HTTPException(status_code=response_status, detail=error, headers=headers) from exc
    except IntegrityError as exc:
        db.rollback()
        error = error_body(request, status_code=409, code="channel_conflict", message="O canal não pôde ser criado porque já existe um conflito de unicidade.", reason="ALREADY_EXISTS")["error"]
        operation = db.get(Operation, operation.id)
        if operation:
            mark_operation_failed(operation, error)
            db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error) from exc


@router.get("/channels/{channel_uuid}", response_model=dict, summary="Consultar canal via API key")
def get_channel_m2m(
    channel_uuid: UUID,
    request: Request,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key),
):
    _strict_scope(api_key, "channels:read", "channels:write")
    row, project, tenant = _channel_for_key(db, channel_uuid, api_key)
    return {"channel": _channel_view(row, project, tenant)}


@router.post("/channels/{channel_uuid}/connect", response_model=M2MChannelResponse, summary="Solicitar conexão do canal")
async def connect_channel_m2m(channel_uuid: UUID, request: Request, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    _strict_scope(api_key, "channels:write")
    row, project, tenant = _channel_for_key(db, channel_uuid, api_key)
    key = _idempotency_key(request)
    operation, replayed = create_or_replay_operation(db, tenant_id=tenant.id, project_id=project.id, kind="channel.connect", idempotency_key=key, request_hash=canonical_request_hash({"channel_uuid": str(channel_uuid)}), api_key_id=api_key.id, metadata={"resource": "channel", "action": "connect"})
    replay = _replay_or_raise(db, operation, replayed)
    if replay is not None:
        return replay
    mark_operation_running(operation)
    db.commit()
    try:
        adapter = EvolutionManagementAdapter(row.provider_flavor)
        await adapter.ensure_instance(row.instance_name, _secret(row) or "")
        provider = await adapter.connect(row.instance_name, _secret(row), webhook_url=row.webhook_url or _public_webhook(row), events=row.subscribed_events)
        row.status = "qr_pending" if provider.get("qrcode") or provider.get("code") else "connecting"
        row.last_error_code = None
        row.last_error_message = None
        response = {"ok": True, "channel": _channel_view(row, project, tenant), "provider": _public_provider(provider), "operation": _operation_public(db, operation)}
        mark_operation_succeeded(operation, _json_safe(response))
        _audit(db, request, api_key, tenant.id, "m2m.channel.connect", str(row.instance_uuid))
        db.commit()
        response["operation"] = _operation_public(db, operation)
        return response
    except ProviderError as exc:
        db.rollback()
        operation = db.get(Operation, operation.id)
        row = db.get(EvolutionInstance, row.id)
        response_status, error = _provider_error(request, exc)
        if row:
            row.status = "degraded"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
        if operation:
            mark_operation_failed(operation, error)
        db.commit()
        _raise_provider(request, exc)


@router.get("/channels/{channel_uuid}/qr", response_model=M2MChannelQrResponse, summary="Solicitar QR do canal")
async def qr_channel_m2m(channel_uuid: UUID, request: Request, response: Response, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    _strict_scope(api_key, "channels:write")
    row, project, tenant = _channel_for_key(db, channel_uuid, api_key)
    key = _idempotency_key(request)
    operation, replayed = create_or_replay_operation(db, tenant_id=tenant.id, project_id=project.id, kind="channel.qr", idempotency_key=key, request_hash=canonical_request_hash({"channel_uuid": str(channel_uuid)}), api_key_id=api_key.id, metadata={"resource": "channel", "action": "qr"}, ttl_days=1)
    replay = _replay_or_raise(db, operation, replayed)
    if replay is not None:
        response.headers["Cache-Control"] = "no-store, private"
        return replay
    mark_operation_running(operation)
    db.commit()
    try:
        adapter = EvolutionManagementAdapter(row.provider_flavor)
        await adapter.ensure_instance(row.instance_name, _secret(row) or "")
        result = await adapter.qr(row.instance_name, _secret(row))
        ttl = int(result.get("expires_in", 60))
        row.status = "qr_pending"
        row.qr_expires_at = _now() + timedelta(seconds=min(max(ttl, 15), 300))
        response_body = {"ok": True, "channel_id": row.instance_uuid, "expires_at": row.qr_expires_at, "qrcode": result.get("qrcode"), "qrcode_svg": qr_svg_data(result.get("qrcode")), "operation": _operation_public(db, operation)}
        mark_operation_succeeded(operation, _json_safe(response_body), metadata={"expires_at": row.qr_expires_at.isoformat()})
        _audit(db, request, api_key, tenant.id, "m2m.channel.qr", str(row.instance_uuid))
        db.commit()
        response.headers["Cache-Control"] = "no-store, private"
        response_body["operation"] = _operation_public(db, operation)
        return response_body
    except ProviderError as exc:
        db.rollback()
        operation = db.get(Operation, operation.id)
        row = db.get(EvolutionInstance, row.id)
        response_status, error = _provider_error(request, exc)
        if row:
            row.status = "degraded"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
        if operation:
            mark_operation_failed(operation, error)
        db.commit()
        _raise_provider(request, exc)


@router.post("/channels/{channel_uuid}/pair", response_model=M2MPairingResponse, summary="Solicitar pairing code do canal")
async def pair_channel_m2m(channel_uuid: UUID, payload: M2MPairingRequest, request: Request, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    _strict_scope(api_key, "channels:write")
    row, project, tenant = _channel_for_key(db, channel_uuid, api_key)
    if row.provider_flavor != "evolution_go":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "unsupported_operation", "message": "Pairing code não está disponível para este flavor Evolution.", "reason": "FAILED_PRECONDITION"})
    key = _idempotency_key(request)
    operation, replayed = create_or_replay_operation(db, tenant_id=tenant.id, project_id=project.id, kind="channel.pair", idempotency_key=key, request_hash=canonical_request_hash({"channel_uuid": str(channel_uuid), "phone": payload.phone}), api_key_id=api_key.id, metadata={"resource": "channel", "action": "pair"}, ttl_days=1)
    replay = _replay_or_raise(db, operation, replayed)
    if replay is not None:
        return replay
    mark_operation_running(operation)
    db.commit()
    try:
        result = await EvolutionManagementAdapter(row.provider_flavor).pair(row.instance_name, _secret(row) or "", payload.phone)
        row.status = "pairing_pending"
        response = {"ok": True, "channel": _channel_view(row, project, tenant), "pairing_code": result.get("pairing_code"), "provider": _public_provider(result.get("provider", {})), "operation": _operation_public(db, operation)}
        mark_operation_succeeded(operation, _json_safe(response))
        _audit(db, request, api_key, tenant.id, "m2m.channel.pair", str(row.instance_uuid))
        db.commit()
        response["operation"] = _operation_public(db, operation)
        return response
    except ProviderError as exc:
        db.rollback()
        operation = db.get(Operation, operation.id)
        row = db.get(EvolutionInstance, row.id)
        response_status, error = _provider_error(request, exc)
        if row:
            row.status = "degraded"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
        if operation:
            mark_operation_failed(operation, error)
        db.commit()
        _raise_provider(request, exc)


@router.get("/channels/{channel_uuid}/status", response_model=M2MChannelStatusResponse, summary="Atualizar status do canal")
async def status_channel_m2m(channel_uuid: UUID, request: Request, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    _strict_scope(api_key, "channels:read", "channels:write")
    row, project, tenant = _channel_for_key(db, channel_uuid, api_key)
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
        return {"channel": _channel_view(row, project, tenant), "status": {"status": checked.get("status"), "provider_status": checked.get("provider_status"), "jid": checked.get("jid"), "phone": checked.get("phone"), "checked": True}}
    except ProviderError as exc:
        db.rollback()
        row = db.get(EvolutionInstance, row.id)
        if row:
            row.status = "degraded"
            row.last_status_check_at = _now()
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
            db.commit()
        _raise_provider(request, exc)


async def _channel_action_m2m(channel_uuid: UUID, action: str, request: Request, db: Session, api_key: ServiceApiKey) -> dict[str, Any]:
    _strict_scope(api_key, "channels:write")
    row, project, tenant = _channel_for_key(db, channel_uuid, api_key)
    key = _idempotency_key(request)
    operation, replayed = create_or_replay_operation(db, tenant_id=tenant.id, project_id=project.id, kind=f"channel.{action}", idempotency_key=key, request_hash=canonical_request_hash({"channel_uuid": str(channel_uuid), "action": action}), api_key_id=api_key.id, metadata={"resource": "channel", "action": action})
    replay = _replay_or_raise(db, operation, replayed)
    if replay is not None:
        return replay
    mark_operation_running(operation)
    db.commit()
    try:
        adapter = EvolutionManagementAdapter(row.provider_flavor)
        provider = await getattr(adapter, action)(row.instance_name, _secret(row))
        row.status = "connecting" if action == "reconnect" else "disconnected"
        response = {"ok": True, "channel": _channel_view(row, project, tenant), "provider": _public_provider(provider), "operation": _operation_public(db, operation)}
        mark_operation_succeeded(operation, _json_safe(response))
        _audit(db, request, api_key, tenant.id, f"m2m.channel.{action}", str(row.instance_uuid))
        db.commit()
        response["operation"] = _operation_public(db, operation)
        return response
    except ProviderError as exc:
        db.rollback()
        operation = db.get(Operation, operation.id)
        row = db.get(EvolutionInstance, row.id)
        response_status, error = _provider_error(request, exc)
        if row:
            row.status = "degraded"
            row.last_error_code = exc.code
            row.last_error_message = str(exc)[:512]
        if operation:
            mark_operation_failed(operation, error)
        db.commit()
        _raise_provider(request, exc)


@router.post("/channels/{channel_uuid}/reconnect", response_model=M2MChannelResponse, summary="Reconectar canal")
async def reconnect_channel_m2m(channel_uuid: UUID, request: Request, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    return await _channel_action_m2m(channel_uuid, "reconnect", request, db, api_key)


@router.post("/channels/{channel_uuid}/disconnect", response_model=M2MChannelResponse, summary="Desconectar canal")
async def disconnect_channel_m2m(channel_uuid: UUID, request: Request, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    return await _channel_action_m2m(channel_uuid, "disconnect", request, db, api_key)


@router.get("/projects/{project_uuid}/webhooks", response_model=M2MWebhookListResponse, summary="Listar subscriptions downstream")
def list_webhook_subscriptions_m2m(project_uuid: UUID, request: Request, db: Session = Depends(get_db), api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    _strict_scope(api_key, "webhooks:read", "webhooks:write")
    project = _project_for_key(db, project_uuid, api_key)
    rows = db.scalars(select(WebhookSubscription).where(WebhookSubscription.tenant_id == api_key.tenant_id, WebhookSubscription.project_id == project.id).order_by(desc(WebhookSubscription.id))).all()
    return {"items": [_webhook_view(row, project) for row in rows], "next_page_token": None}


def _webhook_view(row: WebhookSubscription, project: PlatformProject) -> dict[str, Any]:
    return {
        "id": row.subscription_uuid,
        "project_id": project.project_uuid,
        "endpoint_url": row.endpoint_url,
        "events": row.events or [],
        "status": row.status,
        "failure_count": int(row.failure_count or 0),
        "last_delivery_at": row.last_delivery_at,
        "created_at": row.created_at,
    }


@router.post("/projects/{project_uuid}/webhooks", response_model=M2MWebhookResponse, status_code=status.HTTP_201_CREATED, summary="Registrar webhook downstream assinado")
def create_webhook_subscription_m2m(
    project_uuid: UUID,
    payload: M2MWebhookCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key),
):
    _strict_scope(api_key, "webhooks:write")
    project = _project_for_key(db, project_uuid, api_key)
    key = _idempotency_key(request)
    endpoint_url = str(payload.endpoint_url)
    try:
        endpoint_url = validate_webhook_endpoint(endpoint_url)
    except UnsafeWebhookEndpoint as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail={"code": "unsafe_webhook_endpoint", "message": str(exc), "reason": "INVALID_ARGUMENT"}) from exc
    operation, replayed = create_or_replay_operation(
        db,
        tenant_id=api_key.tenant_id,
        project_id=project.id,
        kind="webhook.create",
        idempotency_key=key,
        request_hash=canonical_request_hash({"project_uuid": str(project_uuid), "endpoint_url": endpoint_url, "events": payload.events}),
        api_key_id=api_key.id,
        metadata={"resource": "webhook_subscription", "events": payload.events},
    )
    replay = _replay_or_raise(db, operation, replayed)
    if replay is not None:
        return replay
    raw_secret = "whsec_" + secrets.token_urlsafe(32)
    row = WebhookSubscription(
        tenant_id=api_key.tenant_id,
        project_id=project.id,
        endpoint_url=endpoint_url,
        secret_encrypted=encrypt_secret(raw_secret),
        events=payload.events,
        status="active",
    )
    db.add(row)
    mark_operation_running(operation)
    db.flush()
    response = {"ok": True, "webhook": _webhook_view(row, project), "secret": raw_secret, "secret_warning": "Armazene este segredo agora; ele não será exibido novamente.", "operation": _operation_public(db, operation)}
    mark_operation_succeeded(operation, _json_safe({"ok": True, "webhook": _webhook_view(row, project), "secret_warning": "secret_returned_once"}))
    _audit(db, request, api_key, api_key.tenant_id, "m2m.webhook.create", str(row.subscription_uuid))
    db.commit()
    return response


@router.get("/webhooks/events", response_model=dict, summary="Listar eventos downstream suportados")
def list_supported_webhook_events(api_key: ServiceApiKey = Depends(get_service_api_key_x_api_key)):
    _strict_scope(api_key, "webhooks:read", "webhooks:write")
    return {"items": allowed_subscription_events(), "all": "all"}


def _secret(row: EvolutionInstance) -> str:
    from ..platform_crypto import decrypt_secret
    return decrypt_secret(row.instance_token_encrypted) if row.instance_token_encrypted else ""


def _public_webhook(row: EvolutionInstance) -> str | None:
    import os
    from urllib.parse import urljoin
    from ..platform_crypto import decrypt_secret
    base = os.getenv("EVOLUTION_WEBHOOK_PUBLIC_URL", "").strip()
    if not base or not row.webhook_secret_encrypted:
        return None
    return urljoin(base.rstrip("/") + "/", f"v1/webhooks/evolution/{row.instance_uuid}/{decrypt_secret(row.webhook_secret_encrypted)}")
