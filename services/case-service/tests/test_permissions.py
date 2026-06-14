"""Tests for case access control."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.permissions import assert_can_read, assert_can_write, get_case_or_404
from gxp_shared.auth.dependencies import UserContext


CASE_ID = uuid.uuid4()


def _user(roles=None, user_id="u-1"):
    return UserContext(user_id=user_id, email="u@dot.gov", roles=roles or [], tenant_slug="dot")


def _participant(role="owner"):
    p = MagicMock()
    p.role = role
    return p


def _mock_db_with_participant(participant):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = participant
    db.execute = AsyncMock(return_value=result)
    return db


def _mock_case():
    c = MagicMock()
    c.id = CASE_ID
    return c


# ── get_case_or_404 ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_case_or_404_returns_case():
    case = _mock_case()
    db = AsyncMock()
    db.get = AsyncMock(return_value=case)
    result = await get_case_or_404(CASE_ID, db)
    assert result is case


@pytest.mark.asyncio
async def test_get_case_or_404_raises_404():
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    with pytest.raises(HTTPException) as exc:
        await get_case_or_404(CASE_ID, db)
    assert exc.value.status_code == 404


# ── assert_can_read ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_read_without_participation():
    user = _user(roles=["gxp-admin"])
    db = AsyncMock()
    result = await assert_can_read(_mock_case(), user, db)
    assert result is None  # admin bypass returns None
    db.execute.assert_not_awaited()


@pytest.mark.parametrize("role", ["owner", "collaborator", "observer", "subject"])
@pytest.mark.asyncio
async def test_participant_can_read(role):
    user = _user()
    db = _mock_db_with_participant(_participant(role))
    result = await assert_can_read(_mock_case(), user, db)
    assert result.role == role


@pytest.mark.asyncio
async def test_non_participant_cannot_read():
    user = _user()
    db = _mock_db_with_participant(None)
    with pytest.raises(HTTPException) as exc:
        await assert_can_read(_mock_case(), user, db)
    assert exc.value.status_code == 403


# ── assert_can_write ──────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_can_write():
    user = _user(roles=["gxp-admin"])
    db = AsyncMock()
    result = await assert_can_write(_mock_case(), user, db)
    assert result is None


@pytest.mark.parametrize("role", ["owner", "collaborator"])
@pytest.mark.asyncio
async def test_editor_roles_can_write(role):
    user = _user()
    db = _mock_db_with_participant(_participant(role))
    result = await assert_can_write(_mock_case(), user, db)
    assert result.role == role


@pytest.mark.parametrize("role", ["observer", "subject"])
@pytest.mark.asyncio
async def test_read_only_roles_cannot_write(role):
    user = _user()
    db = _mock_db_with_participant(_participant(role))
    with pytest.raises(HTTPException) as exc:
        await assert_can_write(_mock_case(), user, db)
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_non_participant_cannot_write():
    user = _user()
    db = _mock_db_with_participant(None)
    with pytest.raises(HTTPException) as exc:
        await assert_can_write(_mock_case(), user, db)
    assert exc.value.status_code == 403
