from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..platform_models import EmailDelivery, EmailProviderEvent, EmailSuppression
from ..providers.resend_email import normalize_email

router = APIRouter(prefix="/v1/webhooks/email", tags=["email-webhooks"])
MAX_CLOCK_SKEW_SECONDS = 300


def _webhook_key() -> bytes | None:
    secret = os.getenv("RESEND_WEBHOOK_SIGNING_SECRET", "").strip()
    if not secret:
        return None
    encoded = secret.removeprefix("whsec_")
    try:
        return base64.b64decode(encoded + "=" * (-len(encoded) % 4))
    except (ValueError, base64.binascii.Error):
        return None


def _signature_valid(request: Request, body: bytes) -> bool:
    key = _webhook_key()
    svix_id = request.headers.get("svix-id", "").strip()
    timestamp = request.headers.get("svix-timestamp", "").strip()
    supplied = request.headers.get("svix-signature", "").strip()
    if not key or not svix_id or not timestamp or not supplied:
        return False
    try:
        timestamp_int = int(timestamp)
    except ValueError:
        return False
    if abs(int(time.time()) - timestamp_int) > MAX_CLOCK_SKEW_SECONDS:
        return False
    signed = f"{svix_id}.{timestamp}.".encode("utf-8") + body
    expected = base64.b64encode(hmac.new(key, signed, hashlib.sha256).digest()).decode("ascii")
    return any(
        part.startswith("v1,") and hmac.compare_digest(part[3:], expected)
        for part in supplied.split()
    )


def _recipient(data: dict) -> str | None:
    values = data.get("to")
    if isinstance(values, list) and values:
        raw = values[0]
    else:
        raw = values
    if not isinstance(raw, str):
        return None
    if "<" in raw and ">" in raw:
        raw = raw.rsplit("<", 1)[1].split(">", 1)[0]
    return normalize_email(raw)


@router.post("/resend")
async def resend_webhook(request: Request):
    body = await request.body()
    if not _signature_valid(request, body):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid webhook signature")
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid webhook payload") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid webhook payload")

    provider_event_id = request.headers.get("svix-id", "").strip()
    event_type = str(payload.get("type") or "unknown")[:80]
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    email_id = str(data.get("email_id") or data.get("id") or "").strip()[:180] or None
    recipient = _recipient(data)

    db = SessionLocal()
    try:
        event = EmailProviderEvent(
            provider="resend",
            provider_event_id=provider_event_id,
            event_type=event_type,
            email_id=email_id,
            recipient_email=recipient,
            payload=payload,
        )
        try:
            with db.begin_nested():
                db.add(event)
                db.flush()
        except IntegrityError:
            db.rollback()
            return {"ok": True, "duplicate": True}

        delivery = db.scalar(select(EmailDelivery).where(EmailDelivery.provider_message_id == email_id)) if email_id else None
        if delivery:
            delivery.provider_event_id = provider_event_id
            if event_type == "email.delivered":
                delivery.status = "delivered"
                delivery.delivered_at = delivery.delivered_at or event.received_at
            elif event_type in {"email.bounced", "email.complained"}:
                delivery.status = "bounced" if event_type.endswith("bounced") else "complained"
                delivery.error_code = event_type.replace("email.", "")[:80]
                delivery.error_message = "Recipient suppressed by provider event"
                if recipient:
                    existing = db.scalar(select(EmailSuppression).where(EmailSuppression.email == recipient))
                    if existing:
                        existing.reason = "bounce" if event_type.endswith("bounced") else "complaint"
                        existing.provider_event_id = provider_event_id
                    else:
                        db.add(EmailSuppression(email=recipient, reason="bounce" if event_type.endswith("bounced") else "complaint", provider_event_id=provider_event_id))
            elif event_type == "email.failed":
                delivery.status = "failed"
                delivery.error_code = "provider_failed"
                delivery.error_message = "Provider reported email failure"
        db.commit()
        return {"ok": True, "duplicate": False}
    finally:
        db.close()
