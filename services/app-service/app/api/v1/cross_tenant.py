"""
Cross-tenant read access for apps.

GET /api/v1/apps/cross-tenant/{tenant_slug}/{app_id}
  - Validates a cross-tenant grant (requesting tenant from JWT, granting tenant from path)
  - Returns the published app schema from the granting tenant's schema
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.app import AppVersion, GxpApp
from gxp_shared.auth.cross_tenant import assert_cross_tenant_grant
from gxp_shared.auth.dependencies import UserContext, get_current_user

router = APIRouter()


@router.get("/cross-tenant/{tenant_slug}/{app_id}")
async def get_cross_tenant_app(
    tenant_slug: str,
    app_id: UUID,
    user: UserContext = Depends(get_current_user),
):
    """
    Read a published app from a different tenant.
    Requires an approved cross-tenant grant with 'read' permission on this app.
    """
    requesting = user.tenant_slug
    if not requesting:
        raise HTTPException(status_code=403, detail="Tenant context required")
    if requesting == tenant_slug:
        raise HTTPException(status_code=400, detail="Use the standard endpoint for same-tenant access")

    await assert_cross_tenant_grant(
        requesting_tenant=requesting,
        granting_tenant=tenant_slug,
        resource_type="app",
        resource_id=app_id,
        required_permission="read",
        tenant_service_db_url=settings.tenant_service_db_url,
        valkey_url=settings.valkey_url,
    )

    async with AsyncSessionLocal() as db:
        await db.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))
        result = await db.execute(
            select(GxpApp).where(GxpApp.id == app_id, GxpApp.status == "published")
        )
        app = result.scalar_one_or_none()
        if not app:
            raise HTTPException(status_code=404, detail="Published app not found in granting tenant")

        if app.current_version_id:
            ver_result = await db.execute(
                select(AppVersion).where(AppVersion.id == app.current_version_id)
            )
            version = ver_result.scalar_one_or_none()
        else:
            version = None

    return {
        "id": str(app.id),
        "name": app.name,
        "status": app.status,
        "tenant_slug": tenant_slug,
        "current_version": {
            "id": str(version.id),
            "version_number": version.version_number,
            "minio_key": version.minio_key,
            "schema": version.schema_snapshot,
        } if version else None,
    }
