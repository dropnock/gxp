"""Tests for the audit event emitter."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from gxp_shared.audit import emitter as emitter_module
from gxp_shared.audit.emitter import emit_audit_event


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Reset the module-level _redis singleton between tests."""
    emitter_module._redis = None
    yield
    emitter_module._redis = None


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.xadd = AsyncMock()
    with patch.object(emitter_module, "_get_redis", return_value=r):
        yield r


@pytest.mark.asyncio
async def test_emit_audit_event_sends_to_stream(mock_redis):
    await emit_audit_event(
        redis_url="redis://localhost:6379/0",
        service="app-service",
        event_type="http.request",
        actor_id="user-abc",
        actor_email="u@dot.gov",
        actor_roles=["gxp-developer"],
        resource_type="app",
        resource_id="app-uuid",
        action="POST /api/v1/apps",
        outcome="success",
        ip_address="10.0.0.1",
        request_id="req-123",
        metadata={"http_status": 201},
    )
    mock_redis.xadd.assert_awaited_once()
    stream_key, payload = mock_redis.xadd.call_args.args
    assert stream_key == "audit:events"
    assert payload["service"] == "app-service"
    assert payload["event_type"] == "http.request"
    assert payload["actor_id"] == "user-abc"
    assert payload["outcome"] == "success"
    assert json.loads(payload["actor_roles"]) == ["gxp-developer"]
    assert json.loads(payload["metadata"]) == {"http_status": 201}


@pytest.mark.asyncio
async def test_emit_audit_event_defaults(mock_redis):
    await emit_audit_event(
        redis_url="redis://localhost:6379/0",
        service="audit-service",
        event_type="http.request",
        actor_id="",
        action="GET /health",
        outcome="success",
    )
    _, payload = mock_redis.xadd.call_args.args
    assert payload["actor_email"] == ""
    assert json.loads(payload["actor_roles"]) == []
    assert json.loads(payload["metadata"]) == {}
    assert payload["resource_type"] == ""
    assert payload["resource_id"] == ""
    assert "event_time" in payload
