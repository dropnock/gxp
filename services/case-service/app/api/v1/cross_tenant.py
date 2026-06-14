"""
Cross-tenant read access for cases.

GET /api/v1/cases/cross-tenant/{tenant_slug}/{case_id}
  - Validates a cross-tenant grant
  - Returns the case from the granting tenant's schema (read-only)
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, text

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.models.case import Case, CaseParticipant, CaseTimelineEvent
from gxp_shared.auth.cross_tenant import assert_cross_tenant_grant
from gxp_shared.auth.dependencies import UserContext, get_current_user

router = APIRouter()


@router.get("/cross-tenant/{tenant_slug}/{case_id}")
async def get_cross_tenant_case(
    tenant_slug: str,
    case_id: UUID,
    user: UserContext = Depends(get_current_user),
):
    """
    Read a case from a different tenant.
    Requires an approved cross-tenant grant with 'read' permission on this case.
    """
    requesting = user.tenant_slug
    if not requesting:
        raise HTTPException(status_code=403, detail="Tenant context required")
    if requesting == tenant_slug:
        raise HTTPException(status_code=400, detail="Use the standard endpoint for same-tenant access")

    await assert_cross_tenant_grant(
        requesting_tenant=requesting,
        granting_tenant=tenant_slug,
        resource_type="case",
        resource_id=case_id,
        required_permission="read",
        tenant_service_db_url=settings.tenant_service_db_url,
        valkey_url=settings.valkey_url,
    )

    async with AsyncSessionLocal() as db:
        await db.execute(text(f'SET search_path TO "t_{tenant_slug}", public'))

        result = await db.execute(select(Case).where(Case.id == case_id))
        case = result.scalar_one_or_none()
        if not case:
            raise HTTPException(status_code=404, detail="Case not found in granting tenant")

        participants_result = await db.execute(
            select(CaseParticipant).where(CaseParticipant.case_id == case_id)
        )
        participants = participants_result.scalars().all()

        timeline_result = await db.execute(
            select(CaseTimelineEvent)
            .where(CaseTimelineEvent.case_id == case_id)
            .order_by(CaseTimelineEvent.occurred_at)
        )
        timeline = timeline_result.scalars().all()

    return {
        "id": str(case.id),
        "case_number": case.case_number,
        "title": case.title,
        "status": case.status,
        "priority": case.priority,
        "assigned_to": str(case.assigned_to) if case.assigned_to else None,
        "created_at": case.created_at.isoformat(),
        "tenant_slug": tenant_slug,
        "participants": [
            {"user_id": str(p.user_id), "role": p.role} for p in participants
        ],
        "timeline": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "actor_id": str(e.actor_id),
                "occurred_at": e.occurred_at.isoformat(),
                "metadata": e.metadata_,
            }
            for e in timeline
        ],
    }
