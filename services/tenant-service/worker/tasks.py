"""
Tenant-service Celery tasks.

expire_grants — beat task, runs every 5 minutes.
  Finds all approved grants where expires_at < now() and flips them to 'expired'.
  Also invalidates the short-lived Valkey grant cache so access is denied immediately.
"""
from __future__ import annotations

import asyncio
import logging

import redis as sync_redis
from sqlalchemy import create_engine, text, update
from sqlalchemy.orm import Session

from app.config import settings
from worker.celery_app import celery_app

logger = logging.getLogger(__name__)

# Sync DB URL for Celery workers (psycopg2 instead of asyncpg)
_SYNC_DB_URL = settings.database_url.replace(
    "postgresql+asyncpg://", "postgresql+psycopg2://"
)
_engine = create_engine(_SYNC_DB_URL, pool_pre_ping=True)


@celery_app.task(name="worker.tasks.expire_grants", bind=True, max_retries=3)
def expire_grants(self):
    """
    Transition approved cross-tenant grants past their expires_at to 'expired'.
    Invalidates Valkey cache entries for each expired grant so revocation takes
    effect within seconds even for in-flight requests.
    """
    try:
        with Session(_engine) as session:
            # Fetch grants to expire (need IDs for cache invalidation)
            rows = session.execute(
                text("""
                    SELECT g.id,
                           req.slug AS requesting_slug,
                           grt.slug AS granting_slug,
                           g.resource_type,
                           g.resource_id,
                           g.permissions
                    FROM platform.cross_tenant_grants g
                    JOIN platform.tenants req ON req.id = g.requesting_tenant_id
                    JOIN platform.tenants grt ON grt.id = g.granting_tenant_id
                    WHERE g.status = 'approved'
                      AND g.expires_at IS NOT NULL
                      AND g.expires_at <= now()
                """)
            ).fetchall()

            if not rows:
                return {"expired": 0}

            ids = [str(r.id) for r in rows]
            session.execute(
                text("""
                    UPDATE platform.cross_tenant_grants
                    SET status = 'expired'
                    WHERE id = ANY(:ids::uuid[])
                """),
                {"ids": ids},
            )
            session.commit()

        # Invalidate Valkey cache so the denial takes effect immediately
        _invalidate_cache(rows)

        logger.info("Expired %d cross-tenant grants", len(rows))
        return {"expired": len(rows)}

    except Exception as exc:
        logger.exception("expire_grants task failed: %s", exc)
        raise self.retry(exc=exc, countdown=30)


def _invalidate_cache(rows) -> None:
    r = sync_redis.from_url(settings.valkey_url, decode_responses=True)
    pipe = r.pipeline()
    for row in rows:
        for perm in (row.permissions or []):
            key = (
                f"gxp:grant:{row.requesting_slug}:{row.granting_slug}"
                f":{row.resource_type}:{row.resource_id}:{perm}"
            )
            pipe.delete(key)
    pipe.execute()
    r.close()


# ── Audit emit helper (async) ──────────────────────────────────────────────────

def _emit_audit(event_type: str, payload: dict) -> None:
    async def _inner():
        from gxp_shared.audit.emitter import emit_audit_event
        await emit_audit_event(
            valkey_url=settings.valkey_url,
            service="tenant-service",
            event_type=event_type,
            payload=payload,
        )
    asyncio.run(_inner())
