"""
Case access control.

Participants with 'owner' or 'collaborator' role may read and write.
Participants with 'observer' role may only read.
Non-participants are denied entirely.
gxp-admin bypasses participant checks.
"""
from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case, CaseParticipant
from gxp_shared.auth.dependencies import UserContext

_EDITOR_ROLES = {"owner", "collaborator"}
_ALL_ROLES = {"owner", "collaborator", "observer", "subject"}


async def get_case_or_404(
    case_id: uuid.UUID,
    db: AsyncSession,
) -> Case:
    case = await db.get(Case, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case


async def assert_can_read(
    case: Case,
    user: UserContext,
    db: AsyncSession,
) -> CaseParticipant | None:
    if "gxp-admin" in user.roles:
        return None
    participant = await _get_participant(case.id, user.user_id, db)
    if not participant:
        raise HTTPException(status_code=403, detail="Not a participant on this case")
    return participant


async def assert_can_write(
    case: Case,
    user: UserContext,
    db: AsyncSession,
) -> CaseParticipant | None:
    if "gxp-admin" in user.roles:
        return None
    participant = await assert_can_read(case, user, db)
    if participant and participant.role not in _EDITOR_ROLES:
        raise HTTPException(status_code=403, detail="Observer-only access — cannot modify this case")
    return participant


async def _get_participant(
    case_id: uuid.UUID,
    user_id: str,
    db: AsyncSession,
) -> CaseParticipant | None:
    result = await db.execute(
        select(CaseParticipant).where(
            CaseParticipant.case_id == case_id,
            CaseParticipant.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()
