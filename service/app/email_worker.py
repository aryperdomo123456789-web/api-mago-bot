from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import select

from .db import SessionLocal
from . import models  # noqa: F401 — registra panel_users no metadata do worker
from .email_service import default_reply_to
from .platform_limits import QuotaExceeded
from .platform_models import EmailDelivery, EmailSenderIdentity, EmailSuppression
from .platform_rate_limit import DistributedRateLimitExceeded, enforce_distributed_limit
from .providers.resend_email import ResendEmailClient, ResendEmailError

logger = logging.getLogger("mago.email_worker")
POLL_SECONDS = max(1.0, float(os.getenv("EMAIL_WORKER_POLL_SECONDS", "2")))
MAX_ATTEMPTS = max(1, int(os.getenv("EMAIL_WORKER_MAX_ATTEMPTS", "8")))
DAILY_LIMIT = max(1, int(os.getenv("RESEND_DAILY_LIMIT", "100")))


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _retry_at(attempt_count: int) -> datetime:
    return _now() + timedelta(seconds=min(3600, 2 ** min(attempt_count, 10)))


def claim_one() -> int | None:
    db = SessionLocal()
    try:
        row = db.scalar(
            select(EmailDelivery)
            .where(
                EmailDelivery.status == "pending",
                EmailDelivery.next_attempt_at <= _now(),
            )
            .order_by(EmailDelivery.id.asc())
            .with_for_update(skip_locked=True)
        )
        if not row:
            return None
        row.status = "sending"
        row.attempt_count += 1
        db.commit()
        return row.id
    finally:
        db.close()


def _mark_failure(db, row: EmailDelivery, *, code: str, message: str, retryable: bool) -> None:
    row.error_code = code[:80]
    row.error_message = message[:512]
    if retryable and row.attempt_count < MAX_ATTEMPTS:
        row.status = "pending"
        row.next_attempt_at = _retry_at(row.attempt_count)
    else:
        row.status = "dead_letter" if retryable else "failed"


async def deliver_one(delivery_id: int) -> None:
    db = SessionLocal()
    try:
        row = db.get(EmailDelivery, delivery_id)
        if not row or row.status != "sending":
            return
        identity = db.get(EmailSenderIdentity, row.sender_identity_id) if row.sender_identity_id else None
        if not identity or identity.status != "active":
            _mark_failure(db, row, code="sender_identity_unavailable", message="Sender identity is unavailable", retryable=False)
            db.commit()
            return
        if db.scalar(select(EmailSuppression.id).where(EmailSuppression.email == row.recipient_email)):
            row.status = "suppressed"
            row.error_code = "recipient_suppressed"
            row.error_message = "Recipient is on the suppression list"
            db.commit()
            return

        client = ResendEmailClient()
        try:
            if not client.dry_run:
                enforce_distributed_limit(
                    db,
                    namespace="resend_daily",
                    subject="global",
                    limit=DAILY_LIMIT,
                    window_seconds=86400,
                )
            result = await client.send(
                from_email=identity.sender_email,
                from_name=identity.sender_name,
                to_email=row.recipient_email,
                to_name=row.recipient_name,
                reply_to=identity.reply_to or default_reply_to(),
                subject=row.subject,
                html_body=row.html_body,
                text_body=row.text_body,
                tags={"mago_message_type": row.message_type, "mago_delivery": str(row.delivery_uuid)},
            )
            row.provider_message_id = result.provider_message_id[:180]
            row.status = "sent"
            row.sent_at = _now()
            row.error_code = None
            row.error_message = None
        except DistributedRateLimitExceeded as exc:
            _mark_failure(db, row, code="resend_daily_limit", message=f"Resend daily limit reached; retry after {exc.retry_after}s", retryable=True)
        except (QuotaExceeded, ResendEmailError) as exc:
            retryable = getattr(exc, "retryable", False)
            code = getattr(exc, "code", "email_delivery_error")
            _mark_failure(db, row, code=code, message=str(exc), retryable=retryable)
        db.commit()
    except Exception:
        logger.exception("email_delivery_worker_failed", extra={"delivery_id": delivery_id})
        db.rollback()
        row = db.get(EmailDelivery, delivery_id)
        if row and row.status == "sending":
            _mark_failure(db, row, code="worker_internal_error", message="Unexpected email worker failure", retryable=True)
            db.commit()
    finally:
        db.close()


async def run_worker() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    heartbeat = Path(os.getenv("EMAIL_WORKER_HEARTBEAT", "/tmp/mago_email_worker_heartbeat"))
    while True:
        heartbeat.touch()
        delivery_id = claim_one()
        if delivery_id is not None:
            await deliver_one(delivery_id)
        else:
            await asyncio.sleep(POLL_SECONDS)


if __name__ == "__main__":
    asyncio.run(run_worker())
