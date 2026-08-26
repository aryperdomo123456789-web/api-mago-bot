from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import PanelUser
from .platform_models import TenantMembership

PLATFORM_ROLES = frozenset({"platform_superadmin", "platform_operator", "platform_support", "platform_partner", "owner"})
TENANT_ROLES = frozenset({"tenant_owner", "tenant_admin", "tenant_developer", "tenant_billing", "tenant_readonly", "customer_common"})
ALL_ROLES = PLATFORM_ROLES | TENANT_ROLES

PERMISSIONS: dict[str, frozenset[str]] = {
    "platform_superadmin": frozenset({"platform:*"}),
    "platform_operator": frozenset(
        {
            "tenant:read",
            "tenant:suspend",
            "project:read",
            "project:write",
            "conversation:read",
            "conversation:write",
            "resource:read",
            "resource:provision",
            "resource:operate",
            "webhook:read",
            "webhook:operate",
            "queue:read",
            "audit:read",
            "metrics:read",
        }
    ),
    "platform_support": frozenset({"tenant:read", "project:read", "conversation:read", "resource:read", "webhook:read", "audit:read:assigned"}),
    "platform_partner": frozenset({"tenant:read:assigned", "project:read:assigned", "resource:operate:assigned", "support:write:assigned"}),
    "tenant_owner": frozenset({"tenant:self", "membership:manage", "project:read", "project:write", "conversation:read", "conversation:write", "key:manage", "resource:read", "resource:request", "webhook:manage", "usage:read", "support:write"}),
    "tenant_admin": frozenset({"tenant:self", "project:read", "project:write", "conversation:read", "conversation:write", "key:manage", "resource:read", "resource:request", "webhook:manage", "usage:read", "support:write"}),
    "tenant_developer": frozenset({"project:read", "project:write", "conversation:read", "conversation:write", "key:manage", "resource:read", "webhook:manage", "usage:read", "support:write"}),
    "tenant_billing": frozenset({"tenant:self", "billing:manage", "usage:read", "support:write"}),
    "tenant_readonly": frozenset({"tenant:self", "project:read", "conversation:read", "resource:read", "webhook:read", "usage:read", "support:write"}),
    "customer_common": frozenset({"tenant:self", "project:read", "conversation:read", "resource:read", "usage:read", "support:write"}),
}


def ensure_known_role(role: str) -> None:
    if role not in ALL_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="role is not allowed")


def _role_permissions(role: str) -> frozenset[str]:
    ensure_known_role(role)
    return PERMISSIONS[role]


def has_permission(role: str, permission: str) -> bool:
    permissions = _role_permissions(role)
    return "platform:*" in permissions or permission in permissions


def require_platform_role(user: PanelUser, *allowed_roles: str) -> PanelUser:
    if user.role != "owner" and user.role not in allowed_roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="platform role required")
    return user


def get_membership(db: Session, user_id: int, tenant_id: int) -> TenantMembership:
    membership = db.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
            TenantMembership.status == "active",
        )
    )
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="resource not found")
    ensure_known_role(membership.role)
    return membership


def require_tenant_permission(db: Session, user: PanelUser, tenant_id: int, permission: str) -> TenantMembership:
    if user.role in PLATFORM_ROLES:
        if user.role == "platform_support" and permission not in {"tenant:read", "project:read", "conversation:read", "resource:read", "webhook:read", "audit:read:assigned", "metrics:read"}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
        return TenantMembership(tenant_id=tenant_id, user_id=user.id, role=user.role, status="active")

    membership = get_membership(db, user.id, tenant_id)
    if not has_permission(membership.role, permission):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="permission denied")
    return membership
