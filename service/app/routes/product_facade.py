from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_limits import get_service_api_key
from ..platform_models import (
    Conversation,
    EvolutionInstance,
    PlatformProject,
    ProviderResource,
    Subscription,
    Tenant,
    TenantMembership,
    UsageLedgerEntry,
)
from ..conversation_schemas import ConversationCreateRequest, ConversationEventCreateRequest, ConversationStatusUpdateRequest
from ..platform_schemas import MessageSendRequest
from .conversations import (
    append_conversation_event,
    create_conversation,
    get_conversation,
    list_conversation_events,
    list_conversations,
    update_conversation_status,
)
from .messages import get_message, list_messages, send_message

router = APIRouter(prefix="/v1", tags=["product-facade"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user(request: Request, db: Session) -> PanelUser:
    return get_current_platform_user(request, db)


def _resolve_project_id(db: Session, project_uuid: UUID, tenant_id: int, key_project_id: int | None = None) -> int:
    project = db.scalar(select(PlatformProject).where(
        PlatformProject.project_uuid == project_uuid,
        PlatformProject.tenant_id == tenant_id,
        PlatformProject.status == "active",
    ))
    if not project or (key_project_id is not None and key_project_id != project.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    return project.id


def _tenant_rows(db: Session, user: PanelUser, tenant_uuid: str | None = None):
    # Global platform roles receive a read/write wildcard over active tenants, but
    # the synthetic membership is never persisted and carries no customer grant.
    if user.role in {"owner", "platform_superadmin", "platform_operator"}:
        query = select(Tenant).where(Tenant.status == "active").order_by(Tenant.created_at.asc())
        if tenant_uuid:
            query = query.where(Tenant.tenant_uuid == tenant_uuid)
        tenants = db.scalars(query).all()
        return [
            (tenant, TenantMembership(tenant_id=tenant.id, user_id=user.id, role=user.role, status="active"))
            for tenant in tenants
        ]

    query = (
        select(Tenant, TenantMembership)
        .join(TenantMembership, TenantMembership.tenant_id == Tenant.id)
        .where(TenantMembership.user_id == user.id, TenantMembership.status == "active", Tenant.status == "active")
        .order_by(Tenant.created_at.asc())
    )
    rows = db.execute(query).all()
    if tenant_uuid:
        rows = [row for row in rows if str(row[0].tenant_uuid) == tenant_uuid]
    return rows


def _tenant_ids(db: Session, user: PanelUser, tenant_uuid: str | None = None) -> set[int]:
    return {tenant.id for tenant, _membership in _tenant_rows(db, user, tenant_uuid)}


def _tenant_map(db: Session, tenant_ids: set[int]) -> dict[int, Tenant]:
    if not tenant_ids:
        return {}
    return {tenant.id: tenant for tenant in db.scalars(select(Tenant).where(Tenant.id.in_(tenant_ids))).all()}


def _tenant_view(tenant: Tenant, membership: TenantMembership) -> dict:
    return {
        "id": str(tenant.tenant_uuid),
        "slug": tenant.slug,
        "name": tenant.legal_name,
        "status": tenant.status,
        "plan": tenant.plan_slug,
        "role": membership.role,
        "created_at": tenant.created_at,
    }


def _capabilities(provider_type: str, instance: EvolutionInstance | None = None) -> list[str]:
    if provider_type == "evolution":
        if instance and instance.status != "connected":
            return ["status", "qr", "pairing", "reconnect", "webhooks"]
        return ["text", "image", "video", "audio", "document", "status", "webhooks", "reconnect"]
    if provider_type == "meta_cloud":
        return ["text", "template", "image", "video", "audio", "document", "status", "webhooks"]
    return ["status", "webhooks"]


def _resource_view(resource: ProviderResource, project: PlatformProject, instance: EvolutionInstance | None, tenant: Tenant) -> dict:
    current_status = instance.status if instance else resource.status
    return {
        "id": str(resource.resource_uuid),
        "organization_id": str(tenant.tenant_uuid),
        "project_id": str(project.project_uuid),
        "name": resource.display_name,
        "provider": resource.provider_type,
        "provider_resource_id": resource.provider_resource_id,
        "status": current_status,
        "connection": {
            "instance_id": str(instance.instance_uuid) if instance else None,
            "instance_name": instance.instance_name if instance else None,
            "phone_number": instance.display_phone_number if instance else None,
            "last_status_check_at": instance.last_status_check_at if instance else None,
            "last_connected_at": instance.last_connected_at if instance else None,
        },
        "capabilities": _capabilities(resource.provider_type, instance),
        "created_at": resource.created_at,
        "updated_at": resource.updated_at,
    }


@router.get("/organizations")
def list_organizations(request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    return {"items": [_tenant_view(tenant, membership) for tenant, membership in _tenant_rows(db, user)]}


@router.get("/integrations")
def list_integrations(
    request: Request,
    organization_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    user = _user(request, db)
    allowed_ids = _tenant_ids(db, user, organization_id)
    if not allowed_ids:
        return {"items": []}
    projects = {
        project.id: project
        for project in db.scalars(select(PlatformProject).where(PlatformProject.tenant_id.in_(allowed_ids))).all()
    }
    tenant_map = _tenant_map(db, allowed_ids)
    instances = {
        instance.resource_id: instance
        for instance in db.scalars(select(EvolutionInstance).where(EvolutionInstance.tenant_id.in_(allowed_ids))).all()
        if instance.resource_id is not None
    }
    resources = db.scalars(
        select(ProviderResource)
        .where(ProviderResource.tenant_id.in_(allowed_ids))
        .order_by(ProviderResource.created_at.asc())
    ).all()
    items = []
    for resource in resources:
        project = projects.get(resource.project_id)
        tenant = tenant_map.get(resource.tenant_id)
        if project and tenant:
            items.append(_resource_view(resource, project, instances.get(resource.id), tenant))
    return {"items": items}


@router.get("/channels")
def list_channels(
    request: Request,
    organization_id: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    payload = list_integrations(request, organization_id, db)
    return {
        "items": [
            {
                "id": item["id"],
                "organization_id": item["organization_id"],
                "project_id": item["project_id"],
                "name": item["name"],
                "type": item["provider"],
                "status": item["status"],
                "capabilities": item["capabilities"],
                "connection": item["connection"],
                "updated_at": item["updated_at"],
            }
            for item in payload["items"]
        ]
    }


@router.get("/billing")
def billing_summary(request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    allowed_ids = _tenant_ids(db, user)
    tenant_map = _tenant_map(db, allowed_ids)
    subscriptions = db.scalars(
        select(Subscription).where(Subscription.tenant_id.in_(allowed_ids)).order_by(Subscription.created_at.desc())
    ).all() if allowed_ids else []
    return {
        "items": [
            {
                "organization_id": str(tenant_map[row.tenant_id].tenant_uuid) if row.tenant_id in tenant_map else None,
                "plan": row.plan_slug,
                "status": row.status,
                "current_period_start": row.current_period_start,
                "current_period_end": row.current_period_end,
                "external_customer_configured": bool(row.external_customer_id),
                "external_subscription_configured": bool(row.external_subscription_id),
            }
            for row in subscriptions
        ],
        "checkout": {"available": False, "message": "Checkout será habilitado no próximo pacote comercial."},
    }


@router.get("/analytics")
def analytics_summary(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    db: Session = Depends(get_db),
):
    user = _user(request, db)
    allowed_ids = _tenant_ids(db, user)
    if not allowed_ids:
        return {"period_days": days, "items": [], "totals": {"units": 0, "cost_micros": 0}}
    since = datetime.now(timezone.utc) - timedelta(days=days)
    entries = db.scalars(
        select(UsageLedgerEntry)
        .where(UsageLedgerEntry.tenant_id.in_(allowed_ids), UsageLedgerEntry.created_at >= since)
        .order_by(UsageLedgerEntry.created_at.desc())
        .limit(5000)
    ).all()
    grouped: dict[tuple[str, str], dict[str, int | str]] = defaultdict(
        lambda: {"metric": "", "provider": "", "units": 0, "cost_micros": 0}
    )
    for entry in entries:
        key = (entry.metric, entry.provider_type or "unknown")
        item = grouped[key]
        item["metric"] = entry.metric
        item["provider"] = entry.provider_type or "unknown"
        item["units"] = int(item["units"]) + int(entry.units or 0)
        item["cost_micros"] = int(item["cost_micros"]) + int(entry.cost_micros or 0)
    totals = {
        "units": sum(int(item["units"]) for item in grouped.values()),
        "cost_micros": sum(int(item["cost_micros"]) for item in grouped.values()),
    }
    return {"period_days": days, "items": list(grouped.values()), "totals": totals}


@router.get("/jobs")
def jobs_catalog(request: Request, db: Session = Depends(get_db)):
    _user(request, db)
    return {
        "items": [],
        "supported": ["webhook_delivery", "email_delivery", "evolution_health"],
        "message": "O catálogo de jobs está disponível; listagem detalhada entra no próximo pacote de observabilidade.",
    }


@router.post("/messages", status_code=status.HTTP_201_CREATED)
async def send_product_message(
    request: Request,
    response: Response,
    payload: MessageSendRequest,
    project_id: UUID = Query(...),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    x_resource_id: int | None = Header(default=None, alias="X-Resource-Id"),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return await send_message(internal_project_id, payload, request, response, x_idempotency_key, x_resource_id, db, api_key)


@router.get("/messages")
def list_product_messages(
    request: Request,
    project_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return list_messages(internal_project_id, request, limit, db, api_key)


@router.get("/messages/{message_id}")
def get_product_message(
    request: Request,
    message_id: str,
    project_id: UUID = Query(...),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return get_message(internal_project_id, message_id, request, db, api_key)


@router.post("/conversations", status_code=status.HTTP_201_CREATED)
def create_product_conversation(
    response: Response,
    payload: ConversationCreateRequest,
    project_id: UUID = Query(...),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return create_conversation(internal_project_id, payload, response, db, api_key)


@router.get("/conversations")
def list_product_conversations(
    project_id: UUID = Query(...),
    limit: int = Query(default=50, ge=1, le=100),
    status_filter: str | None = Query(default=None),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return list_conversations(internal_project_id, limit, status_filter, db, api_key)


@router.get("/conversations/{conversation_id}")
def get_product_conversation(
    conversation_id: UUID,
    project_id: UUID = Query(...),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return get_conversation(internal_project_id, conversation_id, db, api_key)


@router.get("/conversations/{conversation_id}/events")
def list_product_conversation_events(
    conversation_id: UUID,
    project_id: UUID = Query(...),
    limit: int = Query(default=100, ge=1, le=200),
    before_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return list_conversation_events(internal_project_id, conversation_id, limit, before_id, db, api_key)


@router.post("/conversations/{conversation_id}/events", status_code=status.HTTP_201_CREATED)
def append_product_conversation_event(
    response: Response,
    conversation_id: UUID,
    payload: ConversationEventCreateRequest,
    project_id: UUID = Query(...),
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return append_conversation_event(internal_project_id, conversation_id, payload, response, x_idempotency_key, db, api_key)


@router.patch("/conversations/{conversation_id}/status")
def update_product_conversation_status(
    conversation_id: UUID,
    payload: ConversationStatusUpdateRequest,
    project_id: UUID = Query(...),
    db: Session = Depends(get_db),
    api_key=Depends(get_service_api_key),
):
    internal_project_id = _resolve_project_id(db, project_id, api_key.tenant_id, api_key.project_id)
    return update_conversation_status(internal_project_id, conversation_id, payload, db, api_key)
