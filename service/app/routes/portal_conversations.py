from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_models import Conversation, ConversationEvent, CustomerProfile
from ..platform_rbac import require_tenant_permission

router = APIRouter(prefix="/v1/platform", tags=["platform-conversations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _profile_view(profile: CustomerProfile | None) -> dict | None:
    if not profile:
        return None
    return {"id": str(profile.profile_uuid), "display_name": profile.display_name, "external_ref": profile.external_ref}


def _conversation_view(row: Conversation, profile: CustomerProfile | None) -> dict:
    return {
        "id": str(row.conversation_uuid),
        "project_id": row.project_id,
        "status": row.status,
        "channel": row.primary_channel,
        "subject": row.subject,
        "external_ref": row.external_ref,
        "customer": _profile_view(profile),
        "last_event_at": row.last_event_at,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _tenant_access(request: Request, db: Session, tenant_id: int) -> PanelUser:
    user = get_current_platform_user(request, db)
    require_tenant_permission(db, user, tenant_id, "conversation:read")
    return user


@router.get("/conversations")
def list_portal_conversations(
    tenant_id: int,
    request: Request,
    project_id: int | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    _tenant_access(request, db, tenant_id)
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="limit must be between 1 and 100")
    query = select(Conversation).where(Conversation.tenant_id == tenant_id)
    if project_id is not None:
        query = query.where(Conversation.project_id == project_id)
    if status_filter:
        query = query.where(Conversation.status == status_filter)
    rows = db.scalars(query.order_by(desc(Conversation.updated_at)).limit(limit)).all()
    profiles = {profile.id: profile for profile in db.scalars(select(CustomerProfile).where(CustomerProfile.id.in_([row.customer_profile_id for row in rows]))).all()} if rows else {}
    return {"items": [_conversation_view(row, profiles.get(row.customer_profile_id)) for row in rows]}


@router.get("/conversations/{conversation_id}")
def get_portal_conversation(
    conversation_id: UUID,
    tenant_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    _tenant_access(request, db, tenant_id)
    row = db.scalar(select(Conversation).where(Conversation.conversation_uuid == conversation_id, Conversation.tenant_id == tenant_id))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="conversation not found")
    profile = db.get(CustomerProfile, row.customer_profile_id)
    events = db.scalars(
        select(ConversationEvent).where(
            ConversationEvent.conversation_id == row.id,
            ConversationEvent.tenant_id == tenant_id,
        ).order_by(ConversationEvent.id.desc()).limit(100)
    ).all()
    return {
        "conversation": _conversation_view(row, profile),
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
