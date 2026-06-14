from fastapi import APIRouter
from app.api.v1 import cases, case_types, cross_tenant

router = APIRouter()
router.include_router(case_types.router, prefix="/case-types", tags=["case-types"])
router.include_router(cases.router, prefix="/cases", tags=["cases"])
router.include_router(cross_tenant.router, prefix="/cases", tags=["cross-tenant"])
