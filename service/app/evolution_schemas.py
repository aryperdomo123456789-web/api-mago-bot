from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


_INSTANCE_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{1,118}$")
_ALLOWED_FLAVORS = {"evolution_api", "evolution_go"}
_ALLOWED_EVENTS = {
    "ALL",
    "MESSAGE",
    "SEND_MESSAGE",
    "CONNECTION",
    "QRCODE",
    "READ_RECEIPT",
    "HISTORY_SYNC",
    "PRESENCE",
    "CHAT_PRESENCE",
    "CALL",
    "LABEL",
    "CONTACT",
    "GROUP",
    "NEWSLETTER",
}


class EvolutionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EvolutionInstanceCreateRequest(EvolutionRequest):
    tenant_id: int = Field(gt=0)
    project_id: int = Field(gt=0)
    instance_name: str = Field(min_length=2, max_length=120)
    provider_flavor: str = Field(default="evolution_api", min_length=8, max_length=32)
    webhook_url: str | None = Field(default=None, max_length=2048)
    events: list[str] = Field(default_factory=lambda: ["ALL"], max_length=20)
    pairing_phone: str | None = Field(default=None, min_length=10, max_length=20)

    @field_validator("instance_name")
    @classmethod
    def validate_instance_name(cls, value: str) -> str:
        if not _INSTANCE_RE.fullmatch(value):
            raise ValueError("instance_name must use letters, numbers, hyphen or underscore")
        return value

    @field_validator("provider_flavor")
    @classmethod
    def validate_provider_flavor(cls, value: str) -> str:
        normalized = value.lower()
        if normalized not in _ALLOWED_FLAVORS:
            raise ValueError("unsupported Evolution provider flavor")
        return normalized

    @field_validator("webhook_url")
    @classmethod
    def validate_webhook_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("https://"):
            raise ValueError("Evolution webhook URL must use HTTPS")
        return value

    @field_validator("events")
    @classmethod
    def validate_events(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().upper() for value in values if value.strip()})
        if not normalized:
            return ["ALL"]
        if any(value not in _ALLOWED_EVENTS for value in normalized):
            raise ValueError("unsupported Evolution webhook event")
        return normalized


class EvolutionPairRequest(EvolutionRequest):
    phone: str = Field(min_length=10, max_length=20)


class EvolutionInstanceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    uuid: UUID
    tenant_id: int
    project_id: int
    resource_id: int | None
    instance_name: str
    provider_flavor: str
    status: str
    jid: str | None = None
    display_phone_number: str | None = None
    webhook_url: str | None = None
    events: list[str]
    capabilities: list[str] = Field(default_factory=list)
    last_status_check_at: datetime | None = None
    last_connected_at: datetime | None = None
    last_sync_at: datetime | None = None
    qr_expires_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EvolutionActionResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool = True
    instance: EvolutionInstanceResponse
    provider: dict[str, Any] = Field(default_factory=dict)
