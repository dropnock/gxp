"""Platform catalog — publish templates and fork them into tenant namespaces."""
from __future__ import annotations

import logging
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.platform import CatalogTemplate

logger = logging.getLogger(__name__)

# Maps catalog category to the downstream service endpoint that accepts the resource
_FORK_TARGETS: dict[str, str] = {
    "app": f"http://app-service:8000/api/v1/apps",
    "workflow": f"http://workflow-service:8000/api/v1/workflow/definitions",
    "dmn": f"http://workflow-service:8000/api/v1/workflow/dmn-definitions",
    "case_type": f"http://case-service:8000/api/v1/case-types",
}


async def fork_template(
    template_id: UUID,
    requesting_tenant_slug: str,
    actor_token: str,
    db: AsyncSession,
) -> dict:
    """
    Copies a catalog template into the requesting tenant's namespace by calling
    the appropriate downstream service with the template's schema_json.
    The forked resource is fully owned by the tenant — no live link to the catalog.
    """
    result = await db.execute(
        select(CatalogTemplate).where(
            CatalogTemplate.id == template_id,
            CatalogTemplate.is_active == True,  # noqa: E712
        )
    )
    template = result.scalar_one_or_none()
    if template is None:
        raise ValueError(f"Catalog template {template_id} not found or inactive")

    target_url = _FORK_TARGETS.get(template.category)
    if target_url is None:
        raise ValueError(f"Unknown catalog category: {template.category}")

    # Forward the fork request to the owning service with the tenant's JWT so
    # TenantContextMiddleware on the target service scopes it to the right schema.
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            target_url,
            json={**template.schema_json, "_forked_from_catalog": str(template_id)},
            headers={
                "Authorization": f"Bearer {actor_token}",
                "X-Tenant-Slug": requesting_tenant_slug,
            },
        )
        resp.raise_for_status()

    logger.info(
        "Forked catalog template %s (%s) into tenant %s",
        template.name,
        template_id,
        requesting_tenant_slug,
    )
    return resp.json()
