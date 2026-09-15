from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OwnerProfileAdminUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: str = Field(min_length=1, max_length=180)
    company_name: str | None = Field(default=None, max_length=180)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    bio: str | None = Field(default=None, max_length=4000)


class AdminUserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str = Field(min_length=3, max_length=255)
    full_name: str = Field(min_length=1, max_length=180)
    password: str = Field(min_length=12, max_length=256)
    phone: str | None = Field(default=None, max_length=40)
    role: Literal["customer_common"] = "customer_common"
    notes: str | None = Field(default=None, max_length=4000)


class AdminUserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str | None = Field(default=None, min_length=3, max_length=255)
    full_name: str | None = Field(default=None, min_length=1, max_length=180)
    password: str | None = Field(default=None, min_length=12, max_length=256)
    phone: str | None = Field(default=None, max_length=40)
    role: str | None = Field(default=None, max_length=40)
    is_active: bool | None = None
    notes: str | None = Field(default=None, max_length=4000)


class AdminProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=180)
    slug: str = Field(min_length=2, max_length=180, pattern=r"^[a-z0-9][a-z0-9-]*$")
    domain: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)


class AdminProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=180)
    domain: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    is_active: bool | None = None


class OwnerTenantProjectCreate(BaseModel):
    """Create a customer boundary and its first project in one audited owner action."""

    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=2, max_length=180)
    tenant_slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    billing_email: str | None = Field(default=None, max_length=255)
    plan_slug: str = Field(default="start", min_length=2, max_length=64, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    project_name: str = Field(min_length=2, max_length=180)
    project_slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    provider_type: Literal["evolution", "meta_cloud"] = "evolution"
    project_description: str | None = Field(default=None, max_length=4000)
    create_default_queue: bool = True
    queue_name: str = Field(default="Atendimento geral", min_length=2, max_length=120)


class AdminLicenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=180)
    project_slug: str = Field(min_length=2, max_length=180)
    expires_at: datetime | None = None
    scopes: list[str] = Field(default_factory=list, max_length=32)
    created_by: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, max_length=4000)
    metadata: dict = Field(default_factory=dict)

    @field_validator("scopes")
    @classmethod
    def validate_scopes(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values if value and value.strip()]
        if any(len(value) > 80 for value in cleaned):
            raise ValueError("scope too long")
        return cleaned


class AdminPlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=120)
    subtitle: str | None = Field(default=None, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    price_cents: int | None = Field(default=None, ge=0, le=10_000_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    trial_days: int | None = Field(default=None, ge=0, le=3650)
    billing_period_days: int | None = Field(default=None, ge=1, le=3650)
    max_instances: int | None = Field(default=None, ge=0, le=10_000_000)
    max_projects: int | None = Field(default=None, ge=0, le=10_000_000)
    max_keys: int | None = Field(default=None, ge=0, le=10_000_000)
    is_partner: bool | None = None
    is_active: bool | None = None
    cta_label: str | None = Field(default=None, max_length=120)
    features: list[str] | None = Field(default=None, max_length=100)
    sort_order: int | None = Field(default=None, ge=-1_000_000, le=1_000_000)


class AdminCustomerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["trialing", "active", "suspended", "expired", "cancelled"] | None = None
    plan_slug: str | None = Field(default=None, min_length=1, max_length=64)
    notes: str | None = Field(default=None, max_length=4000)


class AdminPartnerUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["pending", "approved", "rejected", "contacted"]
    reason: str | None = Field(default=None, max_length=1000)


class AdminLicenseValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=10, max_length=512)
    scope: str | None = Field(default=None, max_length=80)
    project_slug: str | None = Field(default=None, max_length=180)
    domain: str | None = Field(default=None, max_length=255)
