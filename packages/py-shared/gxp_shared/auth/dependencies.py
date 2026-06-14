"""
FastAPI dependency factories for authentication and authorization.

Usage in route files:

    from gxp_shared.auth.dependencies import get_current_user, require_roles

    @router.get("/items")
    async def list_items(user: UserContext = Depends(get_current_user)):
        ...

    @router.post("/items")
    async def create_item(
        _: UserContext = Depends(require_roles("gxp-developer", "gxp-admin")),
    ):
        ...
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, HTTPException, Request


@dataclass(frozen=True)
class UserContext:
    user_id: str
    email: str
    roles: list[str]
    tenant_slug: str | None


def get_current_user(request: Request) -> UserContext:
    """
    Reads identity set by TenantContextMiddleware.
    Raises 401 if the middleware did not authenticate the request.
    """
    user_id: str | None = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return UserContext(
        user_id=user_id,
        email=getattr(request.state, "user_email", ""),
        roles=getattr(request.state, "user_roles", []),
        tenant_slug=getattr(request.state, "tenant_slug", None),
    )


def require_roles(*roles: str) -> Callable[..., UserContext]:
    """
    Returns a FastAPI Depends factory that ensures the caller has at least
    one of the listed roles.  Roles are Keycloak realm_access roles.

    Example:
        Depends(require_roles("gxp-admin", "gxp-developer"))
    """
    role_set = set(roles)

    def _check(user: UserContext = Depends(get_current_user)) -> UserContext:
        if not role_set.intersection(user.roles):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of: {', '.join(sorted(role_set))}",
            )
        return user

    return _check


def require_platform_admin(user: UserContext = Depends(get_current_user)) -> UserContext:
    """
    Ensures the caller is authenticated against the gxp-platform realm.
    Platform admins have no tenant_slug (their iss is .../realms/gxp-platform).
    """
    if user.tenant_slug is not None:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    if "gxp-platform-admin" not in user.roles:
        raise HTTPException(status_code=403, detail="Platform admin access required")
    return user
