from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..platform_limits import get_service_api_key, require_key_scope
from ..platform_models import (
    Conversation,
    ConversationEvent,
    ConversationParticipant,
    CustomerIdentity,
    CustomerProfile,
    IdempotencyRecord,
    PlatformProject,
    ServiceApiKey,
    Tenant,
)
from ..conversation_schemas import (
    ConversationCreateRequest,
    ConversationEventCreateRequest,
    ConversationStatusUpdateRequest,
)

router = APIRouter(prefix="/v1", tags=["conversations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_identity(identity_type: str, value: str) -> str:
    value = value.strip()
    if identity_type in {"email", "sip_uri", "whatsapp"}:
        return value.lower()
    if identity_type == "phone":
        compact = "".join(char for char in value if char.isdigit() or char == "+")
        if not compact.startswith("+") or len(compact) < 8:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="phone identity must use E.164 format")
        return compact
    return value


def _project_for_key(db: Session, project_id: int, api_key: ServiceApiKey) -> PlatformProject:
    if api_key.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    project = db.scalar(
        select(PlatformProject).where(
            PlatformProject.id == project_id,
            PlatformProject.tenant_id == api_key.tenant_id,
            PlatformProject.status == "active",
        )
    )
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    tenant = db.get(Tenant, api_key.tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant inactive")
    return project


def _conversation_for_key(db: Session, project_id: int, conversation_id: UUID, api_key: ServiceApiKey) -> Conversation:
    _project_for_key(db, project_id, api_key)
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.conversation_uuid == conversation_id,
            Conversation.project_id == project_id,
            Conversation.tenant_id == api_key.tenant_id,
        )
    )
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    return conversation


def _conversation_view(row: Conversation, profile: CustomerProfile | None = None) -> dict:
    result = {
        "id": str(row.conversation_uuid),
        "status": row.status,
        "channel": row.primary_channel,
        "customer_profile_id": str(profile.profile_uuid) if profile else None,
        "subject": row.subject,
        "external_ref": row.external_ref,
        "last_event_at": row.last_event_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }
    if profile:
        result["customer"] = {
            "id": str(profile.profile_uuid),
            "display_name": profile.display_name,
            "external_ref": profile.external_ref,
        }
    return result


def _event_view(row: ConversationEvent) -> dict:
    return {
        "id": str(row.event_uuid),
        "event_type": row.event_type,
        "direction": row.direction,
        "channel": row.channel,
        "actor_type": row.actor_type,
        "content": row.content,
        "provider_event_id": row.provider_event_id,
        "created_at": row.created_at,
    }


@router.post("/projects/{project_id}/conversations", status_code=status.HTTP_201_CREATED)
def create_conversation(
    project_id: int,
    payload: ConversationCreateRequest,
    response: Response,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "conversations:write")
    project = _project_for_key(db, project_id, api_key)
    normalized = _normalize_identity(payload.identity_type, payload.identity)

    identity = db.scalar(
        select(CustomerIdentity).where(
            CustomerIdentity.tenant_id == api_key.tenant_id,
            CustomerIdentity.identity_type == payload.identity_type,
            CustomerIdentity.normalized_value == normalized,
        )
    )
    if identity:
        profile = db.get(CustomerProfile, identity.customer_profile_id)
        if not profile:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="customer identity is orphaned")
        if payload.display_name and not profile.display_name:
            profile.display_name = payload.display_name
    else:
        profile = CustomerProfile(
            tenant_id=api_key.tenant_id,
            display_name=payload.display_name,
            external_ref=payload.external_ref,
            metadata_json=payload.metadata,
            last_seen_at=_utcnow(),
        )
        db.add(profile)
        db.flush()
        identity = CustomerIdentity(
            tenant_id=api_key.tenant_id,
            customer_profile_id=profile.id,
            identity_type=payload.identity_type,
            normalized_value=normalized,
            channel=payload.channel,
            is_primary=True,
            metadata_json={},
        )
        db.add(identity)

    conversation = None
    if payload.external_ref:
        conversation = db.scalar(
            select(Conversation).where(
                Conversation.tenant_id == api_key.tenant_id,
                Conversation.project_id == project.id,
                Conversation.external_ref == payload.external_ref,
                Conversation.status.not_in(("closed", "archived")),
            ).order_by(desc(Conversation.updated_at))
        )
    if conversation:
        response.status_code = status.HTTP_200_OK
        return {"conversation": _conversation_view(conversation, profile), "created": False}

    conversation = Conversation(
        tenant_id=api_key.tenant_id,
        project_id=project.id,
        customer_profile_id=profile.id,
        primary_channel=payload.channel,
        status="active",
        subject=payload.subject,
        external_ref=payload.external_ref,
        last_event_at=_utcnow(),
        metadata_json=payload.metadata,
    )
    db.add(conversation)
    db.flush()
    db.add(
        ConversationParticipant(
            tenant_id=api_key.tenant_id,
            conversation_id=conversation.id,
            customer_profile_id=profile.id,
            participant_type="customer",
            participant_ref=str(profile.profile_uuid),
            channel=payload.channel,
            address=normalized,
            display_name=profile.display_name,
        )
    )
    db.add(
        ConversationEvent(
            tenant_id=api_key.tenant_id,
            project_id=project.id,
            conversation_id=conversation.id,
            customer_profile_id=profile.id,
            event_type="system",
            direction="system",
            channel=payload.channel,
            actor_type="system",
            content={"action": "conversation.created"},
            metadata_json={"identity_type": payload.identity_type},
        )
    )
    db.commit()
    db.refresh(conversation)
    db.refresh(profile)
    return {"conversation": _conversation_view(conversation, profile), "created": True}


