from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..platform_models import ProviderResource, WebhookDelivery, WebhookEvent, WebhookSubscription
from ..platform_webhook_events import canonical_event_type, subscription_event_matches

router = APIRouter(prefix="/v1/webhooks", tags=["webhooks"])
MAX_META_PAYLOAD_BYTES = 3 * 1024 * 1024


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _verify_token() -> str:
    value = os.getenv("META_WEBHOOK_VERIFY_TOKEN", "")
    if not value:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="webhook is not configured")
    return value


def _app_secret() -> str:
    value = os.getenv("META_APP_SECRET", "")
    if not value:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="webhook is not configured")
    return value


def _event_items(payload: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    events: list[tuple[str, str, dict[str, Any]]] = []
    for entry in payload.get("entry", []) if isinstance(payload.get("entry"), list) else []:
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []) if isinstance(entry.get("changes"), list) else []:
            if not isinstance(change, dict):
                continue
            field = str(change.get("field") or "unknown")
            value = change.get("value") if isinstance(change.get("value"), dict) else {}
            nested = []
            for collection_name in ("messages", "statuses", "errors", "calls"):
                collection = value.get(collection_name)
                if isinstance(collection, list):
                    nested.extend(item for item in collection if isinstance(item, dict))
            if not nested:
                nested = [value]
            for item in nested:
                item_id = item.get("id") or item.get("message_id") or item.get("wamid")
                stable = str(item_id or hashlib.sha256(json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest())
                events.append((f"{field}:{stable}", field, {"entry": entry, "change": change, "item": item}))
    return events


def _resource_for_event(db: Session, event_payload: dict[str, Any]) -> ProviderResource | None:
    change = event_payload.get("change") if isinstance(event_payload.get("change"), dict) else {}
    value = change.get("value") if isinstance(change.get("value"), dict) else {}
    metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
    phone_number_id = metadata.get("phone_number_id")
    if not phone_number_id:
        return None
    return db.scalar(
        select(ProviderResource).where(
            ProviderResource.provider_type == "meta_cloud",
            ProviderResource.provider_resource_id == str(phone_number_id),
            ProviderResource.status == "active",
        ).order_by(ProviderResource.id)
    )


def _signature_is_valid(body: bytes, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(_app_secret().encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature[7:], expected)


@router.get("/meta")
def verify_meta_webhook(
    hub_mode: str | None = None,
    hub_verify_token: str | None = None,
    hub_challenge: str | None = None,
):
    if hub_mode != "subscribe" or not hub_verify_token or not hmac.compare_digest(hub_verify_token, _verify_token()):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="verification failed")
    if not hub_challenge:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="challenge required")
    return Response(content=hub_challenge, media_type="text/plain")


@router.post("/meta")
async def receive_meta_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    body = await request.body()
    if len(body) > MAX_META_PAYLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="payload too large")
    if not _signature_is_valid(body, x_hub_signature_256):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid webhook signature")
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="JSON object required")

    accepted = 0
    duplicate = 0
    for provider_event_id, raw_event_type, event_payload in _event_items(payload):
        canonical_type = canonical_event_type(raw_event_type, event_payload)
        existing = db.scalar(
            select(WebhookEvent.id).where(
                WebhookEvent.provider_type == "meta_cloud",
                WebhookEvent.provider_event_id == provider_event_id,
            )
        )
        if existing:
            duplicate += 1
            continue
        resource = _resource_for_event(db, event_payload)
        event = WebhookEvent(
            provider_type="meta_cloud",
            provider_event_id=provider_event_id,
            tenant_id=resource.tenant_id if resource else None,
            resource_id=resource.id if resource else None,
            event_type=canonical_type,
            payload=event_payload,
            status="accepted" if resource else "unmapped",
            attempts=0,
        )
        db.add(event)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            duplicate += 1
            continue
        if resource:
            subscriptions = db.scalars(
                select(WebhookSubscription).where(
                    WebhookSubscription.tenant_id == resource.tenant_id,
                    WebhookSubscription.project_id == resource.project_id,
                    WebhookSubscription.status == "active",
                )
            ).all()
            deliveries = [
                WebhookDelivery(subscription_id=subscription.id, event_id=event.id)
                for subscription in subscriptions
                if subscription_event_matches(subscription.events, canonical_type, raw_event_type)
            ]
            if deliveries:
                db.add_all(deliveries)
                db.commit()
        accepted += 1
    return {"ok": True, "accepted": accepted, "duplicates": duplicate}
