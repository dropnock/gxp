"""Tests for case number generation."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.case_numbers import next_case_number


ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _mock_db(counter_row=None):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = counter_row
    db.execute = AsyncMock(return_value=result)
    db.add = MagicMock()
    db.flush = AsyncMock()
    return db


@pytest.mark.asyncio
async def test_first_case_number_is_00001():
    db = _mock_db(counter_row=None)  # no existing counter
    number = await next_case_number(ORG_ID, db)
    year = datetime.now(tz=timezone.utc).year
    assert number == f"CASE-{year}-00001"
    db.add.assert_called_once()


@pytest.mark.asyncio
async def test_subsequent_case_number_increments():
    existing = MagicMock()
    existing.last_seq = 41
    db = _mock_db(counter_row=existing)

    number = await next_case_number(ORG_ID, db)
    year = datetime.now(tz=timezone.utc).year
    assert number == f"CASE-{year}-00042"
    assert existing.last_seq == 42


@pytest.mark.asyncio
async def test_case_number_zero_pads_to_5_digits():
    existing = MagicMock()
    existing.last_seq = 9999
    db = _mock_db(counter_row=existing)
    number = await next_case_number(ORG_ID, db)
    assert number.endswith("-10000")


@pytest.mark.asyncio
async def test_flush_called_after_update():
    db = _mock_db(counter_row=None)
    await next_case_number(ORG_ID, db)
    db.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_different_orgs_independent():
    """Each org gets its own counter row (DB query is org-scoped)."""
    org_a = uuid.uuid4()
    org_b = uuid.uuid4()
    db_a = _mock_db(counter_row=None)
    db_b = _mock_db(counter_row=None)

    num_a = await next_case_number(org_a, db_a)
    num_b = await next_case_number(org_b, db_b)
    year = datetime.now(tz=timezone.utc).year
    assert num_a == f"CASE-{year}-00001"
    assert num_b == f"CASE-{year}-00001"
