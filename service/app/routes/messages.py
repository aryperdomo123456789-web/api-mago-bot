from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..platform_limits import DEFAULT_LIMITS, QuotaExceeded, get_service_api_key, require_key_scope, consume_quota
from ..platform_rate_limit import DistributedRateLimitExceeded, enforce_distributed_limit
from ..platform_resilience import ProviderCircuitOpen, before_provider_call, record_provider_failure, record_provider_success
from ..platform_crypto import decrypt_secret
from ..platform_models import Conversation, ConversationEvent, EvolutionInstance, OutboundMessage, PlatformProject, ProviderResource, ServiceApiKey, Tenant, UsageLedgerEntry
from ..platform_schemas import MessageSendRequest
from ..providers import DryRunAdapter, EvolutionAdapter, MetaCloudAdapter, ProviderError

router = APIRouter(prefix="/v1", tags=["messages"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _request_hash(payload: MessageSendRequest) -> str:
    encoded = json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _adapter(provider_type: str, *, api_key: str | None = None, flavor: str | None = None):
    if provider_type == "meta_cloud":
        return MetaCloudAdapter()
    if provider_type == "evolution":
        return EvolutionAdapter(api_key=api_key, flavor=flavor)
    if provider_type == "dry_run" and os.getenv("ALLOW_DRY_RUN_PROVIDER", "false").lower() == "true":
        return DryRunAdapter()
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="provider adapter not available")


def _safe_message(row: OutboundMessage) -> dict:
    return {
        "id": str(row.message_uuid),
        "status": row.status,
        "provider": row.provider_type,
        "provider_message_id": row.provider_message_id,
        "conversation_id": str(row.conversation.conversation_uuid) if getattr(row, "conversation", None) else None,
        "created_at": row.created_at,
        "error_code": row.error_code,
    }


def _conversation_for_send(db: Session, project_id: int, tenant_id: int, conversation_id: UUID | None) -> Conversation | None:
    if conversation_id is None:
        return None
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.conversation_uuid == conversation_id,
            Conversation.project_id == project_id,
            Conversation.tenant_id == tenant_id,
        )
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    if conversation.status == "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="conversation archived")
    return conversation


def _ledger_entry(db: Session, *, tenant_id: int, project_id: int, message: OutboundMessage, metric: str, source_id: str, provider_type: str | None = None, metadata: dict | None = None) -> None:
    existing = db.scalar(select(UsageLedgerEntry).where(
        UsageLedgerEntry.tenant_id == tenant_id,
        UsageLedgerEntry.source_type == "outbound_message",
        UsageLedgerEntry.source_id == source_id,
        UsageLedgerEntry.metric == metric,
    ))
    if existing:
        return
    db.add(UsageLedgerEntry(
        tenant_id=tenant_id,
        project_id=project_id,
        message_id=message.id,
        metric=metric,
        units=1,
        provider_type=provider_type,
        source_type="outbound_message",
        source_id=source_id,
        metadata_json=metadata or {},
    ))


def _timeline_event(db: Session, *, message: OutboundMessage, conversation: Conversation | None, event_type: str, actor_type: str, content: dict) -> None:
    if not conversation:
        return
    db.add(ConversationEvent(
        tenant_id=message.tenant_id,
        project_id=message.project_id,
        conversation_id=conversation.id,
        outbound_message_id=message.id,
        customer_profile_id=conversation.customer_profile_id,
        event_type=event_type,
        direction="outbound",
        channel=conversation.primary_channel,
        actor_type=actor_type,
        provider_type=message.provider_type,
        provider_event_id=message.provider_message_id,
        content=content,
        metadata_json={"message_id": str(message.message_uuid)},
    ))


