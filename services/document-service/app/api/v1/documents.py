"""
Document upload, download, metadata, versioning, and permission management.

Upload flow (POST /documents):
  1. Stream file to MinIO staging bucket
  2. Insert Document + DocumentVersion rows (av_status='pending')
  3. Enqueue Celery scan_document task
  4. Return 202 Accepted — client polls GET /documents/{id} for av_status

Download flow (GET /documents/{id}/download):
  1. Permission check
  2. Verify current_version exists and is 'clean'
  3. Generate 5-minute MinIO presigned URL
  4. Return 302 redirect
"""
from __future__ import annotations

import io
import uuid
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.document import Document, DocumentPermission, DocumentVersion
from app.services.permissions import check_permission
from app.storage.minio_client import (
    docs_bucket, generate_presigned_url, object_key,
    stage_bucket, upload_to_staging,
)
from app.worker.tasks import scan_document
from gxp_shared.auth.dependencies import UserContext, get_current_user

router = APIRouter()


# ── Upload ─────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    folder_id: Optional[UUID] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # comma-separated
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """
    Upload a new document or a new version of an existing document.
    Returns 202 immediately; poll GET /documents/{id} for scan status.
    """
    tenant_slug = user.tenant_slug
    if not tenant_slug:
        raise HTTPException(status_code=403, detail="Tenant context required")

    # Permission check: need write on the target folder (if provided)
    if folder_id:
        await check_permission(
            db=db, user=user, resource_type="folder",
            resource_id=folder_id, required_permission="write",
        )

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    mime_type = file.content_type or "application/octet-stream"

    # Read file into memory (for size + hash; acceptable for government doc sizes)
    file_bytes = await file.read()
    size = len(file_bytes)

    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()

    # Determine version number
    # For a new document there is no prior version; we'll handle update-to-existing later
    version_number = 1

    # Upload to MinIO staging
    bucket = stage_bucket(tenant_slug)
    key = object_key(str(doc_id), str(version_id))
    upload_to_staging(
        tenant_slug=tenant_slug,
        document_id=str(doc_id),
        version_id=str(version_id),
        data=io.BytesIO(file_bytes),
        content_type=mime_type,
        size=size,
    )

    # Persist Document + DocumentVersion
    doc = Document(
        id=doc_id,
        folder_id=folder_id,
        name=file.filename or "untitled",
        description=description,
        mime_type=mime_type,
        tags=tag_list,
        created_by=user.user_id,
    )
    db.add(doc)
    await db.flush()  # get doc.id before version insert

    version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=version_number,
        minio_bucket=bucket,
        minio_key=key,
        size_bytes=size,
        av_status="pending",
        uploaded_by=user.user_id,
    )
    db.add(version)
    await db.commit()

    # Enqueue AV scan (Celery)
    scan_document.apply_async(
        args=[str(version_id), str(doc_id), tenant_slug, mime_type],
        queue="document",
    )

    return {
        "id": str(doc_id),
        "version_id": str(version_id),
        "name": doc.name,
        "av_status": "pending",
        "message": "Upload accepted. Document will be available after AV scan completes.",
    }


