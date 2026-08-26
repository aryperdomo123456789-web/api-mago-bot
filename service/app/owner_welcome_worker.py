from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .db import SessionLocal
from .platform_crypto import decrypt_secret
from .platform_models import OwnerWelcomeDelivery, OwnerWhatsAppIntegration
from .providers.owner_meta import OwnerMetaCloudClient, OwnerMetaError

logger = logging.getLogger("mago.owner_welcome")
POLL_SECONDS = max(2, int(os.getenv("OWNER_WELCOME_POLL_SECONDS", "5")))
MAX_ATTEMPTS = max(1, int(os.getenv("OWNER_WELCOME_MAX_ATTEMPTS", "5")))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def claim_one() -> OwnerWelcomeDelivery | None:
    db = SessionLocal()
    try:
        row = db.scalar(
            select(OwnerWelcomeDelivery)
            .where(
                OwnerWelcomeDelivery.status == "pending",
                OwnerWelcomeDelivery.next_attempt_at <= _now(),
            )
            .order_by(OwnerWelcomeDelivery.id.asc())
            .with_for_update(skip_locked=True)
        )
        if not row:
            return None
        row.status = "sending"
        row.attempt_count += 1
        db.commit()
        db.refresh(row)
        return row
    finally:
        db.close()


async def deliver_one(delivery_id: int) -> None:
    db = SessionLocal()
    try:
        row = db.get(OwnerWelcomeDelivery, delivery_id)
        if not row or row.status != "sending":
            return
        integration = db.get(OwnerWhatsAppIntegration, row.integration_id)
        if not integration or integration.status != "connected" or not integration.access_token_encrypted:
            row.status = "dead_letter"
            row.error_code = "integration_not_connected"
            row.error_message = "Owner WhatsApp integration is not connected"
            db.commit()
            return
        if not row.opt_in:
            row.status = "cancelled"
            row.error_code = "opt_in_missing"
            row.error_message = "Welcome delivery requires an explicit opt-in"
            db.commit()
            return
        try:
            token = decrypt_secret(integration.access_token_encrypted)
            parameters = [row.recipient_name] if row.recipient_name else None
            data = await OwnerMetaCloudClient(token).send_template(
                integration.phone_number_id,
                row.recipient_phone,
                row.template_name,
                row.template_language,
                parameters,
            )
            messages = data.get("messages") if isinstance(data, dict) else None
            row.provider_message_id = str(messages[0].get("id")) if messages and isinstance(messages[0], dict) and messages[0].get("id") else None
            row.status = "sent"
            row.error_code = None
            row.error_message = None
            row.delivered_at = _now()
            db.commit()
        except OwnerMetaError as exc:
            if exc.retryable and row.attempt_count < MAX_ATTEMPTS:
                row.status = "pending"
                row.next_attempt_at = _now() + timedelta(seconds=min(3600, 4 ** row.attempt_count))
            else:
                row.status = "dead_letter" if exc.retryable else "failed"
            row.error_code = exc.code[:80]
            row.error_message = str(exc)[:512]
            db.commit()
        except Exception as exc:  # noqa: BLE001 — worker must contain unexpected failures
            logger.exception("owner_welcome_delivery_failed", extra={"delivery_id": delivery_id})
            if row.attempt_count < MAX_ATTEMPTS:
                row.status = "pending"
                row.next_attempt_at = _now() + timedelta(seconds=min(3600, 4 ** row.attempt_count))
            else:
                row.status = "dead_letter"
            row.error_code = "worker_internal_error"
            row.error_message = "Unexpected worker failure"
            db.commit()
    finally:
        db.close()


async def run() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    heartbeat = Path(os.getenv("OWNER_WELCOME_WORKER_HEARTBEAT", "/tmp/mago_owner_welcome_worker_heartbeat"))
    while True:
        heartbeat.touch()
        row = claim_one()
        if row:
            await deliver_one(row.id)
        else:
            await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run())
