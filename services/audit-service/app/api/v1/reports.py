"""
Audit summary reports for the auditor role.
Covers NIST 800-53 AU-6 (audit review, analysis, and reporting).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit_event import AuditEvent
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

_AUDITOR_ROLES = ("gxp-auditor", "gxp-admin", "gxp-platform-admin")


@router.get("/summary")
async def activity_summary(
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    user: UserContext = Depends(require_roles(*_AUDITOR_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns event counts grouped by (service, event_type, outcome) for the
    requested time window.  Defaults to the last 24 hours.
    """
    now = datetime.now(tz=timezone.utc)
    since = since or (now - timedelta(hours=24))
    until = until or now

    stmt = (
        select(
            AuditEvent.service,
            AuditEvent.event_type,
            AuditEvent.outcome,
            func.count().label("count"),
        )
        .where(AuditEvent.event_time >= since, AuditEvent.event_time < until)
        .group_by(AuditEvent.service, AuditEvent.event_type, AuditEvent.outcome)
        .order_by(func.count().desc())
    )
    if user.tenant_slug is not None:
        stmt = stmt.where(AuditEvent.tenant_slug == user.tenant_slug)

    result = await db.execute(stmt)
    rows = result.all()

    return {
        "since": since.isoformat(),
        "until": until.isoformat(),
        "tenant_slug": user.tenant_slug,
        "rows": [
            {
                "service": r.service,
                "event_type": r.event_type,
                "outcome": r.outcome,
                "count": r.count,
            }
            for r in rows
        ],
    }


@router.get("/actor-activity")
async def actor_activity(
    actor_id: str,
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    limit: int = Query(200, le=1000),
    user: UserContext = Depends(require_roles(*_AUDITOR_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Return the most recent events for a specific actor (user ID)."""
    now = datetime.now(tz=timezone.utc)
    since = since or (now - timedelta(days=30))
    until = until or now

    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.actor_id == actor_id,
            AuditEvent.event_time >= since,
            AuditEvent.event_time < until,
        )
        .order_by(AuditEvent.event_time.desc())
        .limit(limit)
    )
    if user.tenant_slug is not None:
        stmt = stmt.where(AuditEvent.tenant_slug == user.tenant_slug)

    result = await db.execute(stmt)
    events = result.scalars().all()

    return {
        "actor_id": actor_id,
        "since": since.isoformat(),
        "until": until.isoformat(),
        "count": len(events),
        "events": [
            {
                "id": str(e.id),
                "event_time": e.event_time.isoformat(),
                "service": e.service,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "outcome": e.outcome,
                "ip_address": e.ip_address,
            }
            for e in events
        ],
    }


@router.get("/failed-actions")
async def failed_actions(
    since: Optional[datetime] = Query(None),
    until: Optional[datetime] = Query(None),
    limit: int = Query(100, le=500),
    user: UserContext = Depends(require_roles(*_AUDITOR_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """Return failed (client_error, server_error) events — useful for security review."""
    now = datetime.now(tz=timezone.utc)
    since = since or (now - timedelta(hours=24))
    until = until or now

    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.outcome.in_(["client_error", "server_error"]),
            AuditEvent.event_time >= since,
            AuditEvent.event_time < until,
        )
        .order_by(AuditEvent.event_time.desc())
        .limit(limit)
    )
    if user.tenant_slug is not None:
        stmt = stmt.where(AuditEvent.tenant_slug == user.tenant_slug)

    result = await db.execute(stmt)
    events = result.scalars().all()
    return [
        {
            "id": str(e.id),
            "event_time": e.event_time.isoformat(),
            "service": e.service,
            "actor_id": e.actor_id,
            "action": e.action,
            "outcome": e.outcome,
            "ip_address": e.ip_address,
            "tenant_slug": e.tenant_slug,
        }
        for e in events
    ]
