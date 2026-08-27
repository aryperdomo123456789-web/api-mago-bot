from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from sqlalchemy import select

from .db import SessionLocal
from .platform_crypto import decrypt_secret
from .platform_models import WebhookDelivery, WebhookEvent, WebhookSubscription
from .platform_webhook_events import canonical_event_type
from .platform_ssrf import UnsafeWebhookEndpoint, validate_webhook_endpoint

MAX_ATTEMPTS = int(os.getenv("WEBHOOK_MAX_ATTEMPTS", "10"))
POLL_SECONDS = float(os.getenv("WEBHOOK_POLL_SECONDS", "2"))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def build_signed_delivery(event: WebhookEvent, delivery: WebhookDelivery, secret: str) -> tuple[bytes, dict[str, str]]:
    event_type = canonical_event_type(event.event_type, event.payload)
    body_data = {
        "id": str(event.event_uuid),
        "type": event_type,
        "provider": event.provider_type,
        "created_at": event.received_at.isoformat() if event.received_at else None,
        "data": event.payload,
    }
    body = json.dumps(body_data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "MagoBot-Webhooks/1.0",
        "X-Mago-Signature": _signature(secret, body),
        "X-Mago-Event-ID": str(event.event_uuid),
        "X-Mago-Delivery-ID": str(delivery.delivery_uuid),
        "X-Mago-Event-Type": event_type,
    }
    return body, headers


async def deliver_one() -> bool:
    db = SessionLocal()
    try:
        delivery = db.scalar(
            select(WebhookDelivery)
            .where(
                WebhookDelivery.status.in_(["pending", "retrying"]),
                WebhookDelivery.next_attempt_at <= _now(),
            )
            .order_by(WebhookDelivery.id)
            .with_for_update(skip_locked=True)
        )
        if not delivery:
            return False
        delivery.status = "processing"
        delivery.attempt_count += 1
        db.commit()
        subscription = db.get(WebhookSubscription, delivery.subscription_id)
        event = db.get(WebhookEvent, delivery.event_id)
        if not subscription or subscription.status != "active" or not event:
            delivery.status = "cancelled"
            db.commit()
            return True
        body, signed_headers = build_signed_delivery(event, delivery, decrypt_secret(subscription.secret_encrypted))
        try:
            endpoint_url = await asyncio.to_thread(validate_webhook_endpoint, subscription.endpoint_url)
            async with httpx.AsyncClient(timeout=10, follow_redirects=False) as client:
                response = await client.post(
                    endpoint_url,
                    content=body,
                    headers=signed_headers,
                )
            delivery.response_code = response.status_code
            if 200 <= response.status_code < 300:
                delivery.status = "delivered"
                delivery.delivered_at = _now()
                subscription.last_delivery_at = _now()
                subscription.failure_count = 0
            else:
                raise RuntimeError(f"endpoint returned HTTP {response.status_code}")
        except UnsafeWebhookEndpoint as exc:
            delivery.last_error = f"unsafe webhook endpoint: {exc}"[:512]
            delivery.status = "dead_letter"
            subscription.failure_count += 1
        except Exception as exc:
            delivery.last_error = str(exc)[:512]
            subscription.failure_count += 1
            if delivery.attempt_count >= MAX_ATTEMPTS:
                delivery.status = "dead_letter"
            else:
                delivery.status = "retrying"
                delay = min(3600, 2 ** min(delivery.attempt_count, 10))
                delivery.next_attempt_at = _now() + timedelta(seconds=delay)
        db.commit()
        return True
    finally:
        db.close()


async def run_worker() -> None:
    heartbeat = Path(os.getenv("WEBHOOK_WORKER_HEARTBEAT", "/tmp/mago_webhook_worker_heartbeat"))
    while True:
        heartbeat.touch()
        processed = await deliver_one()
        if not processed:
            await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
