"""Tests for the audit event stream consumer."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.consumers.audit_consumer import (
    BATCH_SIZE,
    CONSUMER_GROUP,
    RETRY_DELAY,
    STREAM_KEY,
    _process_batch,
)


def _make_entry(entry_id=b"1-0", **fields):
    """Build a Redis Streams entry in bytes format."""
    defaults = {
        b"service": b"app-service",
        b"event_type": b"http.request",
        b"actor_id": b"user-1",
        b"actor_email": b"u@dot.gov",
        b"actor_roles": json.dumps(["gxp-developer"]).encode(),
        b"resource_type": b"app",
        b"resource_id": b"app-uuid",
        b"action": b"POST /api/v1/apps",
        b"outcome": b"success",
        b"ip_address": b"10.0.0.1",
        b"request_id": b"req-123",
        b"event_time": b"1700000000.0",
        b"metadata": json.dumps({"tenant_slug": "dot", "http_status": 201}).encode(),
    }
    defaults.update({k.encode() if isinstance(k, str) else k: v.encode() if isinstance(v, str) else v
                     for k, v in fields.items()})
    return (entry_id, defaults)


def _make_session_ctx():
    """Build a mock async-context-manager session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=session)
    ctx.__aexit__ = AsyncMock(return_value=False)
    return ctx, session


def _patch_pg_insert():
    """Patch pg_insert so SQLAlchemy doesn't compile a real INSERT statement."""
    mock_stmt = MagicMock()
    mock_stmt.values.return_value.on_conflict_do_nothing.return_value = mock_stmt
    return patch("app.consumers.audit_consumer.pg_insert", return_value=mock_stmt)


@pytest.mark.asyncio
async def test_process_batch_returns_all_ids():
    ctx, session = _make_session_ctx()
    entries = [_make_entry(b"1-0"), _make_entry(b"2-0"), _make_entry(b"3-0")]
    with patch("app.consumers.audit_consumer.AsyncSessionLocal", return_value=ctx), _patch_pg_insert():
        ids = await _process_batch(entries)
    assert ids == [b"1-0", b"2-0", b"3-0"]
    session.execute.assert_awaited_once()
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_batch_acks_malformed_entry():
    """Malformed entries must still be ACKed to avoid infinite retry (AU-5)."""
    ctx, session = _make_session_ctx()
    bad_entry = (b"bad-1", {b"totally": b"wrong"})
    good_entry = _make_entry(b"good-1")
    with patch("app.consumers.audit_consumer.AsyncSessionLocal", return_value=ctx), _patch_pg_insert():
        ids = await _process_batch([bad_entry, good_entry])
    assert b"bad-1" in ids
    assert b"good-1" in ids


@pytest.mark.asyncio
async def test_process_batch_empty_entries_does_not_hit_db():
    ctx, session = _make_session_ctx()
    with patch("app.consumers.audit_consumer.AsyncSessionLocal", return_value=ctx), _patch_pg_insert():
        ids = await _process_batch([])
    assert ids == []
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_batch_handles_string_format_fields():
    """Consumer must handle both bytes and string keys (Redis client version differences)."""
    ctx, session = _make_session_ctx()
    str_entry = ("1-0", {
        "service": "workflow-service",
        "event_type": "http.request",
        "actor_id": "u1",
        "actor_email": "",
        "actor_roles": "[]",
        "resource_type": "workflow",
        "resource_id": "",
        "action": "GET /api/v1/workflow/definitions",
        "outcome": "success",
        "ip_address": "",
        "request_id": "",
        "event_time": "1700000001.0",
        "metadata": '{"tenant_slug": "dot"}',
    })
    with patch("app.consumers.audit_consumer.AsyncSessionLocal", return_value=ctx), _patch_pg_insert():
        ids = await _process_batch([str_entry])
    assert "1-0" in ids


@pytest.mark.asyncio
async def test_process_batch_invalid_event_time_defaults_to_now():
    """If event_time is unparseable, the consumer defaults to now() without crashing."""
    ctx, session = _make_session_ctx()
    entry = _make_entry(b"1-0", event_time=b"not-a-timestamp")
    with patch("app.consumers.audit_consumer.AsyncSessionLocal", return_value=ctx), _patch_pg_insert():
        ids = await _process_batch([entry])
    assert b"1-0" in ids
    session.commit.assert_awaited_once()


def test_consumer_constants():
    assert STREAM_KEY == "audit:events"
    assert CONSUMER_GROUP == "audit-service"
    assert BATCH_SIZE == 100
    assert RETRY_DELAY == 5
