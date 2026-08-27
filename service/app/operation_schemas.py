from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from .platform_schemas import PlatformModel


class OperationErrorResponse(PlatformModel):
    code: str
    message: str
    status: str
    reason: str
    domain: str
    retryable: bool = False
    retry_after_seconds: int | None = Field(default=None, ge=1, le=86400)
    request_id: str | None = None
    details: list[dict[str, Any]] = Field(default_factory=list)


class OperationMetadataResponse(PlatformModel):
    state: str
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    attempt: int = Field(default=0, ge=0)
    start_time: datetime | None = None
    last_update_time: datetime | None = None
    retryable: bool = False
    provider: str | None = None
    message_id: str | None = None


class OperationResponse(PlatformModel):
    name: str
    id: UUID
    organization_id: UUID
    project_id: UUID
    kind: str
    status: str
    done: bool
    metadata: OperationMetadataResponse
    response: dict[str, Any] | list[Any] | str | None = None
    error: OperationErrorResponse | None = None
    attempt_count: int
    created_time: datetime
    start_time: datetime | None = None
    update_time: datetime
    complete_time: datetime | None = None
    expire_time: datetime


class OperationListResponse(PlatformModel):
    items: list[OperationResponse]
    next_page_token: str | None = None
