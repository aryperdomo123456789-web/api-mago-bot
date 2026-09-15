from __future__ import annotations

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,78}[a-z0-9])?$")
ROLE_RE = re.compile(r"^[a-z_]{3,40}$")


class PlatformModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="forbid")


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()
    if not EMAIL_RE.fullmatch(normalized):
        raise ValueError("invalid email")
    return normalized


def validate_slug(value: str) -> str:
    normalized = value.strip().lower()
    if not SLUG_RE.fullmatch(normalized):
        raise ValueError("slug must contain only lowercase letters, numbers and hyphens")
    return normalized


class PlatformSignupRequest(PlatformModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=12, max_length=128)
    full_name: str = Field(min_length=2, max_length=180)
    company_name: str = Field(min_length=2, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    whatsapp_opt_in: bool = False
    whatsapp_opt_in_source: str | None = Field(default=None, max_length=180)
    tenant_slug: str | None = Field(default=None, min_length=3, max_length=80)

    _email = field_validator("email")(normalize_email)
    _slug = field_validator("tenant_slug")(lambda value: validate_slug(value) if value else value)


class PlatformLoginRequest(PlatformModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=1, max_length=128)
    mfa_code: str | None = Field(default=None, min_length=6, max_length=32)

    _email = field_validator("email")(normalize_email)


class VerifyEmailRequest(PlatformModel):
    token: str = Field(min_length=32, max_length=256)


class MfaCodeRequest(PlatformModel):
    mfa_code: str = Field(min_length=6, max_length=32)


class PasswordResetRequest(PlatformModel):
    email: str = Field(min_length=5, max_length=255)

    _email = field_validator("email")(normalize_email)


class PasswordResetConfirmRequest(PlatformModel):
    token: str = Field(min_length=32, max_length=256)
    password: str = Field(min_length=12, max_length=128)


class PlatformUserResponse(PlatformModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    email_verified: bool
    mfa_enabled: bool = False


class TenantResponse(PlatformModel):
    id: int
    uuid: UUID
    slug: str
    legal_name: str
    status: str
    plan_slug: str
    created_at: datetime | None = None


class MembershipResponse(PlatformModel):
    tenant_id: int
    role: str
    status: str


class ProjectCreateRequest(PlatformModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=80)
    provider_type: str = Field(default="meta_cloud", min_length=3, max_length=32)
    description: str | None = Field(default=None, max_length=2000)

    _slug = field_validator("slug")(validate_slug)


class ProjectResponse(PlatformModel):
    id: int
    uuid: UUID
    tenant_id: int
    name: str
    slug: str
    status: str
    provider_type: str | None = None
    description: str | None = None
    created_at: datetime | None = None


class ResourceCreateRequest(PlatformModel):
    display_name: str = Field(min_length=2, max_length=180)
    provider_type: str = Field(min_length=3, max_length=32)
    provider_resource_id: str = Field(min_length=2, max_length=180)


class ResourceResponse(PlatformModel):
    id: int
    uuid: UUID
    tenant_id: int
    project_id: int
    provider_type: str
    provider_resource_id: str | None = None
    status: str
    display_name: str
    created_at: datetime | None = None


class ApiKeyCreateRequest(PlatformModel):
    project_id: int
    scopes: list[str] = Field(default_factory=list, max_length=12)
    expires_at: datetime | None = None

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, values: list[str]) -> list[str]:
        normalized = sorted({value.strip().lower() for value in values if value.strip()})
        if any(len(value) > 80 or not ROLE_RE.fullmatch(value.replace(":", "_")) for value in normalized):
            raise ValueError("invalid scope")
        return normalized


class ApiKeyResponse(PlatformModel):
    id: int
    uuid: UUID
    tenant_id: int
    project_id: int | None = None
    prefix: str
    scopes: list[str]
    status: str
    expires_at: datetime | None = None
    created_at: datetime | None = None
    token: str | None = None


class MessageResponse(PlatformModel):
    id: UUID
    status: str
    provider: str
    provider_message_id: str | None = None
    created_at: datetime | None = None
    error_code: str | None = None


class MessageSendRequest(PlatformModel):
    to: str = Field(min_length=6, max_length=32)
    type: str = Field(default="text", min_length=3, max_length=32)
    conversation_id: UUID | None = None
    text: dict[str, Any] | None = None
    template: dict[str, Any] | None = None
    media: dict[str, Any] | None = None


class WebhookSubscriptionCreateRequest(PlatformModel):
    endpoint_url: str = Field(min_length=16, max_length=2048)
    events: list[str] = Field(default_factory=lambda: ["messages", "statuses"], max_length=40)

    @field_validator("endpoint_url")
    @classmethod
    def validate_endpoint_url(cls, value: str) -> str:
        from urllib.parse import urlparse
        parsed = urlparse(value.strip())
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("webhook endpoint must use HTTPS")
        if parsed.hostname.lower() in {"localhost", "127.0.0.1", "::1"} or parsed.hostname.endswith(".local"):
            raise ValueError("private webhook endpoint is not allowed")
        return value.strip()

    @field_validator("events")
    @classmethod
    def validate_events(cls, values: list[str]) -> list[str]:
        allowed = {"messages", "statuses", "errors", "account", "templates", "calls", "all"}
        normalized = sorted({item.strip().lower() for item in values if item.strip()})
        if any(item not in allowed for item in normalized):
            raise ValueError("unsupported webhook event")
        return normalized or ["messages", "statuses"]


class WebhookSubscriptionResponse(PlatformModel):
    id: int
    uuid: UUID
    tenant_id: int
    project_id: int
    endpoint_url: str
    events: list[str]
    status: str
    failure_count: int
    last_delivery_at: datetime | None = None
    created_at: datetime | None = None
    secret: str | None = None


class WebhookEventResponse(PlatformModel):
    accepted: bool
    event_id: str
