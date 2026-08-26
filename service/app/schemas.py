from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "pd-api"


class PanelLoginRequest(BaseModel):
    email: str
    password: str


class PanelUserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=180)
    role: str = Field(default="subscriber", max_length=24)
    notes: str | None = None


class PanelUserUpdate(BaseModel):
    email: str | None = Field(default=None, min_length=5, max_length=255)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    full_name: str | None = Field(default=None, min_length=2, max_length=180)
    role: str | None = Field(default=None, max_length=24)
    is_active: bool | None = None
    notes: str | None = None


class PanelUserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    notes: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OwnerProfileUpdate(BaseModel):
    display_name: str = Field(min_length=2, max_length=180)
    company_name: str | None = Field(default=None, max_length=180)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    bio: str | None = None


class OwnerProfileResponse(BaseModel):
    display_name: str
    company_name: str | None = None
    email: str | None = None
    phone: str | None = None
    bio: str | None = None
    updated_at: datetime | None = None


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(min_length=2, max_length=180)
    domain: str | None = Field(default=None, max_length=255)
    description: str | None = None


class LicenseCreate(BaseModel):
    label: str = Field(min_length=2, max_length=180)
    project_slug: str = Field(min_length=2, max_length=180)
    scopes: list[str] = Field(default_factory=list)
    expires_at: datetime | None = None
    created_by: str | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LicenseValidateRequest(BaseModel):
    token: str
    scope: str | None = None
    project_slug: str | None = None
    domain: str | None = None


class LicenseResponse(BaseModel):
    id: int
    uuid: UUID
    label: str
    project_slug: str
    scopes: list[str]
    status: str
    expires_at: datetime | None = None
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None


class LicenseValidationResponse(BaseModel):
    valid: bool
    status: str
    reason: str | None = None
    license: LicenseResponse | None = None


class PlanCatalogResponse(BaseModel):
    slug: str
    name: str
    subtitle: str | None = None
    description: str | None = None
    price_cents: int | None = None
    currency: str = "BRL"
    trial_days: int = 0
    billing_period_days: int = 30
    max_instances: int | None = None
    max_projects: int | None = None
    max_keys: int | None = None
    is_partner: bool = False
    is_active: bool = True
    cta_label: str | None = None
    features: list[str] = Field(default_factory=list)
    sort_order: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TrialCreateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=180)
    email: str = Field(min_length=5, max_length=255)
    company_name: str | None = Field(default=None, max_length=180)
    phone: str | None = Field(default=None, max_length=40)
    website: str | None = Field(default=None, max_length=255)
    plan_slug: str = Field(default="start", max_length=64)
    notes: str | None = None


class TrialActivationRequest(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    activation_code: str = Field(min_length=8, max_length=80)


class CustomerAccountResponse(BaseModel):
    id: int
    account_uuid: UUID
    email: str
    full_name: str
    company_name: str | None = None
    phone: str | None = None
    website: str | None = None
    plan_slug: str
    status: str
    activation_code_hint: str | None = None
    trial_ends_at: datetime | None = None
    activated_at: datetime | None = None
    expires_at: datetime | None = None
    license_project_id: int | None = None
    license_id: int | None = None
    notes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PartnerApplicationCreate(BaseModel):
    company_name: str = Field(min_length=2, max_length=180)
    full_name: str = Field(min_length=2, max_length=180)
    email: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=40)
    website: str | None = Field(default=None, max_length=255)
    monthly_volume: str | None = Field(default=None, max_length=80)
    message: str | None = None


class PartnerApplicationResponse(BaseModel):
    id: int
    company_name: str
    full_name: str
    email: str
    phone: str | None = None
    website: str | None = None
    monthly_volume: str | None = None
    message: str | None = None
    status: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
