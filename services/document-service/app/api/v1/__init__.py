from fastapi import APIRouter
from app.api.v1 import cross_tenant, documents, folders, search

router = APIRouter()
router.include_router(folders.router, prefix="/documents/folders", tags=["folders"])
router.include_router(documents.router, prefix="/documents", tags=["documents"])
router.include_router(search.router, prefix="/documents/search", tags=["document-search"])
router.include_router(cross_tenant.router, prefix="/documents", tags=["cross-tenant"])
