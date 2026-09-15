from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..owner_whatsapp_schemas import OwnerWhatsAppConfigRequest, OwnerWhatsAppStatusResponse, OwnerWhatsAppTestResponse
from ..platform_auth import get_current_platform_user
from ..platform_crypto import decrypt_secret, encrypt_secret
from ..platform_models import OwnerWhatsAppIntegration
from ..platform_rbac import require_platform_role
from ..providers.owner_meta import OwnerMetaCloudClient, OwnerMetaError

router = APIRouter(prefix="/v1/platform/owner/whatsapp", tags=["owner-whatsapp"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owner(request: Request, db: Session) -> PanelUser:
    user = get_current_platform_user(request, db)
    return require_platform_role(user, "platform_superadmin", "platform_operator")


def _integration(db: Session, user_id: int) -> OwnerWhatsAppIntegration | None:
    return db.scalar(select(OwnerWhatsAppIntegration).where(OwnerWhatsAppIntegration.owner_user_id == user_id))


def _serialize(row: OwnerWhatsAppIntegration | None) -> dict:
    if not row:
        return OwnerWhatsAppStatusResponse(
            configured=False,
            status="not_configured",
            provider_type="meta_cloud",
            opt_in_required=True,
        ).model_dump(mode="json")
    return OwnerWhatsAppStatusResponse(
        configured=bool(row.access_token_encrypted and row.phone_number_id),
        status=row.status,
        provider_type=row.provider_type,
        phone_number_id=row.phone_number_id,
        waba_id=row.waba_id,
        display_phone_number=row.display_phone_number,
        verified_name=row.verified_name,
        quality_rating=row.quality_rating,
        welcome_enabled=row.welcome_enabled,
        welcome_template_name=row.welcome_template_name,
        welcome_template_language=row.welcome_template_language,
        opt_in_required=row.opt_in_required,
        access_token_configured=bool(row.access_token_encrypted),
        app_secret_configured=bool(row.app_secret_encrypted),
        webhook_verify_token_configured=bool(row.webhook_verify_token_encrypted),
        last_checked_at=row.last_checked_at,
        last_error=row.last_error,
        updated_at=row.updated_at,
    ).model_dump(mode="json")


@router.get("", response_model=OwnerWhatsAppStatusResponse)
def get_owner_whatsapp(request: Request, db: Session = Depends(get_db)):
    user = _owner(request, db)
    return _serialize(_integration(db, user.id))


@router.put("", response_model=OwnerWhatsAppStatusResponse)
def save_owner_whatsapp(
    payload: OwnerWhatsAppConfigRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = _owner(request, db)
    if not payload.access_token and not _integration(db, user.id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="access_token is required for first configuration")
    if payload.welcome_enabled and not payload.welcome_template_name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="an approved welcome template is required")
    if not payload.opt_in_required:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="opt-in cannot be disabled")

    row = _integration(db, user.id)
    if row is None:
        row = OwnerWhatsAppIntegration(owner_user_id=user.id, provider_type="meta_cloud", phone_number_id=payload.phone_number_id)
        db.add(row)
    row.phone_number_id = payload.phone_number_id
    row.waba_id = payload.waba_id
    if payload.access_token:
        row.access_token_encrypted = encrypt_secret(payload.access_token)
    if payload.app_secret:
        row.app_secret_encrypted = encrypt_secret(payload.app_secret)
    if payload.webhook_verify_token:
        row.webhook_verify_token_encrypted = encrypt_secret(payload.webhook_verify_token)
    row.welcome_enabled = payload.welcome_enabled
    row.welcome_template_name = payload.welcome_template_name
    row.welcome_template_language = payload.welcome_template_language
    row.opt_in_required = True
    row.status = "configured" if row.access_token_encrypted else "draft"
    row.last_error = None
    db.commit()
    db.refresh(row)
    return _serialize(row)


@router.post("/test", response_model=OwnerWhatsAppTestResponse)
async def test_owner_whatsapp(request: Request, db: Session = Depends(get_db)):
    user = _owner(request, db)
    row = _integration(db, user.id)
    if not row or not row.access_token_encrypted:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="WhatsApp integration is not configured")
    try:
        profile = await OwnerMetaCloudClient(decrypt_secret(row.access_token_encrypted)).get_phone_profile(row.phone_number_id)
    except OwnerMetaError as exc:
        row.status = "error"
        row.last_error = str(exc)[:512]
        row.last_checked_at = _now()
        db.commit()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail={"code": exc.code, "message": str(exc)}) from exc

    row.status = "connected"
    row.last_error = None
    row.last_checked_at = _now()
    row.display_phone_number = str(profile.get("display_phone_number") or "")[:40] or None
    row.verified_name = str(profile.get("verified_name") or "")[:180] or None
    row.quality_rating = str(profile.get("quality_rating") or "")[:40] or None
    db.commit()
    return OwnerWhatsAppTestResponse(
        ok=True,
        status=row.status,
        phone_number_id=row.phone_number_id,
        display_phone_number=row.display_phone_number,
        verified_name=row.verified_name,
        quality_rating=row.quality_rating,
        request_id=getattr(request.state, "request_id", None),
    )


@router.post("/disconnect", response_model=OwnerWhatsAppStatusResponse)
def disconnect_owner_whatsapp(request: Request, db: Session = Depends(get_db)):
    user = _owner(request, db)
    row = _integration(db, user.id)
    if not row:
        return _serialize(None)
    row.access_token_encrypted = None
    row.app_secret_encrypted = None
    row.webhook_verify_token_encrypted = None
    row.welcome_enabled = False
    row.status = "disconnected"
    row.last_error = None
    db.commit()
    db.refresh(row)
    return _serialize(row)
