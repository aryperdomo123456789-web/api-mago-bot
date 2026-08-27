import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .operation_schemas import OperationResponse
from .platform_models import IdempotencyRecord, Operation

TERMINAL_OPERATION_STATES = {"succeeded", "failed", "cancelled", "aborted", "expired"}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical_request_hash(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def require_idempotency_key(value: str | None) -> str:
    normalized = (value or "").strip()
    if len(normalized) < 16 or len(normalized) > 160:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "idempotency_key_required",
                "message": "X-Idempotency-Key é obrigatório e deve ter entre 16 e 160 caracteres.",
                "reason": "IDEMPOTENCY_KEY_REQUIRED",
                "retryable": False,
            },
        )
    return normalized


def operation_name(row: Operation) -> str:
    return f"operations/{row.operation_uuid}"


def operation_view(
    row: Operation,
    *,
    organization_uuid: Any | None = None,
    project_uuid: Any | None = None,
) -> dict[str, Any]:
    metadata = dict(row.metadata_json or {})
    metadata.setdefault("state", row.status)
    metadata.setdefault("attempt", int(row.attempt_count or 0))
    metadata.setdefault("start_time", row.start_time)
    metadata.setdefault("last_update_time", row.update_time)
    metadata.setdefault("retryable", bool((row.error_json or {}).get("retryable", False)))
    return {
        "name": operation_name(row),
        "id": row.operation_uuid,
        "organization_id": organization_uuid or row.tenant_id,
        "project_id": project_uuid or row.project_id,
        "kind": row.kind,
        "status": row.status,
        "done": row.status in TERMINAL_OPERATION_STATES,
        "metadata": metadata,
        "response": row.response_json,
        "error": row.error_json,
        "attempt_count": int(row.attempt_count or 0),
        "created_time": row.created_time,
        "start_time": row.start_time,
        "update_time": row.update_time,
        "complete_time": row.complete_time,
        "expire_time": row.expire_time,
    }


def find_operation(
    db: Session,
    *,
    tenant_id: int,
    project_id: int,
    kind: str,
    idempotency_key: str,
) -> Operation | None:
    return db.scalar(
        select(Operation).where(
            Operation.tenant_id == tenant_id,
            Operation.project_id == project_id,
            Operation.kind == kind,
            Operation.idempotency_key == idempotency_key,
        )
    )


def create_or_replay_operation(
    db: Session,
    *,
    tenant_id: int,
    project_id: int,
    kind: str,
    idempotency_key: str,
    request_hash: str,
    api_key_id: int | None = None,
    actor_user_id: int | None = None,
    metadata: dict[str, Any] | None = None,
    ttl_days: int = 30,
) -> tuple[Operation, bool]:
    existing = find_operation(
        db,
        tenant_id=tenant_id,
        project_id=project_id,
        kind=kind,
        idempotency_key=idempotency_key,
    )
    if existing:
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_key_reused",
                    "message": "A chave de idempotência foi reutilizada com outro payload.",
                    "reason": "IDEMPOTENCY_KEY_REUSED",
                    "retryable": False,
                },
            )
        return existing, True

    now = utcnow()
    row = Operation(
        tenant_id=tenant_id,
        project_id=project_id,
        api_key_id=api_key_id,
        actor_user_id=actor_user_id,
        kind=kind,
        status="queued",
        idempotency_key=idempotency_key,
        request_hash=request_hash,
        metadata_json=metadata or {},
        attempt_count=0,
        created_time=now,
        update_time=now,
        expire_time=now + timedelta(days=max(1, min(ttl_days, 90))),
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        existing = find_operation(
            db,
            tenant_id=tenant_id,
            project_id=project_id,
            kind=kind,
            idempotency_key=idempotency_key,
        )
        if not existing:
            raise
        if existing.request_hash != request_hash:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "idempotency_key_reused",
                    "message": "A chave de idempotência foi reutilizada com outro payload.",
                    "reason": "IDEMPOTENCY_KEY_REUSED",
                    "retryable": False,
                },
            )
        return existing, True
    return row, False


def mark_operation_running(row: Operation, *, metadata: dict[str, Any] | None = None) -> None:
    now = utcnow()
    row.status = "running"
    row.start_time = row.start_time or now
    row.update_time = now
    row.heartbeat_time = now
    row.attempt_count = int(row.attempt_count or 0) + 1
    if metadata:
        row.metadata_json = {**(row.metadata_json or {}), **metadata}


def mark_operation_succeeded(row: Operation, response: dict[str, Any] | list[Any] | str | None, *, metadata: dict[str, Any] | None = None) -> None:
    now = utcnow()
    row.status = "succeeded"
    row.response_json = response
    row.error_json = None
    row.complete_time = now
    row.update_time = now
    row.heartbeat_time = now
    if metadata:
        row.metadata_json = {**(row.metadata_json or {}), **metadata}


def mark_operation_failed(row: Operation, error: dict[str, Any], *, metadata: dict[str, Any] | None = None, terminal: bool = True) -> None:
    now = utcnow()
    row.status = "failed" if terminal else "running"
    row.response_json = None
    row.error_json = error
    row.complete_time = now if terminal else None
    row.update_time = now
    row.heartbeat_time = now
    if metadata:
        row.metadata_json = {**(row.metadata_json or {}), **metadata}


def record_legacy_idempotency(
    db: Session,
    *,
    tenant_id: int,
    project_id: int | None,
    user_id: int | None,
    idempotency_key: str,
    endpoint: str,
    request_hash: str,
    response_json: dict[str, Any],
    ttl_days: int = 365,
) -> IdempotencyRecord:
    record = IdempotencyRecord(
        tenant_id=tenant_id,
        project_id=project_id,
        user_id=user_id,
        idempotency_key=idempotency_key,
        endpoint=endpoint,
        request_hash=request_hash,
        response_json=response_json,
        expires_at=utcnow() + timedelta(days=max(1, min(ttl_days, 730))),
    )
    db.add(record)
    return record


def as_operation_response(
    row: Operation,
    *,
    organization_uuid: Any | None = None,
    project_uuid: Any | None = None,
) -> OperationResponse:
    return OperationResponse.model_validate(
        operation_view(row, organization_uuid=organization_uuid, project_uuid=project_uuid)
    )