@router.post("/projects/{project_id}/messages", status_code=status.HTTP_201_CREATED)
async def send_message(
    project_id: int,
    payload: MessageSendRequest,
    request: Request,
    response: Response,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    x_resource_id: int | None = Header(default=None, alias="X-Resource-Id"),
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "whatsapp:messages:send")
    if not x_idempotency_key or len(x_idempotency_key.strip()) < 16 or len(x_idempotency_key) > 160:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Idempotency-Key is required")
    idempotency_key = x_idempotency_key.strip()

    project = db.scalar(
        select(PlatformProject).where(
            PlatformProject.id == project_id,
            PlatformProject.tenant_id == api_key.tenant_id,
            PlatformProject.status == "active",
        )
    )
    if not project or api_key.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    conversation = _conversation_for_send(db, project_id, api_key.tenant_id, payload.conversation_id)

    request_hash = _request_hash(payload)
    existing = db.scalar(
        select(OutboundMessage).where(
            OutboundMessage.tenant_id == api_key.tenant_id,
            OutboundMessage.idempotency_key == idempotency_key,
        )
    )
    if existing:
        if existing.payload.get("_request_hash") != request_hash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency key reused with different payload")
        response.status_code = status.HTTP_200_OK
        return {"message": _safe_message(existing), "idempotent_replay": True}

    tenant = db.get(Tenant, api_key.tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant inactive")

    try:
        limit = DEFAULT_LIMITS.get(tenant.plan_slug, DEFAULT_LIMITS["start"]).get("messages_per_minute", 60)
        enforce_distributed_limit(
            db,
            namespace="messages_per_minute",
            subject=f"tenant:{tenant.id}:key:{api_key.id}",
            limit=limit,
            window_seconds=60,
        )
        consume_quota(db, tenant.id, tenant.plan_slug, "messages_per_minute")
        consume_quota(db, tenant.id, tenant.plan_slug, "messages_per_day")
    except DistributedRateLimitExceeded as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limit_exceeded", "namespace": exc.namespace, "limit": exc.limit},
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    except QuotaExceeded as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "quota_exceeded", "metric": exc.metric, "limit": exc.limit},
            headers={"Retry-After": "60" if exc.metric.endswith("minute") else "3600"},
        ) from exc

    resource_query = select(ProviderResource).where(
        ProviderResource.tenant_id == api_key.tenant_id,
        ProviderResource.project_id == project.id,
        ProviderResource.status == "active",
    )
    if x_resource_id is not None:
        resource_query = resource_query.where(ProviderResource.id == x_resource_id)
    resources = db.scalars(resource_query.order_by(ProviderResource.id)).all()
    if len(resources) != 1:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="one active provider resource is required")
    resource = resources[0]
    if not resource.provider_resource_id:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="provider resource is not configured")

    managed_evolution = None
    if resource.provider_type == "evolution":
        managed_evolution = db.scalar(select(EvolutionInstance).where(
            EvolutionInstance.resource_id == resource.id,
            EvolutionInstance.status != "deleted",
        ))
        if managed_evolution and managed_evolution.status != "connected":
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"code": "evolution_instance_not_connected", "status": managed_evolution.status},
            )

    stored_payload = payload.model_dump(mode="json")
    stored_payload["_request_hash"] = request_hash
    message = OutboundMessage(
        tenant_id=api_key.tenant_id,
        project_id=project.id,
        conversation_id=conversation.id if conversation else None,
        resource_id=resource.id,
        provider_type=resource.provider_type,
        idempotency_key=idempotency_key,
        recipient=payload.to,
        message_type=payload.type,
        payload=stored_payload,
        status="sending",
    )
    db.add(message)
    db.flush()
    _ledger_entry(
        db,
        tenant_id=api_key.tenant_id,
        project_id=project.id,
        message=message,
        metric="messages.accepted",
        source_id=str(message.message_uuid),
        provider_type=resource.provider_type,
        metadata={"channel": conversation.primary_channel if conversation else resource.provider_type},
    )
    _timeline_event(
        db,
        message=message,
        conversation=conversation,
        event_type="message.accepted",
        actor_type="application",
        content={"status": "accepted", "message_id": str(message.message_uuid), "type": payload.type},
    )
    db.commit()
    db.refresh(message)

    provider_payload = payload.model_dump(exclude_none=True)
    try:
        before_provider_call(db, provider_type=resource.provider_type, resource_key=str(resource.id))
        db.commit()
    except ProviderCircuitOpen as exc:
        db.rollback()
        message.status = "failed"
        message.error_code = "provider_circuit_open"
        message.error_message = "provider temporarily isolated"
        _timeline_event(
            db,
            message=message,
            conversation=conversation,
            event_type="message.failed",
            actor_type="control_plane",
            content={"status": "failed", "error_code": "provider_circuit_open", "message_id": str(message.message_uuid)},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "provider_circuit_open", "message": "provider temporarily isolated"},
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc

    try:
        provider_api_key = None
        provider_flavor = None
        if managed_evolution:
            provider_api_key = decrypt_secret(managed_evolution.instance_token_encrypted) if managed_evolution.instance_token_encrypted else None
            provider_flavor = managed_evolution.provider_flavor
        result = await _adapter(
            resource.provider_type,
            api_key=provider_api_key,
            flavor=provider_flavor,
        ).send_message(resource.provider_resource_id, provider_payload)
    except ProviderError as exc:
        record_provider_failure(
            db,
            provider_type=resource.provider_type,
            resource_key=str(resource.id),
            retryable=exc.retryable,
        )
        message.status = "failed"
        message.error_code = exc.code
        message.error_message = str(exc)[:512]
        _timeline_event(
            db,
            message=message,
            conversation=conversation,
            event_type="message.failed",
            actor_type="provider",
            content={"status": "failed", "error_code": exc.code, "message_id": str(message.message_uuid)},
        )
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE if exc.retryable else status.HTTP_502_BAD_GATEWAY,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc

    record_provider_success(db, provider_type=resource.provider_type, resource_key=str(resource.id))
    message.status = "sent"
    message.provider_message_id = result.provider_message_id
    _timeline_event(
        db,
        message=message,
        conversation=conversation,
        event_type="message.sent",
        actor_type="provider",
        content={"status": "sent", "provider_message_id": result.provider_message_id, "message_id": str(message.message_uuid)},
    )
    db.commit()
    db.refresh(message)
    return {"message": _safe_message(message), "idempotent_replay": False}


@router.get("/projects/{project_id}/messages")
def list_messages(
    project_id: int,
    request: Request,
    limit: int = 50,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "whatsapp:messages:read")
    if api_key.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 100")
    rows = db.scalars(
        select(OutboundMessage)
        .where(OutboundMessage.project_id == project_id, OutboundMessage.tenant_id == api_key.tenant_id)
        .order_by(OutboundMessage.id.desc())
        .limit(limit)
    ).all()
    return {"items": [_safe_message(row) for row in rows]}


@router.get("/projects/{project_id}/messages/{message_id}")
def get_message(
    project_id: int,
    message_id: str,
    request: Request,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "whatsapp:messages:read")
    if api_key.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message not found")
    try:
        message_uuid = UUID(message_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="message_id must be a UUID") from exc
    row = db.scalar(
        select(OutboundMessage).where(
            OutboundMessage.message_uuid == message_uuid,
            OutboundMessage.project_id == project_id,
            OutboundMessage.tenant_id == api_key.tenant_id,
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message not found")
    return {"message": _safe_message(row)}
