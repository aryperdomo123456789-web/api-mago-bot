from __future__ import annotations

import os
from typing import Literal

from fastapi import HTTPException, Request, status

Surface = Literal["operations", "customer"]

OPERATIONS_HOST = os.getenv("OPERATIONS_CANONICAL_HOST", "evo-api.mago-bot.com").lower().rstrip(".")
CUSTOMER_HOST = os.getenv("CUSTOMER_CANONICAL_HOST", "app.mago-bot.com").lower().rstrip(".")

OPERATIONS_ROLES = frozenset(
    {
        "owner",
        "platform_superadmin",
        "platform_operator",
        "platform_support",
    }
)
CUSTOMER_ROLES = frozenset(
    {
        "owner",
        "tenant_owner",
        "tenant_admin",
        "tenant_developer",
        "tenant_billing",
        "tenant_readonly",
        "customer_common",
    }
)

_GENERIC_LOGIN_ERROR = "invalid credentials"
_SURFACE_DENIED = "surface access denied"


def _hostname(request: Request) -> str:
    # Host is parsed server-side from the request URL. No frontend field is trusted.
    return (request.url.hostname or "").lower().rstrip(".")


def surface_for_request(request: Request) -> Surface:
    host = _hostname(request)
    if host == OPERATIONS_HOST:
        return "operations"
    if host == CUSTOMER_HOST:
        return "customer"

    if os.getenv("ALLOW_LOCAL_SURFACE_HOSTS", "false").lower() == "true" and host in {"127.0.0.1", "localhost", "::1"}:
        return "customer"
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")


def require_operations_surface(request: Request) -> Surface:
    surface = surface_for_request(request)
    if surface != "operations":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return surface


def require_customer_surface(request: Request) -> Surface:
    surface = surface_for_request(request)
    if surface != "customer":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not found")
    return surface


def role_allowed_on_surface(role: str, surface: Surface) -> bool:
    return role in (OPERATIONS_ROLES if surface == "operations" else CUSTOMER_ROLES)


def enforce_login_surface(request: Request, role: str | None) -> None:
    try:
        surface = surface_for_request(request)
    except HTTPException:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_LOGIN_ERROR) from None
    if not role or not role_allowed_on_surface(role, surface):
        # Do not disclose that an account exists or reveal its role.
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=_GENERIC_LOGIN_ERROR)


def enforce_authenticated_surface(request: Request, role: str | None) -> None:
    surface = surface_for_request(request)
    if not role or not role_allowed_on_surface(role, surface):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=_SURFACE_DENIED)


def _is_shared_auth_path(path: str) -> bool:
    return path in {
        "/v1/platform/auth/login",
        "/v1/platform/auth/logout",
        "/v1/platform/auth/me",
    } or path.startswith("/v1/platform/auth/mfa")


def route_surface_status(request: Request) -> int | None:
    """Return a safe HTTP status for a route/surface mismatch, or None to continue.

    Authentication bootstrap paths are allowed on both canonical domains because
    the login handler itself enforces the role. Every other protected path is
    pinned to exactly one surface before the route handler runs.
    """
    path = request.url.path.rstrip("/") or "/"
    if path.startswith("/v1/platform/auth/"):
        try:
            surface_for_request(request)
        except HTTPException:
            return status.HTTP_404_NOT_FOUND
        if _is_shared_auth_path(path):
            return None
        # Signup, email verification and password reset belong to the customer surface.
        return status.HTTP_404_NOT_FOUND if surface_for_request(request) != "customer" else None

    if path == "/ops" or path.startswith("/ops/") or path == "/v1/ops" or path.startswith("/v1/ops/"):
        required: Surface = "operations"
    elif path == "/v1/platform/owner" or path.startswith("/v1/platform/owner/") or path == "/v1/admin" or path.startswith("/v1/admin/"):
        required = "operations"
    elif path == "/admin" or path.startswith("/admin/") or path == "/platform" or path.startswith("/platform/"):
        required = "customer"
    elif path == "/v1/platform" or path.startswith("/v1/platform/"):
        required = "customer"
    elif path in {
        "/v1/organizations",
        "/v1/integrations",
        "/v1/channels",
        "/v1/messages",
        "/v1/conversations",
        "/v1/billing",
        "/v1/analytics",
        "/v1/jobs",
        "/v1/onboarding",
        "/v1/operations",
    } or any(path.startswith(prefix + "/") for prefix in {
        "/v1/organizations",
        "/v1/integrations",
        "/v1/channels",
        "/v1/messages",
        "/v1/conversations",
        "/v1/billing",
        "/v1/analytics",
        "/v1/jobs",
        "/v1/onboarding",
        "/v1/operations",
    }):
        required = "customer"
    elif path in {
        "/v1/auth",
        "/v1/account",
        "/v1/users",
        "/v1/licenses",
        "/v1/projects",
        "/v1/keys",
        "/v1/plans/catalog",
        "/v1/trials",
        "/v1/partners/applications",
    } or any(path.startswith(prefix + "/") for prefix in {
        "/v1/auth",
        "/v1/account",
        "/v1/users",
        "/v1/licenses",
        "/v1/projects",
        "/v1/keys",
        "/v1/plans/catalog",
        "/v1/trials",
        "/v1/partners/applications",
    }):
        required = "operations"
    else:
        return None

    try:
        return None if surface_for_request(request) == required else status.HTTP_404_NOT_FOUND
    except HTTPException:
        return status.HTTP_404_NOT_FOUND
