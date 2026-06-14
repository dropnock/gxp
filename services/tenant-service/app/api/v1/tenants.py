import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.platform import CrossTenantGrant, Tenant
from app.schemas.tenant import (
    CrossTenantGrantCreate,
    CrossTenantGrantRead,
    TenantCreate,
    TenantRead,
    TenantUpdate,
)
from app.services import provisioner
from gxp_shared.auth.dependencies import UserContext, require_platform_admin, require_roles

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Tenant CRUD ───────────────────────────────────────────────────────────────

@router.post("", response_model=TenantRead, status_code=status.HTTP_202_ACCEPTED)
async def create_tenant(
    body: TenantCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_platform_admin),
):
    """Provision a new tenant. Provisioning runs asynchronously after the record is created."""
    existing = await db.execute(select(Tenant).where(Tenant.slug == body.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Tenant slug '{body.slug}' already exists")

    tenant = Tenant(
        slug=body.slug,
        name=body.name,
        keycloak_realm=f"gxp-{body.slug}",
        status="active",
        created_by=user.user_id,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)

    background_tasks.add_task(
        provisioner.provision_tenant,
        slug=body.slug,
        name=body.name,
        created_by=user.user_id,
    )

    return tenant


@router.get("", response_model=list[TenantRead])
async def list_tenants(
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_platform_admin),
):
    result = await db.execute(select(Tenant).order_by(Tenant.name))
    return result.scalars().all()


@router.get("/{slug}", response_model=TenantRead)
async def get_tenant(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_platform_admin),
):
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.patch("/{slug}", response_model=TenantRead)
async def update_tenant(
    slug: str,
    body: TenantUpdate,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_platform_admin),
):
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(tenant, field, value)

    await db.commit()
    await db.refresh(tenant)
    return tenant


# ── Cross-Tenant Grants ───────────────────────────────────────────────────────

@router.post(
    "/{slug}/cross-tenant-grants",
    response_model=CrossTenantGrantRead,
    status_code=status.HTTP_201_CREATED,
)
async def request_cross_tenant_grant(
    slug: str,
    body: CrossTenantGrantCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_roles("gxp-admin", "gxp-platform-admin")),
):
    """Requesting tenant admin initiates a cross-tenant access request."""
    req_result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    requesting = req_result.scalar_one_or_none()
    if not requesting:
        raise HTTPException(status_code=404, detail="Requesting tenant not found")

    grant_result = await db.execute(select(Tenant).where(Tenant.slug == body.granting_tenant_slug))
    granting = grant_result.scalar_one_or_none()
    if not granting:
        raise HTTPException(status_code=404, detail="Granting tenant not found")

    grant = CrossTenantGrant(
        requesting_tenant_id=requesting.id,
        granting_tenant_id=granting.id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        permissions=body.permissions,
        requested_by=user.user_id,
        status="pending",
        expires_at=body.expires_at,
    )
    db.add(grant)
    await db.commit()
    await db.refresh(grant)
    return grant


@router.post("/{slug}/cross-tenant-grants/{grant_id}/approve", response_model=CrossTenantGrantRead)
async def approve_cross_tenant_grant(
    slug: str,
    grant_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_roles("gxp-admin", "gxp-platform-admin")),
):
    """Granting tenant admin approves a pending cross-tenant access request."""
    grant_result = await db.execute(select(CrossTenantGrant).where(CrossTenantGrant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    if grant.status != "pending":
        raise HTTPException(status_code=409, detail=f"Grant is already {grant.status}")

    grant.status = "approved"
    grant.approved_by = user.user_id
    await db.commit()
    await db.refresh(grant)
    return grant


@router.delete("/{slug}/cross-tenant-grants/{grant_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_cross_tenant_grant(
    slug: str,
    grant_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_roles("gxp-admin", "gxp-platform-admin")),
):
    grant_result = await db.execute(select(CrossTenantGrant).where(CrossTenantGrant.id == grant_id))
    grant = grant_result.scalar_one_or_none()
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    grant.status = "revoked"
    await db.commit()


@router.get("/{slug}/cross-tenant-grants", response_model=list[CrossTenantGrantRead])
async def list_cross_tenant_grants(
    slug: str,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_roles("gxp-admin", "gxp-platform-admin")),
):
    tenant_result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = tenant_result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    result = await db.execute(
        select(CrossTenantGrant).where(
            (CrossTenantGrant.requesting_tenant_id == tenant.id)
            | (CrossTenantGrant.granting_tenant_id == tenant.id)
        )
    )
    return result.scalars().all()
