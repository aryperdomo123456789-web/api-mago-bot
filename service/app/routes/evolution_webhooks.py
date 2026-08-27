from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..platform_crypto import decrypt_secret
from ..platform_webhook_events import canonical_event_type, subscription_event_matches
from ..platform_models import (
    Conversation,
    ConversationEvent,
    CustomerIdentity,
    CustomerProfile,
    EvolutionInstance,
    EvolutionInstanceEvent,
    ProviderResource,
    WebhookDelivery,
    WebhookEvent,
    WebhookSubscription,
)

router = APIRouter(prefix="/v1/webhooks/evolution", tags=["evolution-webhooks"])
MAX_PAYLOAD_BYTES = 8 * 1024 * 1024
_PHONE_RE = re.compile(r"[^0-9]")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sanitize(value: Any, *, depth: int = 0) -> Any:
    blocked = {"token", "instanceToken", "instance_token", "apikey", "apiKey", "secret", "password"}
    if depth > 8:
        return "[depth-limited]"
    if isinstance(value, dict):
        return {str(key): _sanitize(item, depth=depth + 1) for key, item in value.items() if str(key) not in blocked}
    if isinstance(value, list):
        return [_sanitize(item, depth=depth + 1) for item in value[:200]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _event_type(payload: dict[str, Any]) -> str:
    return str(payload.get("event") or payload.get("type") or "UNKNOWN").strip().upper()[:80]


def _event_data(payload: dict[str, Any]) -> dict[str, Any]:
    data = payload.get("data")
    return data if isinstance(data, dict) else {}


def _message_id(data: dict[str, Any], payload: dict[str, Any]) -> str | None:
    info = data.get("Info") if isinstance(data.get("Info"), dict) else {}
    for value in (info.get("ID"), data.get("id"), payload.get("id"), data.get("messageId")):
        if value:
            return str(value)
    return None


def _instance_id(payload: dict[str, Any], fallback: UUID) -> str:
    value = payload.get("instanceId") or payload.get("instance_id") or payload.get("instance")
    return str(value or fallback)


def _provider_event_id(payload: dict[str, Any], instance_uuid: UUID) -> str:
    event_type = _event_type(payload)
    message_id = _message_id(_event_data(payload), payload)
    if not message_id:
        message_id = hashlib.sha256(json.dumps(_sanitize(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    return f"{instance_uuid}:{event_type}:{message_id}"[:180]


def _phone(value: Any) -> str | None:
    if not value:
        return None
    normalized = _PHONE_RE.sub("", str(value).split("@")[0].split(":")[0])
    return normalized if len(normalized) >= 6 else None


def _event_bucket(event_type: str) -> str:
    if event_type in {"MESSAGE", "MESSAGE_UPSERT", "SEND_MESSAGE"}:
        return "messages"
    if event_type in {"RECEIPT", "READ_RECEIPT", "PRESENCE", "CHAT_PRESENCE"}:
        return "statuses"
    if event_type in {"CALL", "CALL_OFFER", "CALL_TERMINATE"}:
        return "calls"
    if event_type in {"CONNECTION", "CONNECTED", "PAIRSUCCESS", "LOGGEDOUT", "QRCODE", "OFFLINESYNCCOMPLETED"}:
        return "account"
    return "all"


def _text_content(data: dict[str, Any]) -> str | None:
    message = data.get("Message") if isinstance(data.get("Message"), dict) else data.get("message")
    if not isinstance(message, dict):
        return None
    if isinstance(message.get("conversation"), str):
        return message["conversation"][:10000]
    extended = message.get("extendedTextMessage")
    if isinstance(extended, dict) and isinstance(extended.get("text"), str):
        return extended["text"][:10000]
    return None


def _upsert_conversation(db: Session, row: EvolutionInstance, payload: dict[str, Any], provider_event_id: str, event_type: str) -> None:
    if event_type not in {"MESSAGE", "MESSAGE_UPSERT"}:
        return
    data = _event_data(payload)
    info = data.get("Info") if isinstance(data.get("Info"), dict) else {}
    sender = _phone(info.get("Sender") or info.get("Chat"))
    chat = str(info.get("Chat") or sender or "")[:180]
    if not sender or not chat:
        return
    identity = db.scalar(select(CustomerIdentity).where(
        CustomerIdentity.tenant_id == row.tenant_id,
        CustomerIdentity.identity_type == "phone",
        CustomerIdentity.normalized_value == sender,
    ))
    if identity:
        profile = db.get(CustomerProfile, identity.customer_profile_id)
    else:
        profile = CustomerProfile(
            tenant_id=row.tenant_id,
            display_name=str(info.get("PushName") or "")[:180] or None,
            external_ref=sender,
            status="active",
            metadata_json={"provider": "evolution", "instance_uuid": str(row.instance_uuid)},
            last_seen_at=_now(),
        )
        db.add(profile)
        db.flush()
        identity = CustomerIdentity(
            tenant_id=row.tenant_id,
            customer_profile_id=profile.id,
            identity_type="phone",
            normalized_value=sender,
            channel="whatsapp",
            is_primary=True,
        )
        db.add(identity)
    profile.last_seen_at = _now()
    conversation = db.scalar(select(Conversation).where(
        Conversation.tenant_id == row.tenant_id,
        Conversation.project_id == row.project_id,
        Conversation.customer_profile_id == profile.id,
        Conversation.primary_channel == "whatsapp",
        Conversation.external_ref == chat,
        Conversation.status != "archived",
    ).order_by(Conversation.id.desc()))
    if not conversation:
        conversation = Conversation(
            tenant_id=row.tenant_id,
            project_id=row.project_id,
            customer_profile_id=profile.id,
            primary_channel="whatsapp",
            status="active",
            external_ref=chat,
            last_event_at=_now(),
            metadata_json={"provider": "evolution", "resource_id": row.resource_id},
        )
        db.add(conversation)
        db.flush()
    conversation.last_event_at = _now()
    db.add(ConversationEvent(
        tenant_id=row.tenant_id,
        project_id=row.project_id,
        conversation_id=conversation.id,
        customer_profile_id=profile.id,
        event_type="message.received",
        direction="inbound",
        channel="whatsapp",
        actor_type="customer",
        provider_type="evolution",
        provider_event_id=provider_event_id,
        content={"text": _text_content(data), "message_type": info.get("Type"), "media_type": info.get("MediaType")},
        metadata_json={"instance_uuid": str(row.instance_uuid), "provider_event_type": event_type},
    ))


def _update_state(row: EvolutionInstance, event_type: str, data: dict[str, Any]) -> None:
    normalized = event_type.replace("_", "").replace(".", "")
    if normalized in {"CONNECTED", "PAIRSUCCESS"}:
        row.status = "connected"
        row.last_connected_at = _now()
        row.last_error_code = None
        row.last_error_message = None
    elif normalized in {"LOGGEDOUT"}:
        row.status = "logged_out"
    elif normalized in {"QRCODE", "QRTIMEOUT"}:
        row.status = "qr_pending"
    elif normalized in {"OFFLINESYNCCOMPLETED"}:
        row.status = "connected"
        row.last_sync_at = _now()
    elif normalized in {"CONNECTION", "CONNECTIONUPDATE"}:
        state = str(data.get("status") or data.get("state") or "").lower()
        if state in {"open", "connected", "online"}:
            row.status = "connected"
            row.last_connected_at = _now()
        elif state in {"close", "closed", "disconnected", "offline"}:
            row.status = "disconnected"
        else:
            row.status = "degraded"
    row.last_status_check_at = _now()


def _deliveries_for_event(db: Session, row: EvolutionInstance, event: WebhookEvent, canonical_type: str, raw_event_type: str) -> None:
    subscriptions = db.scalars(select(WebhookSubscription).where(
        WebhookSubscription.tenant_id == row.tenant_id,
        WebhookSubscription.project_id == row.project_id,
        WebhookSubscription.status == "active",
    )).all()
    db.add_all([
        WebhookDelivery(subscription_id=sub.id, event_id=event.id)
        for sub in subscriptions
        if subscription_event_matches(sub.events, canonical_type, raw_event_type)
    ])


@router.post("/{instance_uuid}/{endpoint_secret}")
async def receive_evolution_webhook(
    instance_uuid: UUID,
    endpoint_secret: str,
    request: Request,
    db: Session = Depends(get_db),
):
    row = db.scalar(select(EvolutionInstance).where(EvolutionInstance.instance_uuid == instance_uuid, EvolutionInstance.status != "deleted"))
    if not row or not row.webhook_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="webhook endpoint not found")
    expected = decrypt_secret(row.webhook_secret_encrypted)
    if not hmac.compare_digest(endpoint_secret, expected):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="webhook endpoint not found")
    body = await request.body()
    if len(body) > MAX_PAYLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="payload too large")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON object required")

    raw_event_type = _event_type(payload)
    canonical_type = canonical_event_type(raw_event_type, payload)
    provider_event_id = _provider_event_id(payload, row.instance_uuid)
    if _instance_id(payload, row.instance_uuid) not in {str(row.instance_uuid), row.instance_name, str(row.resource_id)}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="instance does not match webhook endpoint")
    existing = db.scalar(select(EvolutionInstanceEvent.id).where(
        EvolutionInstanceEvent.instance_id == row.id,
        EvolutionInstanceEvent.provider_event_id == provider_event_id,
    ))
    if existing:
        return {"ok": True, "accepted": 0, "duplicates": 1}

    sanitized = _sanitize(payload)
    data = _event_data(sanitized)
    instance_event = EvolutionInstanceEvent(
        instance_id=row.id,
        provider_event_id=provider_event_id,
        event_type=raw_event_type,
        status="accepted",
        payload=sanitized,
        occurred_at=None,
    )
    db.add(instance_event)
    row_data = _event_data(payload)
    _update_state(row, raw_event_type, row_data)
    _upsert_conversation(db, row, sanitized, provider_event_id, raw_event_type)
    webhook_event = WebhookEvent(
        provider_type="evolution",
        provider_event_id=provider_event_id,
        tenant_id=row.tenant_id,
        resource_id=row.resource_id,
        event_type=canonical_type,
        payload=sanitized,
        status="accepted",
        attempts=0,
    )
    db.add(webhook_event)
    try:
        db.flush()
        _deliveries_for_event(db, row, webhook_event, canonical_type, raw_event_type)
        db.commit()
    except IntegrityError:
        db.rollback()
        return {"ok": True, "accepted": 0, "duplicates": 1}
    return {"ok": True, "accepted": 1, "duplicates": 0, "event_id": str(instance_event.event_uuid)}
