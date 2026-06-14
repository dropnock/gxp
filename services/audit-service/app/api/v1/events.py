"""
Audit events query API.

Accessible to users with gxp-auditor or gxp-admin roles.
All queries are scoped to the calling tenant's slug (from JWT).
Platform admins (tenant_slug=None) can query across all tenants.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.audit_event import AuditEvent
from gxp_shared.auth.dependencies import UserContext, require_roles

router = APIRouter()

_AUDITOR_ROLES = ("gxp-auditor", "gxp-admin", "gxp-platform-admin")


@router.get("")
async def list_events(
    actor_id: Optional[str] = None,
    event_type: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    outcome: Optional[str] = None,
    since: Optional[datetime] = Query(None, description="ISO-8601 timestamp (inclusive)"),
    until: Optional[datetime] = Query(None, description="ISO-8601 timestamp (exclusive)"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    user: UserContext = Depends(require_roles(*_AUDITOR_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditEvent).order_by(AuditEvent.event_time.desc())

    # Tenant scoping: regular users see only their tenant; platform admins see all
    if user.tenant_slug is not None:
        stmt = stmt.where(AuditEvent.tenant_slug == user.tenant_slug)

    if actor_id:
        stmt = stmt.where(AuditEvent.actor_id == actor_id)
    if event_type:
        stmt = stmt.where(AuditEvent.event_type == event_type)
    if resource_type:
        stmt = stmt.where(AuditEvent.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(AuditEvent.resource_id == resource_id)
    if outcome:
        stmt = stmt.where(AuditEvent.outcome == outcome)
    if since:
        stmt = stmt.where(AuditEvent.event_time >= since)
    if until:
        stmt = stmt.where(AuditEvent.event_time < until)

    stmt = stmt.offset(offset).limit(limit)
    result = await db.execute(stmt)
    events = result.scalars().all()

    return [_serialize(e) for e in events]


@router.get("/{event_id}")
async def get_event(
    event_id: UUID,
    user: UserContext = Depends(require_roles(*_AUDITOR_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(AuditEvent).where(AuditEvent.id == event_id)
    if user.tenant_slug is not None:
        stmt = stmt.where(AuditEvent.tenant_slug == user.tenant_slug)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit event not found")
    return _serialize(event)


def _serialize(e: AuditEvent) -> dict:
    return {
        "id": str(e.id),
        "event_time": e.event_time.isoformat(),
        "service": e.service,
        "event_type": e.event_type,
        "actor_id": e.actor_id,
        "actor_email": e.actor_email,
        "actor_roles": e.actor_roles,
        "resource_type": e.resource_type,
        "resource_id": e.resource_id,
        "action": e.action,
        "outcome": e.outcome,
        "ip_address": e.ip_address,
        "request_id": e.request_id,
        "tenant_slug": e.tenant_slug,
        "metadata": e.metadata_,
    }
