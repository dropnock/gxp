"""
Cross-tenant access enforcement.

Call assert_cross_tenant_grant() in any service endpoint that may receive
a request from a different tenant than the resource owner.
"""
from __future__ import annotations

import logging
from typing import Literal
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import HTTPException

logger = logging.getLogger(__name__)

_GRANT_CACHE_TTL = 60  # seconds — short TTL so revocations propagate quickly

ResourceType = Literal["document", "app", "workflow_definition", "case"]
Permission = Literal["read", "write"]


async def assert_cross_tenant_grant(
    *,
    requesting_tenant: str,
    granting_tenant: str,
    resource_type: ResourceType,
    resource_id: UUID,
    required_permission: Permission,
    tenant_service_db_url: str,
    valkey_url: str,
) -> None:
    """
    Raises HTTPException(403) if no approved cross-tenant grant exists that covers
    the requested resource and permission.

    Checks a short-lived Valkey cache first to avoid hitting the DB on every request.
    Falls back to direct DB query on cache miss.
    """
    if requesting_tenant == granting_tenant:
        return  # same-tenant access always allowed

    cache_key = _cache_key(requesting_tenant, granting_tenant, resource_type, resource_id, required_permission)

    r = aioredis.from_url(valkey_url, decode_responses=True)
    cached = await r.get(cache_key)
    if cached == "1":
        return
    if cached == "0":
        raise HTTPException(status_code=403, detail="Cross-tenant access not granted")

    # Cache miss — query the tenant-service database directly
    granted = await _check_db(
        requesting_tenant=requesting_tenant,
        granting_tenant=granting_tenant,
        resource_type=resource_type,
        resource_id=resource_id,
        required_permission=required_permission,
        db_url=tenant_service_db_url,
    )

    # Cache result briefly
    await r.setex(cache_key, _GRANT_CACHE_TTL, "1" if granted else "0")

    if not granted:
        raise HTTPException(status_code=403, detail="Cross-tenant access not granted")


def _cache_key(
    requesting: str,
    granting: str,
    resource_type: str,
    resource_id: UUID,
    permission: str,
) -> str:
    return f"gxp:grant:{requesting}:{granting}:{resource_type}:{resource_id}:{permission}"


async def _check_db(
    requesting_tenant: str,
    granting_tenant: str,
    resource_type: str,
    resource_id: UUID,
    required_permission: str,
    db_url: str,
) -> bool:
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = create_async_engine(db_url, echo=False)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(
                text("""
                    SELECT 1
                    FROM platform.cross_tenant_grants g
                    JOIN platform.tenants req ON req.id = g.requesting_tenant_id
                    JOIN platform.tenants grt ON grt.id = g.granting_tenant_id
                    WHERE req.slug = :requesting
                      AND grt.slug = :granting
                      AND g.resource_type = :resource_type
                      AND g.resource_id = :resource_id
                      AND g.status = 'approved'
                      AND (g.expires_at IS NULL OR g.expires_at > now())
                      AND :permission = ANY(g.permissions)
                    LIMIT 1
                """),
                {
                    "requesting": requesting_tenant,
                    "granting": granting_tenant,
                    "resource_type": resource_type,
                    "resource_id": str(resource_id),
                    "permission": required_permission,
                },
            )
            return result.fetchone() is not None
    finally:
        await engine.dispose()
