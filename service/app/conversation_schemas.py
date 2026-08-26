from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


ChannelName = Literal["whatsapp", "sms", "rcs", "mms", "email", "voice", "chat", "sip"]
IdentityType = Literal["phone", "whatsapp", "email", "external_id", "sip_uri"]
ConversationStatus = Literal["active", "waiting", "handoff", "closed", "archived"]
EventType = Literal["message", "status", "note", "system", "handoff", "insight"]
EventDirection = Literal["inbound", "outbound", "internal", "system"]


class ConversationCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    channel: ChannelName
    identity: str = Field(min_length=1, max_length=255)
    identity_type: IdentityType
    display_name: str | None = Field(default=None, max_length=180)
    external_ref: str | None = Field(default=None, max_length=180)
    subject: str | None = Field(default=None, max_length=255)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("identity")
    @classmethod
    def normalize_identity(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("identity cannot be blank")
        return value


class ConversationEventCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: EventType
    direction: EventDirection = "internal"
    channel: ChannelName | None = None
    content: dict[str, Any] = Field(default_factory=dict)
    provider_event_id: str | None = Field(default=None, max_length=180)
    actor_type: Literal["customer", "human_agent", "ai_agent", "system", "provider"] = "system"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationStatusUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ConversationStatus


class ConversationView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    channel: str
    customer_profile_id: str
    subject: str | None
    external_ref: str | None
    last_event_at: Any | None
    created_at: Any
    updated_at: Any


class ConversationEventView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    direction: str
    channel: str | None
    actor_type: str
    content: dict[str, Any]
    provider_event_id: str | None
    created_at: Any
