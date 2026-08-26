from __future__ import annotations

import uuid as uuid_lib
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class Tenant(Base):
    """A customer boundary. Every product resource must resolve to one tenant."""

    __tablename__ = "platform_tenants"
    __table_args__ = (
        Index("idx_platform_tenants_slug", "slug", unique=True),
        Index("idx_platform_tenants_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    legal_name: Mapped[str] = mapped_column(String(180), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    plan_slug: Mapped[str] = mapped_column(String(64), nullable=False, default="start", server_default="start")
    billing_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (
        UniqueConstraint("tenant_id", "user_id", name="uq_tenant_membership_tenant_user"),
        Index("idx_tenant_memberships_user", "user_id"),
        Index("idx_tenant_memberships_tenant_role", "tenant_id", "role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("panel_users.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(40), nullable=False, default="tenant_readonly", server_default="tenant_readonly")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    invited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PlatformSession(Base):
    __tablename__ = "platform_sessions"
    __table_args__ = (
        Index("idx_platform_sessions_user_active", "user_id", "revoked_at", "expires_at"),
        Index("idx_platform_sessions_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    session_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    session_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("panel_users.id", ondelete="CASCADE"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PlatformProject(Base):
    __tablename__ = "platform_projects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "slug", name="uq_platform_projects_tenant_slug"),
        Index("idx_platform_projects_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    project_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    provider_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Subscription(Base):
    __tablename__ = "platform_subscriptions"
    __table_args__ = (
        Index("idx_platform_subscriptions_tenant_status", "tenant_id", "status"),
        Index("idx_platform_subscriptions_period_end", "current_period_end"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    plan_slug: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="trialing", server_default="trialing")
    current_period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    external_customer_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    external_subscription_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ProviderResource(Base):
    __tablename__ = "provider_resources"
    __table_args__ = (
        Index("idx_provider_resources_tenant_status", "tenant_id", "status"),
        Index("idx_provider_resources_provider_id", "provider_type", "provider_resource_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    resource_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_resource_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="requested", server_default="requested")
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ServiceApiKey(Base):
    __tablename__ = "service_api_keys"
    __table_args__ = (
        Index("idx_service_api_keys_tenant_status", "tenant_id", "status"),
        Index("idx_service_api_keys_hash", "token_hash", unique=True),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    key_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("platform_projects.id", ondelete="SET NULL"), nullable=True)
    prefix: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", "endpoint", name="uq_idempotency_tenant_key_endpoint"),
        Index("idx_idempotency_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(180), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status_code: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    response_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        Index("idx_audit_events_tenant_created_at", "tenant_id", "created_at"),
        Index("idx_audit_events_actor_created_at", "actor_user_id", "created_at"),
        Index("idx_audit_events_action_created_at", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("platform_tenants.id", ondelete="SET NULL"), nullable=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    resource_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    resource_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    outcome: Mapped[str] = mapped_column(String(24), nullable=False, default="success", server_default="success")
    request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class AuthToken(Base):
    __tablename__ = "auth_tokens"
    __table_args__ = (
        Index("idx_auth_tokens_user_purpose", "user_id", "purpose", "used_at"),
        Index("idx_auth_tokens_hash", "token_hash", unique=True),
        Index("idx_auth_tokens_expires_at", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    token_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("panel_users.id", ondelete="CASCADE"), nullable=False)
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UsageCounter(Base):
    __tablename__ = "usage_counters"
    __table_args__ = (
        UniqueConstraint("tenant_id", "window_start", "metric", name="uq_usage_counter_tenant_window_metric"),
        Index("idx_usage_counters_tenant_metric", "tenant_id", "metric", "window_start"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class UsageLedgerEntry(Base):
    __tablename__ = "usage_ledger_entries"
    __table_args__ = (
        UniqueConstraint("tenant_id", "source_type", "source_id", "metric", name="uq_usage_ledger_source"),
        Index("idx_usage_ledger_tenant_created", "tenant_id", "created_at"),
        Index("idx_usage_ledger_tenant_metric_created", "tenant_id", "metric", "created_at"),
        Index("idx_usage_ledger_message", "message_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    entry_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    message_id: Mapped[int | None] = mapped_column(ForeignKey("outbound_messages.id", ondelete="SET NULL"), nullable=True)
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    units: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1, server_default="1")
    provider_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(180), nullable=False)
    cost_micros: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OutboundMessage(Base):
    __tablename__ = "outbound_messages"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_outbound_messages_tenant_idempotency"),
        Index("idx_outbound_messages_tenant_status", "tenant_id", "status", "created_at"),
        Index("idx_outbound_messages_provider_id", "provider_type", "provider_message_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    message_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[int | None] = mapped_column(ForeignKey("conversations.id", ondelete="SET NULL"), nullable=True)
    conversation: Mapped["Conversation | None"] = relationship("Conversation", foreign_keys=[conversation_id], lazy="joined")
    resource_id: Mapped[int | None] = mapped_column(ForeignKey("provider_resources.id", ondelete="SET NULL"), nullable=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(160), nullable=False)
    recipient: Mapped[str] = mapped_column(String(32), nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted", server_default="accepted")
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("provider_type", "provider_event_id", name="uq_webhook_events_provider_event"),
        Index("idx_webhook_events_status_received_at", "status", "received_at"),
        Index("idx_webhook_events_tenant_received_at", "tenant_id", "received_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("platform_tenants.id", ondelete="SET NULL"), nullable=True)
    resource_id: Mapped[int | None] = mapped_column(ForeignKey("provider_resources.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted", server_default="accepted")
    attempts: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WebhookSubscription(Base):
    __tablename__ = "webhook_subscriptions"
    __table_args__ = (
        Index("idx_webhook_subscriptions_tenant_status", "tenant_id", "status"),
        Index("idx_webhook_subscriptions_project_status", "project_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    subscription_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    endpoint_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    secret_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    events: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    failure_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    last_delivery_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"
    __table_args__ = (
        UniqueConstraint("subscription_id", "event_id", name="uq_webhook_deliveries_subscription_event"),
        Index("idx_webhook_deliveries_status_next_attempt", "status", "next_attempt_at"),
        Index("idx_webhook_deliveries_subscription_status", "subscription_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("webhook_subscriptions.id", ondelete="CASCADE"), nullable=False)
    event_id: Mapped[int] = mapped_column(ForeignKey("webhook_events.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    response_code: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    __table_args__ = (
        Index("idx_customer_profiles_tenant_status", "tenant_id", "status"),
        Index("idx_customer_profiles_tenant_external_ref", "tenant_id", "external_ref"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    profile_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CustomerIdentity(Base):
    __tablename__ = "customer_identities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "identity_type", "normalized_value", name="uq_customer_identity_tenant_type_value"),
        Index("idx_customer_identities_profile", "customer_profile_id"),
        Index("idx_customer_identities_tenant_channel", "tenant_id", "channel"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    identity_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    customer_profile_id: Mapped[int] = mapped_column(ForeignKey("customer_profiles.id", ondelete="CASCADE"), nullable=False)
    identity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(255), nullable=False)
    channel: Mapped[str] = mapped_column(String(32), nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversations_tenant_status_updated", "tenant_id", "status", "updated_at"),
        Index("idx_conversations_project_customer", "project_id", "customer_profile_id"),
        Index("idx_conversations_tenant_external_ref", "tenant_id", "external_ref"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    conversation_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    customer_profile_id: Mapped[int] = mapped_column(ForeignKey("customer_profiles.id", ondelete="RESTRICT"), nullable=False)
    primary_channel: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(180), nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    __table_args__ = (
        UniqueConstraint("conversation_id", "participant_type", "participant_ref", name="uq_conversation_participant_ref"),
        Index("idx_conversation_participants_conversation", "conversation_id"),
        Index("idx_conversation_participants_customer", "customer_profile_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    participant_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    customer_profile_id: Mapped[int | None] = mapped_column(ForeignKey("customer_profiles.id", ondelete="SET NULL"), nullable=True)
    participant_type: Mapped[str] = mapped_column(String(32), nullable=False)
    participant_ref: Mapped[str] = mapped_column(String(180), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ConversationEvent(Base):
    __tablename__ = "conversation_events"
    __table_args__ = (
        UniqueConstraint("tenant_id", "provider_type", "provider_event_id", name="uq_conversation_event_provider"),
        Index("idx_conversation_events_conversation_created", "conversation_id", "created_at"),
        Index("idx_conversation_events_tenant_type_created", "tenant_id", "event_type", "created_at"),
        Index("idx_conversation_events_customer_created", "customer_profile_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    outbound_message_id: Mapped[int | None] = mapped_column(ForeignKey("outbound_messages.id", ondelete="SET NULL"), nullable=True)
    customer_profile_id: Mapped[int | None] = mapped_column(ForeignKey("customer_profiles.id", ondelete="SET NULL"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    direction: Mapped[str] = mapped_column(String(24), nullable=False, default="system", server_default="system")
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="system", server_default="system")
    provider_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class OwnerWhatsAppIntegration(Base):
    __tablename__ = "owner_whatsapp_integrations"
    __table_args__ = (
        UniqueConstraint("owner_user_id", name="uq_owner_whatsapp_integration_owner"),
        Index("idx_owner_whatsapp_integrations_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    integration_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    owner_user_id: Mapped[int] = mapped_column(ForeignKey("panel_users.id", ondelete="CASCADE"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False, default="meta_cloud", server_default="meta_cloud")
    phone_number_id: Mapped[str] = mapped_column(String(32), nullable=False)
    waba_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    access_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    app_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_verify_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    verified_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    quality_rating: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft", server_default="draft")
    welcome_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    welcome_template_name: Mapped[str | None] = mapped_column(String(512), nullable=True)
    welcome_template_language: Mapped[str] = mapped_column(String(32), nullable=False, default="pt_BR", server_default="pt_BR")
    opt_in_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class OwnerWelcomeDelivery(Base):
    __tablename__ = "owner_welcome_deliveries"
    __table_args__ = (
        UniqueConstraint("integration_id", "source_type", "source_id", name="uq_owner_welcome_source"),
        Index("idx_owner_welcome_status_next_attempt", "status", "next_attempt_at"),
        Index("idx_owner_welcome_recipient", "recipient_phone", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    integration_id: Mapped[int] = mapped_column(ForeignKey("owner_whatsapp_integrations.id", ondelete="CASCADE"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(180), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    opt_in_source: Mapped[str | None] = mapped_column(String(180), nullable=True)
    template_name: Mapped[str] = mapped_column(String(512), nullable=False)
    template_language: Mapped[str] = mapped_column(String(32), nullable=False, default="pt_BR", server_default="pt_BR")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailSenderIdentity(Base):
    __tablename__ = "email_sender_identities"
    __table_args__ = (
        UniqueConstraint("tenant_id", "sender_email", name="uq_email_sender_identity_tenant_email"),
        Index("idx_email_sender_identities_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    sender_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=True)
    sender_email: Mapped[str] = mapped_column(String(255), nullable=False)
    sender_name: Mapped[str] = mapped_column(String(180), nullable=False, default="Mago Bot", server_default="Mago Bot")
    reply_to: Mapped[str | None] = mapped_column(String(255), nullable=True)
    purpose: Mapped[str] = mapped_column(String(40), nullable=False, default="transactional", server_default="transactional")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailDelivery(Base):
    __tablename__ = "email_deliveries"
    __table_args__ = (
        UniqueConstraint("source_type", "source_id", "message_type", name="uq_email_delivery_source"),
        Index("idx_email_deliveries_claim", "status", "next_attempt_at"),
        Index("idx_email_deliveries_recipient_created", "recipient_email", "created_at"),
        Index("idx_email_deliveries_provider_message", "provider_message_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    delivery_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int | None] = mapped_column(ForeignKey("platform_tenants.id", ondelete="SET NULL"), nullable=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    sender_identity_id: Mapped[int | None] = mapped_column(ForeignKey("email_sender_identities.id", ondelete="SET NULL"), nullable=True)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(180), nullable=False)
    message_type: Mapped[str] = mapped_column(String(48), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    recipient_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    html_body: Mapped[str] = mapped_column(Text, nullable=False)
    text_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    attempt_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    provider_message_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    provider_event_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    next_attempt_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailSuppression(Base):
    __tablename__ = "email_suppressions"
    __table_args__ = (
        Index("idx_email_suppressions_reason_created", "reason", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    reason: Mapped[str] = mapped_column(String(40), nullable=False)
    provider_event_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EmailProviderEvent(Base):
    __tablename__ = "email_provider_events"
    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_email_provider_event"),
        Index("idx_email_provider_events_email_id", "email_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(40), nullable=False, default="resend", server_default="resend")
    provider_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    email_id: Mapped[str | None] = mapped_column(String(180), nullable=True)
    recipient_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class EvolutionInstance(Base):
    __tablename__ = "evolution_instances"
    __table_args__ = (
        UniqueConstraint("project_id", "instance_name", name="uq_evolution_instances_project_name"),
        Index("idx_evolution_instances_tenant_status", "tenant_id", "status"),
        Index("idx_evolution_instances_project_status", "project_id", "status"),
        Index("idx_evolution_instances_health", "status", "last_status_check_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    instance_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    resource_id: Mapped[int | None] = mapped_column(ForeignKey("provider_resources.id", ondelete="SET NULL"), unique=True, nullable=True)
    instance_name: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_flavor: Mapped[str] = mapped_column(String(32), nullable=False, default="evolution_api", server_default="evolution_api")
    instance_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    webhook_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    subscribed_events: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="provisioning", server_default="provisioning")
    jid: Mapped[str | None] = mapped_column(String(180), nullable=True)
    display_phone_number: Mapped[str | None] = mapped_column(String(40), nullable=True)
    last_status_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_connected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(80), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class EvolutionInstanceEvent(Base):
    __tablename__ = "evolution_instance_events"
    __table_args__ = (
        UniqueConstraint("instance_id", "provider_event_id", name="uq_evolution_instance_event"),
        Index("idx_evolution_instance_events_instance_received", "instance_id", "received_at"),
        Index("idx_evolution_instance_events_type_received", "event_type", "received_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    event_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    instance_id: Mapped[int] = mapped_column(ForeignKey("evolution_instances.id", ondelete="CASCADE"), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(180), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="accepted", server_default="accepted")
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class RateLimitBucket(Base):
    __tablename__ = "rate_limit_buckets"
    __table_args__ = (
        UniqueConstraint("namespace", "subject", "window_start", name="uq_rate_limit_bucket_window"),
        Index("idx_rate_limit_bucket_lookup", "namespace", "subject", "window_start"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    subject: Mapped[str] = mapped_column(String(180), nullable=False)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ProviderCircuitState(Base):
    __tablename__ = "provider_circuit_states"
    __table_args__ = (
        UniqueConstraint("provider_type", "resource_key", name="uq_provider_circuit_resource"),
        Index("idx_provider_circuit_state", "state", "opened_until"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    resource_key: Mapped[str] = mapped_column(String(180), nullable=False)
    state: Mapped[str] = mapped_column(String(16), nullable=False, default="closed", server_default="closed")
    failure_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    opened_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ProviderIntegration(Base):
    __tablename__ = "provider_integrations"
    __table_args__ = (
        UniqueConstraint("project_id", "provider_type", "external_resource_id", name="uq_provider_integrations_project_resource"),
        Index("idx_provider_integrations_tenant_status", "tenant_id", "status"),
        Index("idx_provider_integrations_project_provider", "project_id", "provider_type", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    integration_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    external_resource_id: Mapped[str] = mapped_column(String(180), nullable=False)
    credentials_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(512), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class InboxQueue(Base):
    __tablename__ = "inbox_queues"
    __table_args__ = (
        UniqueConstraint("project_id", "slug", name="uq_inbox_queues_project_slug"),
        Index("idx_inbox_queues_tenant_status", "tenant_id", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    queue_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    routing_strategy: Mapped[str] = mapped_column(String(32), nullable=False, default="manual", server_default="manual")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class ConversationAssignment(Base):
    __tablename__ = "conversation_assignments"
    __table_args__ = (
        Index("idx_conversation_assignments_tenant_state", "tenant_id", "state", "updated_at"),
        Index("idx_conversation_assignments_queue_state", "queue_id", "state", "updated_at"),
        Index("idx_conversation_assignments_assignee_state", "assignee_user_id", "state", "updated_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    assignment_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("platform_tenants.id", ondelete="CASCADE"), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("platform_projects.id", ondelete="CASCADE"), nullable=False)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    queue_id: Mapped[int | None] = mapped_column(ForeignKey("inbox_queues.id", ondelete="SET NULL"), nullable=True)
    assignee_user_id: Mapped[int | None] = mapped_column(ForeignKey("panel_users.id", ondelete="SET NULL"), nullable=True)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="unassigned", server_default="unassigned")
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
