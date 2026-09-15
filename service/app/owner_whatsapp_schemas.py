from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator


class OwnerWhatsAppConfigRequest(BaseModel):
    phone_number_id: str = Field(min_length=8, max_length=32)
    waba_id: str | None = Field(default=None, max_length=32)
    access_token: str | None = Field(default=None, min_length=20, max_length=4096)
    app_secret: str | None = Field(default=None, min_length=16, max_length=512)
    webhook_verify_token: str | None = Field(default=None, min_length=16, max_length=512)
    welcome_enabled: bool = False
    welcome_template_name: str | None = Field(default=None, max_length=512)
    welcome_template_language: str = Field(default="pt_BR", min_length=2, max_length=32)
    opt_in_required: bool = True

    @field_validator("phone_number_id", "waba_id")
    @classmethod
    def validate_numeric_id(cls, value: str | None) -> str | None:
        if value is not None and (not value.isdigit() or not 8 <= len(value) <= 32):
            raise ValueError("WhatsApp IDs must contain only digits")
        return value

    @model_validator(mode="after")
    def validate_welcome_configuration(self):
        if self.welcome_enabled and not self.welcome_template_name:
            raise ValueError("an approved welcome template is required when welcome is enabled")
        if not self.opt_in_required:
            raise ValueError("opt-in cannot be disabled")
        return self

    @field_validator("welcome_template_name")
    @classmethod
    def validate_template_name(cls, value: str | None) -> str | None:
        if value is not None:
            normalized = value.strip()
            if not normalized or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for char in normalized):
                raise ValueError("template name may contain only letters, digits and underscore")
            return normalized
        return value


class OwnerWhatsAppStatusResponse(BaseModel):
    configured: bool
    status: str
    provider_type: str
    phone_number_id: str | None = None
    waba_id: str | None = None
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    welcome_enabled: bool = False
    welcome_template_name: str | None = None
    welcome_template_language: str | None = None
    opt_in_required: bool = True
    access_token_configured: bool = False
    app_secret_configured: bool = False
    webhook_verify_token_configured: bool = False
    last_checked_at: datetime | None = None
    last_error: str | None = None
    updated_at: datetime | None = None


class OwnerWhatsAppTestResponse(BaseModel):
    ok: bool
    status: str
    phone_number_id: str
    display_phone_number: str | None = None
    verified_name: str | None = None
    quality_rating: str | None = None
    request_id: str | None = None


class OwnerWelcomePreviewRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=40)
    opt_in: bool = False
    opt_in_source: str | None = Field(default=None, max_length=180)
    name: str | None = Field(default=None, max_length=180)
