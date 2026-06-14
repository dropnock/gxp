"""
Cross-tenant read access for documents.

GET /api/v1/documents/cross-tenant/{tenant_slug}/{document_id}/download
  - Validates a cross-tenant grant
  - Returns a 5-minute presigned MinIO URL for the document from the granting tenant
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select, text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.document import Document, DocumentVersion
from app.storage.minio_client import docs_bucket, generate_presigned_url, object_key
from gxp_shared.auth.cross_tenant import assert_cross_tenant_grant
from gxp_shared.auth.dependencies import UserContext, get_current_user

router = APIRouter()


@router.get("/cross-tenant/{tenant_slug}/{document_id}/download")
async def download_cross_tenant_document(
    tenant_slug: str,
    document_id: UUID,
    user: UserContext = Depends(get_current_user),
):
    """
    Download a document from a different tenant via a short-lived presigned URL.
    Requires an approved cross-tenant grant with 'read' permission.
    """
    requesting = user.tenant_slug
    if not requesting:
        raise HTTPException(status_code=403, detail="Tenant context required")
    if requesting == tenant_slug:
        raise HTTPException(status_code=400, detail="Use the standard endpoint for same-tenant access")

    await assert_cross_tenant_grant(
        requesting_tenant=requesting,
        granting_tenant=tenant_slug,
        resource_type="document",
        resource_id=document_id,
        required_permission="read",
        tenant_service_db_url=settings.tenant_service_db_url,
        valkey_url=settings.valkey_url,
    )

    async with AsyncSessionLocal() as db:
        await db.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))

        result = await db.execute(select(Document).where(Document.id == document_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found in granting tenant")

        if not doc.current_version_id:
            raise HTTPException(status_code=404, detail="Document has no current version")

        ver_result = await db.execute(
            select(DocumentVersion).where(DocumentVersion.id == doc.current_version_id)
        )
        version = ver_result.scalar_one_or_none()
        if not version:
            raise HTTPException(status_code=404, detail="Document version not found")

        if version.av_status != "clean":
            raise HTTPException(status_code=403, detail="Document has not passed antivirus scan")

    bucket = docs_bucket(tenant_slug)
    key = object_key(document_id, version.id)
    url = generate_presigned_url(bucket, key, expiry=settings.presign_expiry_seconds)
    return RedirectResponse(url=url, status_code=302)