@router.get("/projects/{project_id}/conversations")
def list_conversations(
    project_id: int,
    limit: int = 50,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "conversations:read")
    _project_for_key(db, project_id, api_key)
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 100")
    query = select(Conversation).where(
        Conversation.project_id == project_id,
        Conversation.tenant_id == api_key.tenant_id,
    )
    if status_filter:
        query = query.where(Conversation.status == status_filter)
    rows = db.scalars(query.order_by(desc(Conversation.updated_at)).limit(limit)).all()
    profiles = {profile.id: profile for profile in db.scalars(select(CustomerProfile).where(CustomerProfile.id.in_([row.customer_profile_id for row in rows]))).all()} if rows else {}
    return {"items": [_conversation_view(row, profiles.get(row.customer_profile_id)) for row in rows]}


@router.get("/projects/{project_id}/conversations/{conversation_id}")
def get_conversation(
    project_id: int,
    conversation_id: UUID,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "conversations:read")
    row = _conversation_for_key(db, project_id, conversation_id, api_key)
    profile = db.get(CustomerProfile, row.customer_profile_id)
    return {"conversation": _conversation_view(row, profile)}


@router.get("/projects/{project_id}/conversations/{conversation_id}/events")
def list_conversation_events(
    project_id: int,
    conversation_id: UUID,
    limit: int = 100,
    before_id: int | None = None,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "conversations:read")
    row = _conversation_for_key(db, project_id, conversation_id, api_key)
    if limit < 1 or limit > 200:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 200")
    query = select(ConversationEvent).where(
        ConversationEvent.conversation_id == row.id,
        ConversationEvent.project_id == project_id,
        ConversationEvent.tenant_id == api_key.tenant_id,
    )
    if before_id is not None:
        query = query.where(ConversationEvent.id < before_id)
    events = db.scalars(query.order_by(desc(ConversationEvent.id)).limit(limit)).all()
    return {"items": [_event_view(event) for event in reversed(events)]}


@router.post("/projects/{project_id}/conversations/{conversation_id}/events", status_code=status.HTTP_201_CREATED)
def append_conversation_event(
    project_id: int,
    conversation_id: UUID,
    payload: ConversationEventCreateRequest,
    response: Response,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "conversations:write")
    row = _conversation_for_key(db, project_id, conversation_id, api_key)
    if row.status == "archived":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="conversation archived")
    if not x_idempotency_key or len(x_idempotency_key.strip()) < 16 or len(x_idempotency_key) > 160:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="X-Idempotency-Key is required")
    idempotency_key = x_idempotency_key.strip()
    request_hash = hashlib.sha256(json.dumps(payload.model_dump(mode="json"), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    endpoint = f"conversation_events:{conversation_id}"
    existing = db.scalar(
        select(IdempotencyRecord).where(
            IdempotencyRecord.tenant_id == api_key.tenant_id,
            IdempotencyRecord.idempotency_key == idempotency_key,
            IdempotencyRecord.endpoint == endpoint,
        )
    )
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency key reused with different payload")
        event_id = (existing.response_json or {}).get("event_id")
        replay_event = db.scalar(
            select(ConversationEvent).where(
                ConversationEvent.event_uuid == UUID(event_id),
                ConversationEvent.tenant_id == api_key.tenant_id,
                ConversationEvent.conversation_id == row.id,
            )
        ) if event_id else None
        if not replay_event:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency record is inconsistent")
        response.status_code = status.HTTP_200_OK
        return {"event": _event_view(replay_event), "conversation_status": row.status, "idempotent_replay": True}
    event = ConversationEvent(
        tenant_id=api_key.tenant_id,
        project_id=project_id,
        conversation_id=row.id,
        customer_profile_id=row.customer_profile_id,
        event_type=payload.event_type,
        direction=payload.direction,
        channel=payload.channel or row.primary_channel,
        actor_type=payload.actor_type,
        content=payload.content,
        metadata_json={**payload.metadata, "idempotency_key": idempotency_key},
    )

    db.add(event)
    db.flush()
    db.add(
        IdempotencyRecord(
            tenant_id=api_key.tenant_id,
            idempotency_key=idempotency_key,
            endpoint=endpoint,
            request_hash=request_hash,
            response_json={"event_id": str(event.event_uuid), "conversation_status": row.status},
            expires_at=_utcnow().replace(year=_utcnow().year + 1),
        )
    )
    now = _utcnow()
    row.last_event_at = now
    if payload.event_type == "handoff":
        row.status = "handoff"
    elif payload.event_type == "message" and row.status == "waiting":
        row.status = "active"
    db.commit()
    db.refresh(event)
    db.refresh(row)
    return {"event": _event_view(event), "conversation_status": row.status, "idempotent_replay": False}


@router.patch("/projects/{project_id}/conversations/{conversation_id}/status")
def update_conversation_status(
    project_id: int,
    conversation_id: UUID,
    payload: ConversationStatusUpdateRequest,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "conversations:write")
    row = _conversation_for_key(db, project_id, conversation_id, api_key)
    previous = row.status
    row.status = payload.status
    row.last_event_at = _utcnow()
    db.add(
        ConversationEvent(
            tenant_id=api_key.tenant_id,
            project_id=project_id,
            conversation_id=row.id,
            customer_profile_id=row.customer_profile_id,
            event_type="status",
            direction="system",
            channel=row.primary_channel,
            actor_type="system",
            content={"from": previous, "to": payload.status},
            metadata_json={},
        )
    )
    db.commit()
    db.refresh(row)
    return {"conversation": {"id": str(row.conversation_uuid), "status": row.status, "updated_at": row.updated_at}}
