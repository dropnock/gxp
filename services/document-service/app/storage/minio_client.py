"""
MinIO client wrapper for document storage.

Bucket naming per tenant:
  gxp-stage-{slug}       upload staging (pre-AV scan)
  gxp-docs-{slug}        clean documents (after AV clearance, WORM)
  gxp-quarantine-{slug}  infected files

Key scheme (all buckets):
  {document_id}/{version_id}   (filename not embedded so keys are stable)
"""
from __future__ import annotations

import hashlib
import io
from datetime import timedelta
from typing import IO

from minio import Minio
from minio.error import S3Error

from app.config import settings

_client: Minio | None = None


def get_client() -> Minio:
    global _client
    if _client is None:
        _client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )
    return _client


def stage_bucket(tenant_slug: str) -> str:
    return f"gxp-stage-{tenant_slug}"


def docs_bucket(tenant_slug: str) -> str:
    return f"gxp-docs-{tenant_slug}"


def quarantine_bucket(tenant_slug: str) -> str:
    return f"gxp-quarantine-{tenant_slug}"


def object_key(document_id: str, version_id: str) -> str:
    return f"{document_id}/{version_id}"


def upload_to_staging(
    tenant_slug: str,
    document_id: str,
    version_id: str,
    data: IO[bytes],
    content_type: str,
    size: int,
) -> tuple[str, str]:
    """Upload file to staging bucket. Returns (bucket, key)."""
    client = get_client()
    bucket = stage_bucket(tenant_slug)
    key = object_key(document_id, version_id)
    client.put_object(bucket, key, data, length=size, content_type=content_type)
    return bucket, key


def compute_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_bytes(bucket: str, key: str) -> bytes:
    """Download an object and return its bytes."""
    client = get_client()
    response = client.get_object(bucket, key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def promote_to_docs(
    tenant_slug: str,
    document_id: str,
    version_id: str,
    data: bytes,
    content_type: str,
) -> tuple[str, str]:
    """Move a clean file from staging to the permanent docs bucket."""
    client = get_client()
    src_bucket = stage_bucket(tenant_slug)
    dst_bucket = docs_bucket(tenant_slug)
    key = object_key(document_id, version_id)

    client.put_object(dst_bucket, key, io.BytesIO(data), length=len(data), content_type=content_type)
    # Remove from staging
    try:
        client.remove_object(src_bucket, key)
    except S3Error:
        pass  # staging cleanup is best-effort

    return dst_bucket, key


def quarantine(
    tenant_slug: str,
    document_id: str,
    version_id: str,
    data: bytes,
) -> tuple[str, str]:
    """Move an infected file to the quarantine bucket."""
    client = get_client()
    src_bucket = stage_bucket(tenant_slug)
    dst_bucket = quarantine_bucket(tenant_slug)
    key = object_key(document_id, version_id)

    client.put_object(dst_bucket, key, io.BytesIO(data), length=len(data))
    try:
        client.remove_object(src_bucket, key)
    except S3Error:
        pass

    return dst_bucket, key


def generate_presigned_url(bucket: str, key: str, expiry_seconds: int = 300) -> str:
    """Return a time-limited presigned GET URL for a clean document version."""
    client = get_client()
    return client.presigned_get_object(bucket, key, expires=timedelta(seconds=expiry_seconds))
