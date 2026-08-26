from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_models import AuditEvent, Conversation, ConversationAssignment, ConversationEvent, CustomerProfile, InboxQueue, PlatformProject, Tenant
from ..platform_rbac import require_tenant_permission

router = APIRouter(prefix="/v1/platform/inbox", tags=["inbox"])


class QueueCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str = Field(min_length=2, max_length=120)
    project_id: int = Field(gt=0)
    routing_strategy: Literal["manual", "round_robin"] = "manual"


class AssignmentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_user_id: int | None = Field(default=None, gt=0)
    queue_id: int | None = Field(default=None, gt=0)


class SnoozeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    until: datetime = Field(description="UTC timestamp; must be in the future")


class NoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=4000)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(request: Request, db: Session) -> PanelUser:
    return get_current_platform_user(request, db)


def _tenant(db: Session, actor: PanelUser, tenant_id: int, permission: str = "conversation:read") -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="organization not found")
    require_tenant_permission(db, actor, tenant_id, permission)
    return tenant


def _conversation(db: Session, actor: PanelUser, tenant_id: int, conversation_id: UUID, *, write: bool = False) -> Conversation:
    _tenant(db, actor, tenant_id, "conversation:write" if write else "conversation:read")
    row = db.scalar(select(Conversation).where(
        Conversation.conversation_uuid == conversation_id,
        Conversation.tenant_id == tenant_id,
    ))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    return row


def _project(db: Session, tenant_id: int, project_id: int) -> PlatformProject:
    row = db.scalar(select(PlatformProject).where(
        PlatformProject.id == project_id,
        PlatformProject.tenant_id == tenant_id,
        PlatformProject.status == "active",
    ))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return row


def _assignment(db: Session, conversation: Conversation, *, create: bool = True) -> ConversationAssignment | None:
    row = db.scalar(select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation.id))
    if row or not create:
        return row
    row = ConversationAssignment(
        tenant_id=conversation.tenant_id,
        project_id=conversation.project_id,
        conversation_id=conversation.id,
        state="unassigned",
    )
    db.add(row)
    db.flush()
    return row


def _queue(db: Session, tenant_id: int, project_id: int, queue_id: int | None) -> InboxQueue | None:
    if queue_id is None:
        return None
    row = db.scalar(select(InboxQueue).where(
        InboxQueue.id == queue_id,
        InboxQueue.tenant_id == tenant_id,
        InboxQueue.project_id == project_id,
        InboxQueue.status == "active",
    ))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="queue not found")
    return row


def _assignee(db: Session, tenant_id: int, assignee_user_id: int | None) -> PanelUser | None:
    if assignee_user_id is None:
        return None
    user = db.get(PanelUser, assignee_user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignee not found")
    from ..platform_models import TenantMembership
    membership = db.scalar(select(TenantMembership).where(
        TenantMembership.tenant_id == tenant_id,
        TenantMembership.user_id == assignee_user_id,
        TenantMembership.status == "active",
    ))
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="assignee not found")
    return user


def _audit(db: Session, request: Request, actor: PanelUser, tenant_id: int, action: str, conversation: Conversation | None = None, metadata: dict | None = None) -> None:
    db.add(AuditEvent(
        tenant_id=tenant_id,
        actor_user_id=actor.id,
        action=action,
        resource_type="conversation",
        resource_id=str(conversation.conversation_uuid) if conversation else None,
        outcome="success",
        request_id=str(getattr(request.state, "request_id", ""))[:80] or None,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:512],
        metadata_json=metadata or {},
    ))


def _assignment_view(row: ConversationAssignment | None, queue: InboxQueue | None, assignee: PanelUser | None) -> dict:
    return {
        "id": str(row.assignment_uuid) if row else None,
        "state": row.state if row else "unassigned",
        "queue": {"id": str(queue.queue_uuid), "slug": queue.slug, "display_name": queue.display_name} if queue else None,
        "assignee": {"id": assignee.id, "name": assignee.full_name, "email": assignee.email} if assignee else None,
        "snoozed_until": row.snoozed_until if row else None,
        "claimed_at": row.claimed_at if row else None,
        "updated_at": row.updated_at if row else None,
    }


