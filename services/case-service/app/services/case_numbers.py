"""
Human-readable case number generation: CASE-{YEAR}-{SEQ:05d}

Uses a per-(org_id, year) counter row with SELECT FOR UPDATE to serialise
concurrent inserts without needing a separate sequence object.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import CaseCounter


async def next_case_number(org_id: uuid.UUID, db: AsyncSession) -> str:
    now = datetime.now(tz=timezone.utc)
    year = now.year

    # Lock the row for this (org, year) combo
    result = await db.execute(
        select(CaseCounter)
        .where(CaseCounter.org_id == org_id, CaseCounter.year == year)
        .with_for_update()
    )
    counter = result.scalar_one_or_none()

    if counter is None:
        counter = CaseCounter(org_id=org_id, year=year, last_seq=1)
        db.add(counter)
    else:
        counter.last_seq += 1

    # Flush so the counter row is visible to the caller (commit happens in route)
    await db.flush()
    return f"CASE-{year}-{counter.last_seq:05d}"
