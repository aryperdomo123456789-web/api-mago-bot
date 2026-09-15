from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator


class ProviderIntegrationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: int = Field(gt=0)
    project_id: int = Field(gt=0)
    provider_type: Literal["meta_cloud", "evolution"]
    display_name: str = Field(min_length=2, max_length=180)
    external_resource_id: str = Field(min_length=1, max_length=180)
    access_token: SecretStr | None = None
    instance_token: SecretStr | None = None
    api_version: str | None = Field(default=None, max_length=32)
    base_url: str | None = Field(default=None, max_length=255)

    @field_validator("display_name", "external_resource_id")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value cannot be empty")
        return value

    def credential_payload(self) -> dict[str, str]:
        values: dict[str, str] = {}
        if self.access_token:
            values["access_token"] = self.access_token.get_secret_value()
        if self.instance_token:
            values["instance_token"] = self.instance_token.get_secret_value()
        if self.api_version:
            values["api_version"] = self.api_version.strip()
        if self.base_url:
            values["base_url"] = self.base_url.strip()
        return values


class ProviderIntegrationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    project_id: str
    provider_type: str
    display_name: str
    external_resource_id: str
    status: str
    is_primary: bool
    credentials_configured: bool
    last_tested_at: object | None = None
    last_error: str | None = None
    created_at: object | None = None
    updated_at: object | None = None
