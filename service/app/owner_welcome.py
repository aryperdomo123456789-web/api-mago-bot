from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .models import PanelUser
from .platform_models import OwnerWelcomeDelivery, OwnerWhatsAppIntegration


def _now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_phone(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = "".join(char for char in value.strip() if char.isdigit() or char == "+")
    if normalized.startswith("00"):
        normalized = "+" + normalized[2:]
    if not normalized.startswith("+"):
        normalized = "+" + normalized
    digits = normalized[1:]
    if not digits.isdigit() or not 8 <= len(digits) <= 15:
        return None
    return normalized


def owner_integration(db: Session) -> OwnerWhatsAppIntegration | None:
    owner = db.scalar(select(PanelUser).where(PanelUser.role == "owner", PanelUser.is_active.is_(True)).order_by(PanelUser.id.asc()))
    if not owner:
        return None
    return db.scalar(
        select(OwnerWhatsAppIntegration).where(
            OwnerWhatsAppIntegration.owner_user_id == owner.id,
            OwnerWhatsAppIntegration.status == "connected",
            OwnerWhatsAppIntegration.welcome_enabled.is_(True),
            OwnerWhatsAppIntegration.opt_in_required.is_(True),
        )
    )


def enqueue_owner_welcome(
    db: Session,
    *,
    source_type: str,
    source_id: str,
    recipient_phone: str | None,
    recipient_name: str | None,
    opt_in: bool,
    opt_in_source: str | None,
) -> bool:
    """Queue only an explicitly opted-in signup; delivery is later and idempotent."""
    phone = normalize_phone(recipient_phone)
    if not phone or not opt_in:
        return False
    integration = owner_integration(db)
    if not integration or not integration.welcome_template_name:
        return False
    row = OwnerWelcomeDelivery(
        integration_id=integration.id,
        source_type=source_type,
        source_id=str(source_id),
        recipient_phone=phone,
        recipient_name=(recipient_name or "").strip()[:180] or None,
        opt_in=True,
        opt_in_source=(opt_in_source or "signup").strip()[:180],
        template_name=integration.welcome_template_name,
        template_language=integration.welcome_template_language,
        status="pending",
        next_attempt_at=_now(),
    )
    try:
        with db.begin_nested():
            db.add(row)
            db.flush()
    except IntegrityError:
        return False
    return True
