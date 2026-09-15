from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..operation_schemas import OperationListResponse, OperationResponse
from ..platform_errors import error_body
from ..platform_limits import get_service_api_key, require_key_scope
from ..platform_models import Operation, PlatformProject, ServiceApiKey, Tenant
from ..platform_operations import TERMINAL_OPERATION_STATES, operation_view

router = APIRouter(prefix="/v1/operations", tags=["operations"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_uuid(value: str, field: str) -> UUID:
    try:
        return UUID(value.removeprefix("operations/"))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "invalid_uuid",
                "message": f"{field} deve ser um UUID válido.",
                "reason": "INVALID_ARGUMENT",
                "details": [{"type": "field_violation", "field": field}],
            },
        ) from exc


def _project_for_key(db: Session, project_value: str, api_key: ServiceApiKey) -> PlatformProject:
    project_uuid = _parse_uuid(project_value, "project_id")
    project = db.scalar(
        select(PlatformProject).where(
            PlatformProject.project_uuid == project_uuid,
            PlatformProject.tenant_id == api_key.tenant_id,
            PlatformProject.status == "active",
        )
    )
    if not project or (api_key.project_id is not None and api_key.project_id != project.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="project not found")
    tenant = db.get(Tenant, api_key.tenant_id)
    if not tenant or tenant.status != "active":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="tenant inactive")
    return project


def _row_for_key(db: Session, operation_value: str, project: PlatformProject, api_key: ServiceApiKey) -> Operation:
    operation_uuid = _parse_uuid(operation_value, "operation_id")
    row = db.scalar(
        select(Operation).where(
            Operation.operation_uuid == operation_uuid,
            Operation.tenant_id == api_key.tenant_id,
            Operation.project_id == project.id,
        )
    )
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="operation not found")
    if row.status not in TERMINAL_OPERATION_STATES and row.expire_time <= _now():
        row.status = "expired"
        row.complete_time = _now()
        row.update_time = _now()
        row.metadata_json = {**(row.metadata_json or {}), "state": "expired"}
        db.commit()
        db.refresh(row)
    return row


def _public_view(db: Session, row: Operation) -> dict:
    project = db.get(PlatformProject, row.project_id)
    tenant = db.get(Tenant, row.tenant_id)
    return operation_view(
        row,
        organization_uuid=tenant.tenant_uuid if tenant else None,
        project_uuid=project.project_uuid if project else None,
    )


@router.get("", response_model=OperationListResponse)
def list_operations(
    request: Request,
    project_id: str,
    operation_status: str | None = Query(default=None, alias="status", max_length=32),
    kind: str | None = Query(default=None, max_length=80),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "operations:read")
    project = _project_for_key(db, project_id, api_key)
    query = select(Operation).where(
        Operation.tenant_id == api_key.tenant_id,
        Operation.project_id == project.id,
    )
    if operation_status:
        query = query.where(Operation.status == operation_status)
    if kind:
        query = query.where(Operation.kind == kind)
    rows = db.scalars(query.order_by(desc(Operation.id)).limit(page_size)).all()
    return {"items": [_public_view(db, row) for row in rows], "next_page_token": None}


@router.get("/{operation_id}", response_model=OperationResponse)
def get_operation(
    operation_id: str,
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "operations:read")
    project = _project_for_key(db, project_id, api_key)
    row = _row_for_key(db, operation_id, project, api_key)
    return _public_view(db, row)


@router.delete("/{operation_id}", status_code=status.HTTP_204_NO_CONTENT)
def expire_operation(
    operation_id: str,
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "operations:write")
    project = _project_for_key(db, project_id, api_key)
    row = _row_for_key(db, operation_id, project, api_key)
    if row.status not in TERMINAL_OPERATION_STATES:
        row.status = "expired"
        row.complete_time = _now()
        row.update_time = _now()
    row.metadata_json = {**(row.metadata_json or {}), "deleted": True}
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{operation_id}:cancel", response_model=OperationResponse)
def cancel_operation(
    operation_id: str,
    request: Request,
    project_id: str,
    db: Session = Depends(get_db),
    api_key: ServiceApiKey = Depends(get_service_api_key),
):
    require_key_scope(api_key, "operations:write")
    project = _project_for_key(db, project_id, api_key)
    row = _row_for_key(db, operation_id, project, api_key)
    if row.status in TERMINAL_OPERATION_STATES:
        return _public_view(db, row)
    row.status = "cancelled" if row.status == "queued" else "cancel_requested"
    row.update_time = _now()
    if row.status == "cancelled":
        row.complete_time = _now()
        row.error_json = {
            "code": "operation_cancelled",
            "message": "A operação foi cancelada antes da execução.",
            "status": "ABORTED",
            "reason": "OPERATION_CANCELLED",
            "domain": "api.mago-bot.com/operations",
            "retryable": False,
            "request_id": getattr(request.state, "request_id", None),
            "details": [],
        }
    db.commit()
    db.refresh(row)
    return _public_view(db, row)
