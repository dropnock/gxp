"""
Celery tasks for document processing.

scan_document:
  1. Download file bytes from MinIO staging
  2. ClamAV scan via pyclamd
  3. If clean:  promote to docs bucket → extract text (Tika) → index in OpenSearch
               → update av_status='clean', set document.current_version_id
               → emit audit event
  4. If infected: move to quarantine → update av_status='infected'
                → emit audit event (notification-service picks this up)
  5. On error:  update av_status='error', log; leave in staging for retry

Uses synchronous SQLAlchemy (psycopg2) since Celery runs in sync mode.
The DATABASE_URL is rewritten from asyncpg → psycopg2 for the worker.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

import pyclamd
import sqlalchemy as sa
from sqlalchemy import create_engine, update

from app import storage as minio
from app import search as opensearch
from app.config import settings
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Rewrite async driver URL for synchronous use in Celery tasks
_SYNC_DB_URL = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
).replace(
    "postgresql+asyncio://", "postgresql+psycopg2://"
)
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


def _get_clamav() -> pyclamd.ClamdNetworkSocket:
    return pyclamd.ClamdNetworkSocket(
        host=settings.clamav_host,
        port=settings.clamav_port,
        timeout=120,
    )


def _emit_audit(event_type: str, document_id: str, version_id: str, tenant_slug: str, outcome: str, metadata: dict) -> None:
    """Fire-and-forget audit emission from sync Celery task."""
    from gxp_shared.audit.emitter import emit_audit_event
    try:
        asyncio.run(
            emit_audit_event(
                redis_url=settings.valkey_url,
                service="document-service",
                event_type=event_type,
                actor_id="system",
                resource_type="document",
                resource_id=document_id,
                action=event_type,
                outcome=outcome,
                metadata={
                    "version_id": version_id,
                    "tenant_slug": tenant_slug,
                    **metadata,
                },
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("Audit emit failed in worker: %s", exc)


@celery_app.task(name="app.worker.tasks.scan_document", bind=True, max_retries=3, default_retry_delay=60)
def scan_document(
    self,
    version_id: str,
    document_id: str,
    tenant_slug: str,
    mime_type: str,
) -> None:
    """AV scan a newly uploaded document version and promote or quarantine it."""
    with _engine.begin() as conn:
        # Mark as scanning
        conn.execute(
            sa.text(f'SET search_path TO "t_{tenant_slug}", public')
        )
        conn.execute(
            sa.text(
                "UPDATE document_versions SET av_status = 'scanning' WHERE id = :id"
            ),
            {"id": version_id},
        )

    try:
        # 1. Download from staging
        src_bucket = minio.stage_bucket(tenant_slug)
        key = minio.object_key(document_id, version_id)
        data = minio.download_bytes(src_bucket, key)

        # 2. ClamAV scan
        cd = _get_clamav()
        scan_result = cd.scan_stream(data)

        now = datetime.now(tz=timezone.utc)

        if scan_result is None:
            # Clean — promote to docs bucket
            dst_bucket, dst_key = minio.promote_to_docs(tenant_slug, document_id, version_id, data, mime_type)
            checksum = minio.compute_sha256(data)

            # Extract text and index in OpenSearch
            content_text = opensearch.extract_text(data, mime_type)

            with _engine.begin() as conn:
                conn.execute(sa.text(f'SET search_path TO "t_{tenant_slug}", public'))

                # Update version: clean, new bucket/key
                conn.execute(
                    sa.text("""
                        UPDATE document_versions
                        SET av_status = 'clean',
                            av_scanned_at = :scanned_at,
                            minio_bucket = :bucket,
                            minio_key = :key,
                            checksum_sha256 = :checksum
                        WHERE id = :id
                    """),
                    {"scanned_at": now, "bucket": dst_bucket, "key": dst_key, "checksum": checksum, "id": version_id},
                )

                # Promote: set document.current_version_id and update updated_at
                conn.execute(
                    sa.text("""
                        UPDATE documents
                        SET current_version_id = :vid,
                            updated_at = :now
                        WHERE id = :did
                    """),
                    {"vid": version_id, "now": now, "did": document_id},
                )

                # Fetch doc metadata for OpenSearch
                row = conn.execute(
                    sa.text("SELECT name, description, tags, created_by, created_at FROM documents WHERE id = :id"),
                    {"id": document_id},
                ).fetchone()

            if row:
                opensearch.index_document(
                    tenant_slug=tenant_slug,
                    document_id=document_id,
                    version_id=version_id,
                    name=row.name,
                    description=row.description or "",
                    tags=row.tags or [],
                    mime_type=mime_type,
                    uploaded_by=row.created_by,
                    created_at=row.created_at.isoformat() if row.created_at else "",
                    content_text=content_text,
                )

            _emit_audit("document.uploaded", document_id, version_id, tenant_slug, "success", {"av": "clean"})
            logger.info("Document %s/%s: clean, promoted to %s", document_id, version_id, dst_bucket)

        else:
            # Infected
            virus_name = list(scan_result.values())[0][1] if scan_result else "unknown"
            minio.quarantine(tenant_slug, document_id, version_id, data)

            with _engine.begin() as conn:
                conn.execute(sa.text(f'SET search_path TO "t_{tenant_slug}", public'))
                conn.execute(
                    sa.text("""
                        UPDATE document_versions
                        SET av_status = 'infected',
                            av_scanned_at = :scanned_at
                        WHERE id = :id
                    """),
                    {"scanned_at": now, "id": version_id},
                )

            _emit_audit(
                "document.quarantined", document_id, version_id, tenant_slug,
                "blocked", {"virus": virus_name}
            )
            logger.warning("Document %s/%s: INFECTED (%s), quarantined", document_id, version_id, virus_name)

    except Exception as exc:
        logger.error("Scan task failed for %s/%s: %s", document_id, version_id, exc)
        try:
            with _engine.begin() as conn:
                conn.execute(sa.text(f'SET search_path TO "t_{tenant_slug}", public'))
                conn.execute(
                    sa.text("UPDATE document_versions SET av_status = 'error' WHERE id = :id"),
                    {"id": version_id},
                )
        except Exception:
            pass
        raise self.retry(exc=exc)
