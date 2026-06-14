from fastapi import APIRouter

from app.api.v1 import tenants, catalog

router = APIRouter()
router.include_router(tenants.router, prefix="/tenants", tags=["tenants"])
router.include_router(catalog.router, prefix="/catalog", tags=["catalog"])
