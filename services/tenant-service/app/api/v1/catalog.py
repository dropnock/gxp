from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.platform import CatalogTemplate
from app.schemas.tenant import CatalogTemplateCreate, CatalogTemplateRead
from app.services import catalog as catalog_svc
from gxp_shared.auth.dependencies import UserContext, get_current_user, require_platform_admin

router = APIRouter()


@router.get("", response_model=list[CatalogTemplateRead])
async def list_catalog(
    category: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(get_current_user),
):
    """List active catalog templates. Accessible to all authenticated users."""
    q = select(CatalogTemplate).where(CatalogTemplate.is_active == True)  # noqa: E712
    if category:
        q = q.where(CatalogTemplate.category == category)
    result = await db.execute(q.order_by(CatalogTemplate.name))
    return result.scalars().all()


@router.post("", response_model=CatalogTemplateRead, status_code=status.HTTP_201_CREATED)
async def publish_template(
    body: CatalogTemplateCreate,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(require_platform_admin),
):
    """Publish a new catalog template. Platform super-admin only."""
    template = CatalogTemplate(
        category=body.category,
        name=body.name,
        description=body.description,
        schema_json=body.template_body,
        tags=body.tags,
        published_by=user.user_id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.post("/{template_id}/fork", status_code=status.HTTP_201_CREATED)
async def fork_template(
    template_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """
    Copy a catalog template into the calling tenant's namespace.
    The tenant is resolved from the caller's JWT.
    """
    if not user.tenant_slug:
        raise HTTPException(status_code=400, detail="Could not resolve tenant from token")

    auth_header = request.headers.get("authorization", "")
    actor_token = auth_header.removeprefix("Bearer ").strip()

    try:
        result = await catalog_svc.fork_template(
            template_id=template_id,
            requesting_tenant_slug=user.tenant_slug,
            actor_token=actor_token,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return result


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    _user: UserContext = Depends(require_platform_admin),
):
    """Deactivate (soft-delete) a catalog template. Platform super-admin only."""
    result = await db.execute(select(CatalogTemplate).where(CatalogTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    template.is_active = False
    await db.commit()
