from __future__ import annotations

import base64
import io

import qrcode
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..models import PanelUser
from ..platform_auth import get_current_platform_user
from ..platform_crypto import decrypt_secret, encrypt_secret
from ..platform_mfa import (
    consume_recovery_code,
    generate_recovery_codes,
    generate_totp_secret,
    hash_recovery_codes,
    otpauth_uri,
    verify_totp,
)
from ..platform_schemas import MfaCodeRequest

router = APIRouter(prefix="/v1/platform/auth/mfa", tags=["mfa"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _user(request: Request, db: Session = Depends(get_db)) -> PanelUser:
    return get_current_platform_user(request, db)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _qr_data_url(value: str) -> str:
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=8, border=4)
    qr.add_data(value)
    qr.make(fit=True)
    image = qr.make_image(fill_color="#06111d", back_color="white").convert("RGB")
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    encoded = base64.b64encode(output.getvalue()).decode("ascii")
    return "data:image/png;base64," + encoded


def _validate_factor(user: PanelUser, code: str) -> tuple[bool, int | None, list[str] | None]:
    if not user.mfa_secret_encrypted:
        return False, None, None
    try:
        secret = decrypt_secret(user.mfa_secret_encrypted)
    except RuntimeError:
        return False, None, None
    valid, counter = verify_totp(secret, code)
    if valid:
        if counter is not None and user.mfa_last_used_counter == counter:
            return False, None, None
        return True, counter, None
    recovery = list(user.mfa_recovery_hashes or [])
    consumed, remaining = consume_recovery_code(code, recovery)
    return consumed, None, remaining if consumed else None


@router.post("/enroll")
def enroll(request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="mfa already enabled")
    secret = generate_totp_secret()
    recovery_codes = generate_recovery_codes()
    user.mfa_secret_encrypted = encrypt_secret(secret)
    user.mfa_recovery_hashes = hash_recovery_codes(recovery_codes)
    user.mfa_last_used_counter = None
    user.mfa_enrolled_at = None
    db.commit()
    uri = otpauth_uri(secret, user.email)
    return {
        "ok": True,
        "status": "pending_confirmation",
        "otpauth_uri": uri,
        "qr_data_url": _qr_data_url(uri),
        "recovery_codes": recovery_codes,
        "warning": "QR, URI and recovery codes are shown once; store recovery codes in an approved password manager",
    }


@router.post("/confirm")
def confirm(payload: MfaCodeRequest, request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    if user.mfa_enabled:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="mfa already enabled")
    if not user.mfa_secret_encrypted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mfa enrollment not started")
    try:
        secret = decrypt_secret(user.mfa_secret_encrypted)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="mfa secret unavailable") from exc
    valid, counter = verify_totp(secret, payload.mfa_code)
    if not valid or counter is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid mfa code")
    user.mfa_enabled = True
    user.mfa_enrolled_at = _now()
    user.mfa_last_used_counter = counter
    db.commit()
    return {"ok": True, "enabled": True, "recovery_codes_remaining": len(user.mfa_recovery_hashes or [])}


@router.get("/status")
def status_view(request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    return {
        "enabled": bool(user.mfa_enabled),
        "enrolled_at": user.mfa_enrolled_at,
        "recovery_codes_remaining": len(user.mfa_recovery_hashes or []),
    }


@router.post("/disable")
def disable(payload: MfaCodeRequest, request: Request, db: Session = Depends(get_db)):
    user = _user(request, db)
    if not user.mfa_enabled:
        return {"ok": True, "enabled": False}
    valid, counter, remaining = _validate_factor(user, payload.mfa_code)
    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="valid mfa code required")
    user.mfa_enabled = False
    user.mfa_secret_encrypted = None
    user.mfa_recovery_hashes = remaining if remaining is not None else list(user.mfa_recovery_hashes or [])
    user.mfa_last_used_counter = counter
    user.mfa_enrolled_at = None
    db.commit()
    return {"ok": True, "enabled": False}
