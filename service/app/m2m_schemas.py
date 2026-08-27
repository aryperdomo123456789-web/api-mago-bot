from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator

from .platform_webhook_events import CANONICAL_DOWNSTREAM_EVENTS


class M2MChannelCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=3, max_length=120)
    provider: Literal["evolution"] = "evolution"
    provider_flavor: Literal["evolution_api", "evolution_go"] = "evolution_api"
    events: list[str] = Field(default_factory=lambda: ["message.inbound", "message.status", "connection.updated", "qrcode.updated"], max_length=40)
    pairing_phone: str | None = Field(default=None, min_length=8, max_length=24)

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        normalized = " ".join(value.strip().split())
        if len(normalized) < 3:
            raise ValueError("display_name must contain at least 3 characters")
        return normalized

    @field_validator("events")
    @classmethod
    def validate_events(cls, values: list[str]) -> list[str]:
        normalized = sorted({str(value).strip().lower() for value in values if str(value).strip()})
        allowed = set(CANONICAL_DOWNSTREAM_EVENTS) | {"all"}
        if any(value not in allowed for value in normalized):
            raise ValueError("unsupported downstream event")
        return normalized or ["all"]


class M2MChannelView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    organization_id: UUID
    project_id: UUID
    display_name: str
    provider: str
    provider_flavor: str
    provider_instance_id: str
    status: str
    phone_number: str | None = None
    last_seen_at: datetime | None = None
    last_error: dict | None = None
    capabilities: list[str]
    webhook_configured: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class M2MChannelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    channel: M2MChannelView
    provider: dict = Field(default_factory=dict)
    operation: dict | None = None


class M2MChannelListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[M2MChannelView]
    next_page_token: str | None = None


class M2MChannelQrResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    channel_id: UUID
    expires_at: datetime | None = None
    qrcode: str | None = None
    operation: dict | None = None


class M2MPairingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=8, max_length=24)


class M2MPairingResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    channel: M2MChannelView
    pairing_code: str | None = None
    provider: dict = Field(default_factory=dict)
    operation: dict | None = None


class M2MChannelStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: M2MChannelView
    status: dict = Field(default_factory=dict)


class M2MWebhookCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    endpoint_url: AnyHttpUrl
    events: list[str] = Field(default_factory=lambda: ["message.inbound", "message.status", "connection.updated", "qrcode.updated"], max_length=40)

    @field_validator("events")
    @classmethod
    def validate_events(cls, values: list[str]) -> list[str]:
        normalized = sorted({str(value).strip().lower() for value in values if str(value).strip()})
        allowed = set(CANONICAL_DOWNSTREAM_EVENTS) | {"all"}
        if any(value not in allowed for value in normalized):
            raise ValueError("unsupported downstream event")
        return normalized or ["all"]


class M2MWebhookView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: UUID
    project_id: UUID
    endpoint_url: str
    events: list[str]
    status: str
    failure_count: int
    last_delivery_at: datetime | None = None
    created_at: datetime | None = None


class M2MWebhookResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool = True
    webhook: M2MWebhookView
    secret: str | None = None
    secret_warning: str | None = None
    operation: dict | None = None


class M2MWebhookListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[M2MWebhookView]
    next_page_token: str | None = None
