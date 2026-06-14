"""Tests for cross-tenant grant enforcement."""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException

from gxp_shared.auth import cross_tenant as ct_module
from gxp_shared.auth.cross_tenant import _cache_key, assert_cross_tenant_grant


RESOURCE_ID = uuid.uuid4()


def _patch_redis(cached_value: str | None):
    """Return a mock Redis client with a pre-set cache value."""
    r = AsyncMock()
    r.get = AsyncMock(return_value=cached_value)
    r.setex = AsyncMock()
    return r


# ── cache hit ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_same_tenant_always_allowed():
    """Same requesting/granting tenant bypasses all checks."""
    with patch("gxp_shared.auth.cross_tenant.aioredis") as mock_aio:
        mock_aio.from_url.return_value = AsyncMock()
        await assert_cross_tenant_grant(
            requesting_tenant="dot",
            granting_tenant="dot",
            resource_type="document",
            resource_id=RESOURCE_ID,
            required_permission="read",
            tenant_service_db_url="postgresql+asyncpg://x",
            valkey_url="redis://localhost",
        )
        # Redis must NOT have been called at all
        mock_aio.from_url.assert_not_called()


@pytest.mark.asyncio
async def test_cache_hit_granted():
    r = _patch_redis("1")
    with patch("gxp_shared.auth.cross_tenant.aioredis") as mock_aio:
        mock_aio.from_url.return_value = r
        # Should not raise
        await assert_cross_tenant_grant(
            requesting_tenant="dot",
            granting_tenant="doh",
            resource_type="document",
            resource_id=RESOURCE_ID,
            required_permission="read",
            tenant_service_db_url="postgresql+asyncpg://x",
            valkey_url="redis://localhost",
        )
        r.get.assert_awaited_once()


@pytest.mark.asyncio
async def test_cache_hit_denied():
    r = _patch_redis("0")
    with patch("gxp_shared.auth.cross_tenant.aioredis") as mock_aio:
        mock_aio.from_url.return_value = r
        with pytest.raises(HTTPException) as exc:
            await assert_cross_tenant_grant(
                requesting_tenant="dot",
                granting_tenant="doh",
                resource_type="document",
                resource_id=RESOURCE_ID,
                required_permission="read",
                tenant_service_db_url="postgresql+asyncpg://x",
                valkey_url="redis://localhost",
            )
        assert exc.value.status_code == 403


# ── cache miss → DB check ─────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cache_miss_db_granted():
    r = _patch_redis(None)  # cache miss
    with patch("gxp_shared.auth.cross_tenant.aioredis") as mock_aio, \
         patch("gxp_shared.auth.cross_tenant._check_db", new=AsyncMock(return_value=True)):
        mock_aio.from_url.return_value = r
        await assert_cross_tenant_grant(
            requesting_tenant="dot",
            granting_tenant="doh",
            resource_type="app",
            resource_id=RESOURCE_ID,
            required_permission="read",
            tenant_service_db_url="postgresql+asyncpg://x",
            valkey_url="redis://localhost",
        )
        # Should cache the positive result
        r.setex.assert_awaited_once()
        args = r.setex.call_args.args
        assert args[2] == "1"


@pytest.mark.asyncio
async def test_cache_miss_db_denied():
    r = _patch_redis(None)
    with patch("gxp_shared.auth.cross_tenant.aioredis") as mock_aio, \
         patch("gxp_shared.auth.cross_tenant._check_db", new=AsyncMock(return_value=False)):
        mock_aio.from_url.return_value = r
        with pytest.raises(HTTPException) as exc:
            await assert_cross_tenant_grant(
                requesting_tenant="dot",
                granting_tenant="doh",
                resource_type="app",
                resource_id=RESOURCE_ID,
                required_permission="read",
                tenant_service_db_url="postgresql+asyncpg://x",
                valkey_url="redis://localhost",
            )
        assert exc.value.status_code == 403
        # Should cache the negative result
        args = r.setex.call_args.args
        assert args[2] == "0"


# ── cache key format ──────────────────────────────────────────────────────────

def test_cache_key_format():
    rid = uuid.UUID("00000000-0000-0000-0000-000000000001")
    key = _cache_key("dot", "doh", "document", rid, "read")
    assert key == f"gxp:grant:dot:doh:document:{rid}:read"
