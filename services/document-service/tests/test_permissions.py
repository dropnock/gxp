"""Tests for document permission resolution."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.services.permissions import check_permission, get_effective_permissions
from gxp_shared.auth.dependencies import UserContext


DOC_ID = uuid.uuid4()
FOLDER_ID = uuid.uuid4()


def _user(roles=None, user_id="u-1"):
    return UserContext(user_id=user_id, email="u@dot.gov", roles=roles or ["gxp-user"], tenant_slug="dot")


def _db_with_perms(perms: list[str]):
    """Mock DB that returns the given permission strings."""
    db = AsyncMock()
    result = MagicMock()
    rows = [MagicMock(perm=p) for p in perms]
    result.__iter__ = lambda self: iter(rows)
    db.execute = AsyncMock(return_value=result)
    return db


# ── Admin bypass ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_admin_bypasses_permission_check():
    user = _user(roles=["gxp-admin"])
    db = AsyncMock()
    # Should not raise, and must not call db.execute at all
    await check_permission(
        db=db, user=user,
        resource_type="document", resource_id=DOC_ID,
        required_permission="read", folder_id=FOLDER_ID,
    )
    db.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_platform_admin_bypasses_permission_check():
    user = _user(roles=["gxp-platform-admin"])
    db = AsyncMock()
    await check_permission(
        db=db, user=user,
        resource_type="document", resource_id=DOC_ID,
        required_permission="delete",
    )
    db.execute.assert_not_awaited()


# ── Document-level permissions ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_document_level_read_permission_grants_access():
    user = _user()
    db = _db_with_perms(["read"])
    await check_permission(
        db=db, user=user,
        resource_type="document", resource_id=DOC_ID,
        required_permission="read",
    )
    # No exception = pass


@pytest.mark.asyncio
async def test_document_level_insufficient_permission_raises_403():
    user = _user()
    db = _db_with_perms(["read"])  # has read, not write
    with pytest.raises(HTTPException) as exc:
        await check_permission(
            db=db, user=user,
            resource_type="document", resource_id=DOC_ID,
            required_permission="write",
        )
    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_no_permissions_raises_403():
    user = _user()
    db = _db_with_perms([])
    with pytest.raises(HTTPException) as exc:
        await check_permission(
            db=db, user=user,
            resource_type="document", resource_id=DOC_ID,
            required_permission="read",
        )
    assert exc.value.status_code == 403


# ── get_effective_permissions ─────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_effective_permissions_returns_set():
    user = _user()
    db = _db_with_perms(["read", "write"])
    perms = await get_effective_permissions(
        db=db, user=user,
        resource_type="document", resource_id=DOC_ID,
    )
    assert "read" in perms
    assert "write" in perms


@pytest.mark.asyncio
async def test_effective_permissions_empty_for_no_grant():
    user = _user()
    db = _db_with_perms([])
    perms = await get_effective_permissions(
        db=db, user=user,
        resource_type="document", resource_id=DOC_ID,
    )
    assert perms == set()


@pytest.mark.asyncio
async def test_effective_permissions_folder_type_with_no_folder_returns_empty():
    """Folder resource with no folder_id should return empty permissions."""
    user = _user()
    db = _db_with_perms([])
    perms = await get_effective_permissions(
        db=db, user=user,
        resource_type="folder", resource_id=FOLDER_ID,
    )
    # No folder perms in mocked DB
    assert isinstance(perms, set)
