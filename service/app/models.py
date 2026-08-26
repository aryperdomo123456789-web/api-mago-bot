import uuid as uuid_lib

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, JSON, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


class OwnerProfile(Base):
    __tablename__ = "owner_profile"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False, default="Dono wp-api")
    company_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PlanCatalog(Base):
    __tablename__ = "plan_catalog"
    __table_args__ = (
        Index("idx_plan_catalog_slug", "slug", unique=True),
        Index("idx_plan_catalog_active", "is_active"),
        Index("idx_plan_catalog_sort_order", "sort_order"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    subtitle: Mapped[str | None] = mapped_column(String(180), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_cents: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), nullable=False, default="BRL", server_default="BRL")
    trial_days: Mapped[int] = mapped_column(BigInteger, nullable=False, default=7, server_default="7")
    billing_period_days: Mapped[int] = mapped_column(BigInteger, nullable=False, default=30, server_default="30")
    max_instances: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_projects: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    max_keys: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    is_partner: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    cta_label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    features: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    sort_order: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CustomerAccount(Base):
    __tablename__ = "customer_accounts"
    __table_args__ = (
        Index("idx_customer_accounts_email", "email", unique=True),
        Index("idx_customer_accounts_status", "status"),
        Index("idx_customer_accounts_plan_slug", "plan_slug"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    account_uuid: Mapped[uuid_lib.UUID] = mapped_column(UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plan_slug: Mapped[str] = mapped_column(String(64), nullable=False, default="start", server_default="start")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="trialing", server_default="trialing")
    activation_code_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    activation_code_hint: Mapped[str | None] = mapped_column(String(12), nullable=True)
    trial_ends_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    license_project_id: Mapped[int | None] = mapped_column(ForeignKey("license_projects.id", ondelete="SET NULL"), nullable=True)
    license_id: Mapped[int | None] = mapped_column(ForeignKey("license_keys.id", ondelete="SET NULL"), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PartnerApplication(Base):
    __tablename__ = "partner_applications"
    __table_args__ = (
        Index("idx_partner_applications_email", "email"),
        Index("idx_partner_applications_status", "status"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(180), nullable=False)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    monthly_volume: Mapped[str | None] = mapped_column(String(80), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending", server_default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reviewed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class PanelUser(Base):
    __tablename__ = "panel_users"
    __table_args__ = (
        Index("idx_panel_users_email", "email", unique=True),
        Index("idx_panel_users_role", "role"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_salt: Mapped[str] = mapped_column(String(32), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(180), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    whatsapp_opt_in: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    whatsapp_opt_in_source: Mapped[str | None] = mapped_column(String(180), nullable=True)
    whatsapp_opt_in_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False, default="subscriber", server_default="subscriber")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    mfa_secret_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    mfa_recovery_hashes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mfa_last_used_counter: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    mfa_enrolled_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    password_changed_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LicenseProject(Base):
    __tablename__ = "license_projects"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    slug: Mapped[str] = mapped_column(String(180), nullable=False, unique=True, index=True)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    licenses: Mapped[list["LicenseKey"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class LicenseKey(Base):
    __tablename__ = "license_keys"
    __table_args__ = (
        Index("idx_license_keys_project_status", "project_id", "status"),
        Index("idx_license_keys_expires_at", "expires_at"),
        Index("idx_license_keys_last_used_at", "last_used_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    license_uuid: Mapped[uuid_lib.UUID] = mapped_column("uuid", UUID(as_uuid=True), default=uuid_lib.uuid4, unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(180), nullable=False)
    project_id: Mapped[int] = mapped_column(ForeignKey("license_projects.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    scopes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active", server_default="active")
    expires_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[str | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    extra_metadata: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    project: Mapped[LicenseProject] = relationship(back_populates="licenses")
    audits: Mapped[list["LicenseAuditLog"]] = relationship(back_populates="license", cascade="all, delete-orphan")


class LicenseAuditLog(Base):
    __tablename__ = "license_audit_log"
    __table_args__ = (
        Index("idx_license_audit_license_created_at", "license_id", "created_at"),
        Index("idx_license_audit_action_created_at", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    license_id: Mapped[int] = mapped_column(ForeignKey("license_keys.id", ondelete="CASCADE"), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    status_before: Mapped[str | None] = mapped_column(String(24), nullable=True)
    status_after: Mapped[str | None] = mapped_column(String(24), nullable=True)
    actor: Mapped[str | None] = mapped_column(String(120), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[str] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    license: Mapped[LicenseKey] = relationship(back_populates="audits")