def _conversation_view(db: Session, row: Conversation) -> dict:
    profile = db.get(CustomerProfile, row.customer_profile_id)
    assignment = _assignment(db, row, create=False)
    queue = db.get(InboxQueue, assignment.queue_id) if assignment and assignment.queue_id else None
    assignee = db.get(PanelUser, assignment.assignee_user_id) if assignment and assignment.assignee_user_id else None
    return {
        "id": str(row.conversation_uuid),
        "project_id": row.project_id,
        "status": row.status,
        "channel": row.primary_channel,
        "subject": row.subject,
        "external_ref": row.external_ref,
        "customer": {"id": str(profile.profile_uuid), "display_name": profile.display_name, "external_ref": profile.external_ref} if profile else None,
        "assignment": _assignment_view(assignment, queue, assignee),
        "last_event_at": row.last_event_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _append_system_event(db: Session, conversation: Conversation, event_type: str, actor: PanelUser, content: dict) -> None:
    db.add(ConversationEvent(
        tenant_id=conversation.tenant_id,
        project_id=conversation.project_id,
        conversation_id=conversation.id,
        customer_profile_id=conversation.customer_profile_id,
        event_type=event_type,
        direction="internal" if event_type in {"assignment", "note"} else "system",
        channel=conversation.primary_channel,
        actor_type="human_agent",
        content=content,
        metadata_json={"actor_user_id": actor.id},
    ))
    conversation.last_event_at = _now()


@router.get("/queues")
def list_queues(tenant_id: int, request: Request, project_id: int | None = None, db: Session = Depends(get_db)):
    actor = _user(request, db)
    _tenant(db, actor, tenant_id)
    query = select(InboxQueue).where(InboxQueue.tenant_id == tenant_id, InboxQueue.status == "active")
    if project_id is not None:
        _project(db, tenant_id, project_id)
        query = query.where(InboxQueue.project_id == project_id)
    rows = db.scalars(query.order_by(InboxQueue.display_name)).all()
    return {"items": [{"id": str(row.queue_uuid), "internal_id": row.id, "project_id": row.project_id, "slug": row.slug, "display_name": row.display_name, "routing_strategy": row.routing_strategy, "status": row.status} for row in rows]}


@router.post("/queues", status_code=status.HTTP_201_CREATED)
def create_queue(tenant_id: int, payload: QueueCreateRequest, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    _tenant(db, actor, tenant_id, "project:write")
    _project(db, tenant_id, payload.project_id)
    if db.scalar(select(InboxQueue.id).where(InboxQueue.tenant_id == tenant_id, InboxQueue.project_id == payload.project_id, InboxQueue.slug == payload.slug)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="queue already exists")
    row = InboxQueue(tenant_id=tenant_id, project_id=payload.project_id, slug=payload.slug, display_name=payload.display_name.strip(), routing_strategy=payload.routing_strategy)
    db.add(row)
    _audit(db, request, actor, tenant_id, "inbox.queue.create", metadata={"slug": payload.slug})
    db.commit()
    db.refresh(row)
    return {"queue": {"id": str(row.queue_uuid), "internal_id": row.id, "project_id": row.project_id, "slug": row.slug, "display_name": row.display_name, "routing_strategy": row.routing_strategy, "status": row.status}}


@router.get("/conversations")
def list_inbox_conversations(
    tenant_id: int,
    request: Request,
    project_id: int | None = None,
    state: str | None = Query(default=None, max_length=24),
    status_filter: str | None = Query(default=None, alias="status", max_length=24),
    assignee_user_id: int | None = Query(default=None, gt=0),
    queue_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    actor = _user(request, db)
    _tenant(db, actor, tenant_id)
    query = select(Conversation).where(Conversation.tenant_id == tenant_id)
    if project_id is not None:
        _project(db, tenant_id, project_id)
        query = query.where(Conversation.project_id == project_id)
    if status_filter:
        query = query.where(Conversation.status == status_filter)
    rows = db.scalars(query.order_by(desc(Conversation.updated_at)).limit(limit)).all()
    items = []
    for row in rows:
        assignment = _assignment(db, row, create=False)
        if state and (assignment.state if assignment else "unassigned") != state:
            continue
        if assignee_user_id and (assignment.assignee_user_id if assignment else None) != assignee_user_id:
            continue
        if queue_id and (assignment.queue_id if assignment else None) != queue_id:
            continue
        items.append(_conversation_view(db, row))
    return {"items": items, "next_cursor": None}


@router.post("/conversations/{conversation_id}/claim")
def claim_conversation(conversation_id: UUID, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    assignment = db.scalar(select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation.id).with_for_update()) or _assignment(db, conversation)
    assignment.assignee_user_id = actor.id
    assignment.state = "claimed"
    assignment.claimed_at = _now()
    assignment.released_at = None
    _append_system_event(db, conversation, "assignment", actor, {"action": "claimed", "assignee_user_id": actor.id})
    _audit(db, request, actor, tenant_id, "inbox.conversation.claim", conversation)
    db.commit()
    return {"conversation": _conversation_view(db, conversation)}


@router.post("/conversations/{conversation_id}/assign")
def assign_conversation(conversation_id: UUID, tenant_id: int, payload: AssignmentRequest, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    _queue(db, tenant_id, conversation.project_id, payload.queue_id)
    assignee = _assignee(db, tenant_id, payload.assignee_user_id)
    assignment = db.scalar(select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation.id).with_for_update()) or _assignment(db, conversation)
    assignment.queue_id = payload.queue_id
    assignment.assignee_user_id = payload.assignee_user_id
    assignment.state = "assigned" if payload.assignee_user_id or payload.queue_id else "unassigned"
    assignment.claimed_at = _now() if payload.assignee_user_id else assignment.claimed_at
    _append_system_event(db, conversation, "assignment", actor, {"action": "assigned", "assignee_user_id": payload.assignee_user_id, "queue_id": payload.queue_id})
    _audit(db, request, actor, tenant_id, "inbox.conversation.assign", conversation, {"queue_id": payload.queue_id, "assignee_user_id": payload.assignee_user_id})
    db.commit()
    return {"conversation": _conversation_view(db, conversation)}


@router.post("/conversations/{conversation_id}/release")
def release_conversation(conversation_id: UUID, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    assignment = db.scalar(select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation.id).with_for_update()) or _assignment(db, conversation)
    assignment.assignee_user_id = None
    assignment.state = "queued" if assignment.queue_id else "unassigned"
    assignment.released_at = _now()
    _append_system_event(db, conversation, "assignment", actor, {"action": "released"})
    _audit(db, request, actor, tenant_id, "inbox.conversation.release", conversation)
    db.commit()
    return {"conversation": _conversation_view(db, conversation)}


@router.post("/conversations/{conversation_id}/snooze")
def snooze_conversation(conversation_id: UUID, tenant_id: int, payload: SnoozeRequest, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    until = payload.until if payload.until.tzinfo else payload.until.replace(tzinfo=timezone.utc)
    if until <= _now():
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="snooze time must be in the future")
    assignment = db.scalar(select(ConversationAssignment).where(ConversationAssignment.conversation_id == conversation.id).with_for_update()) or _assignment(db, conversation)
    assignment.snoozed_until = until
    assignment.state = "snoozed"
    _append_system_event(db, conversation, "assignment", actor, {"action": "snoozed", "until": until.isoformat()})
    _audit(db, request, actor, tenant_id, "inbox.conversation.snooze", conversation, {"until": until.isoformat()})
    db.commit()
    return {"conversation": _conversation_view(db, conversation)}


@router.post("/conversations/{conversation_id}/resolve")
def resolve_conversation(conversation_id: UUID, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    conversation.status = "closed"
    assignment = _assignment(db, conversation)
    assignment.state = "resolved"
    _append_system_event(db, conversation, "status", actor, {"action": "resolved"})
    _audit(db, request, actor, tenant_id, "inbox.conversation.resolve", conversation)
    db.commit()
    return {"conversation": _conversation_view(db, conversation)}


@router.post("/conversations/{conversation_id}/reopen")
def reopen_conversation(conversation_id: UUID, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    conversation.status = "active"
    assignment = _assignment(db, conversation)
    assignment.state = "unassigned"
    assignment.snoozed_until = None
    _append_system_event(db, conversation, "status", actor, {"action": "reopened"})
    _audit(db, request, actor, tenant_id, "inbox.conversation.reopen", conversation)
    db.commit()
    return {"conversation": _conversation_view(db, conversation)}


@router.post("/conversations/{conversation_id}/notes", status_code=status.HTTP_201_CREATED)
def add_note(conversation_id: UUID, tenant_id: int, payload: NoteRequest, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=True)
    _append_system_event(db, conversation, "note", actor, {"text": payload.content.strip()})
    _audit(db, request, actor, tenant_id, "inbox.conversation.note", conversation)
    db.commit()
    return {"ok": True, "conversation": _conversation_view(db, conversation)}


@router.get("/conversations/{conversation_id}")
def get_inbox_conversation(conversation_id: UUID, tenant_id: int, request: Request, db: Session = Depends(get_db)):
    actor = _user(request, db)
    conversation = _conversation(db, actor, tenant_id, conversation_id, write=False)
    events = db.scalars(select(ConversationEvent).where(
        ConversationEvent.conversation_id == conversation.id,
        ConversationEvent.tenant_id == tenant_id,
    ).order_by(ConversationEvent.id.desc()).limit(100)).all()
    return {
        "conversation": _conversation_view(db, conversation),
        "events": [
            {
                "id": str(event.event_uuid),
                "type": event.event_type,
                "direction": event.direction,
                "channel": event.channel,
                "actor_type": event.actor_type,
                "content": event.content,
                "created_at": event.created_at,
            }
            for event in reversed(events)
        ],
    }