@router.post("/{document_id}/versions", status_code=status.HTTP_202_ACCEPTED)
async def upload_new_version(
    document_id: UUID,
    file: UploadFile = File(...),
    description: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """Upload a new version of an existing document."""
    tenant_slug = user.tenant_slug
    if not tenant_slug:
        raise HTTPException(status_code=403, detail="Tenant context required")

    doc = await _get_document_or_404(db, document_id)
    await check_permission(
        db=db, user=user, resource_type="document",
        resource_id=document_id, required_permission="write",
        folder_id=doc.folder_id,
    )

    # Next version number
    result = await db.execute(
        select(func.max(DocumentVersion.version_number))
        .where(DocumentVersion.document_id == document_id)
    )
    max_ver = result.scalar_one_or_none() or 0
    version_number = max_ver + 1

    mime_type = file.content_type or "application/octet-stream"
    file_bytes = await file.read()
    version_id = uuid.uuid4()

    upload_to_staging(
        tenant_slug=tenant_slug,
        document_id=str(document_id),
        version_id=str(version_id),
        data=io.BytesIO(file_bytes),
        content_type=mime_type,
        size=len(file_bytes),
    )

    version = DocumentVersion(
        id=version_id,
        document_id=document_id,
        version_number=version_number,
        minio_bucket=stage_bucket(tenant_slug),
        minio_key=object_key(str(document_id), str(version_id)),
        size_bytes=len(file_bytes),
        av_status="pending",
        uploaded_by=user.user_id,
    )
    db.add(version)
    await db.commit()

    scan_document.apply_async(
        args=[str(version_id), str(document_id), tenant_slug, mime_type],
        queue="document",
    )

    return {
        "document_id": str(document_id),
        "version_id": str(version_id),
        "version_number": version_number,
        "av_status": "pending",
    }


# ── List + metadata ────────────────────────────────────────────────────────────

@router.get("")
async def list_documents(
    folder_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """List documents in a folder (or root if folder_id omitted)."""
    stmt = (
        select(Document)
        .where(Document.is_deleted == False, Document.folder_id == folder_id)  # noqa: E712
        .order_by(Document.name)
    )
    result = await db.execute(stmt)
    docs = result.scalars().all()
    return [_serialize_doc(d) for d in docs]


@router.get("/{document_id}")
async def get_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    doc = await _get_document_or_404(db, document_id)
    await check_permission(
        db=db, user=user, resource_type="document",
        resource_id=document_id, required_permission="read",
        folder_id=doc.folder_id,
    )
    return _serialize_doc(doc)


@router.get("/{document_id}/versions")
async def list_versions(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    doc = await _get_document_or_404(db, document_id)
    await check_permission(
        db=db, user=user, resource_type="document",
        resource_id=document_id, required_permission="read",
        folder_id=doc.folder_id,
    )
    result = await db.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == document_id)
        .order_by(DocumentVersion.version_number.desc())
    )
    return [_serialize_version(v) for v in result.scalars().all()]


# ── Download ───────────────────────────────────────────────────────────────────

@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    version_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    """
    Returns a 302 redirect to a 5-minute MinIO presigned download URL.
    Only clean (AV-cleared) versions can be downloaded.
    """
    doc = await _get_document_or_404(db, document_id)
    await check_permission(
        db=db, user=user, resource_type="document",
        resource_id=document_id, required_permission="read",
        folder_id=doc.folder_id,
    )

    # Resolve the version to download
    if version_id:
        ver_result = await db.execute(
            select(DocumentVersion).where(
                DocumentVersion.id == version_id,
                DocumentVersion.document_id == document_id,
            )
        )
        version = ver_result.scalar_one_or_none()
    elif doc.current_version_id:
        ver_result = await db.execute(
            select(DocumentVersion).where(DocumentVersion.id == doc.current_version_id)
        )
        version = ver_result.scalar_one_or_none()
    else:
        version = None

    if not version:
        raise HTTPException(status_code=404, detail="No available version found")
    if version.av_status != "clean":
        raise HTTPException(
            status_code=409,
            detail=f"Document version is not available for download (av_status={version.av_status})",
        )

    url = generate_presigned_url(
        bucket=version.minio_bucket,
        key=version.minio_key,
        expiry_seconds=300,
    )
    return RedirectResponse(url=url, status_code=302)


# ── Delete ─────────────────────────────────────────────────────────────────────

@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    doc = await _get_document_or_404(db, document_id)
    await check_permission(
        db=db, user=user, resource_type="document",
        resource_id=document_id, required_permission="delete",
        folder_id=doc.folder_id,
    )
    doc.is_deleted = True
    await db.commit()


# ── Permissions ────────────────────────────────────────────────────────────────

@router.post("/{document_id}/permissions", status_code=status.HTTP_201_CREATED)
async def grant_document_permission(
    document_id: UUID,
    body: dict,
    db: AsyncSession = Depends(get_db),
    user: UserContext = Depends(get_current_user),
):
    doc = await _get_document_or_404(db, document_id)
    await check_permission(
        db=db, user=user, resource_type="document",
        resource_id=document_id, required_permission="write",
        folder_id=doc.folder_id,
    )
    perm = DocumentPermission(
        resource_type="document",
        resource_id=document_id,
        principal_type=body["principal_type"],
        principal_id=body["principal_id"],
        permissions=body["permissions"],
        created_by=user.user_id,
    )
    db.add(perm)
    await db.commit()
    return {"granted": True}


# ── Helpers ────────────────────────────────────────────────────────────────────

async def _get_document_or_404(db: AsyncSession, document_id: UUID) -> Document:
    result = await db.execute(
        select(Document).where(Document.id == document_id, Document.is_deleted == False)  # noqa: E712
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


def _serialize_doc(d: Document) -> dict:
    return {
        "id": str(d.id),
        "folder_id": str(d.folder_id) if d.folder_id else None,
        "name": d.name,
        "description": d.description,
        "mime_type": d.mime_type,
        "tags": d.tags or [],
        "current_version_id": str(d.current_version_id) if d.current_version_id else None,
        "created_by": d.created_by,
        "created_at": d.created_at.isoformat() if d.created_at else "",
        "updated_at": d.updated_at.isoformat() if d.updated_at else "",
    }


def _serialize_version(v: DocumentVersion) -> dict:
    return {
        "id": str(v.id),
        "document_id": str(v.document_id),
        "version_number": v.version_number,
        "size_bytes": v.size_bytes,
        "checksum_sha256": v.checksum_sha256,
        "av_status": v.av_status,
        "av_scanned_at": v.av_scanned_at.isoformat() if v.av_scanned_at else None,
        "uploaded_by": v.uploaded_by,
        "uploaded_at": v.uploaded_at.isoformat() if v.uploaded_at else "",
    }
