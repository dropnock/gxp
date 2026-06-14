from fastapi import APIRouter

from app.api.v1 import apps, cross_tenant, pages, publish

router = APIRouter()
router.include_router(apps.router, prefix="/apps", tags=["apps"])
router.include_router(pages.router, prefix="/apps", tags=["pages"])
router.include_router(publish.router, prefix="/apps", tags=["publish"])
router.include_router(cross_tenant.router, prefix="/apps", tags=["cross-tenant"])
