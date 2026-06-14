"""Tests for the audit reports API endpoints."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.reports import router
from app.db.session import get_db
from gxp_shared.auth.dependencies import UserContext, get_current_user, require_roles


def _auditor(tenant_slug="dot"):
    return UserContext(user_id="aud-1", email="audit@dot.gov", roles=["gxp-auditor"], tenant_slug=tenant_slug)


def _make_test_app(user, db):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_roles("gxp-auditor", "gxp-admin", "gxp-platform-admin")] = lambda: user
    return app


@pytest.fixture
def mock_db():
    db = AsyncMock()
    return db


def _mock_result(rows):
    result = MagicMock()
    result.all.return_value = rows
    result.scalars.return_value.all.return_value = rows
    return result


# ── /summary ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_summary_returns_grouped_counts(mock_db):
    row = MagicMock()
    row.service = "app-service"
    row.event_type = "http.request"
    row.outcome = "success"
    row.count = 42
    mock_db.execute = AsyncMock(return_value=_mock_result([row]))

    app = _make_test_app(_auditor(), mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert "rows" in body
    assert body["rows"][0]["count"] == 42
    assert body["rows"][0]["service"] == "app-service"


@pytest.mark.asyncio
async def test_summary_defaults_24h_window(mock_db):
    mock_db.execute = AsyncMock(return_value=_mock_result([]))
    app = _make_test_app(_auditor(), mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "since" in body
    assert "until" in body


@pytest.mark.asyncio
async def test_summary_requires_auditor_role():
    regular_user = UserContext(user_id="u1", email="u@dot.gov", roles=["gxp-user"], tenant_slug="dot")
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: regular_user
    # Do NOT override the role guard → it will reject

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/summary")
    assert resp.status_code == 403


# ── /actor-activity ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_actor_activity_filters_by_actor(mock_db):
    event = MagicMock()
    event.id = uuid.uuid4()
    event.event_time = datetime.now(tz=timezone.utc)
    event.service = "document-service"
    event.action = "GET /api/v1/documents"
    event.resource_type = "document"
    event.resource_id = ""
    event.outcome = "success"
    event.ip_address = "10.0.0.1"
    mock_db.execute = AsyncMock(return_value=_mock_result([event]))

    app = _make_test_app(_auditor(), mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/actor-activity?actor_id=user-abc")

    assert resp.status_code == 200
    body = resp.json()
    assert body["actor_id"] == "user-abc"
    assert body["count"] == 1


@pytest.mark.asyncio
async def test_actor_activity_requires_actor_id(mock_db):
    app = _make_test_app(_auditor(), mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/actor-activity")  # missing actor_id param
    assert resp.status_code == 422


# ── /failed-actions ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_failed_actions_returns_errors(mock_db):
    err = MagicMock()
    err.id = uuid.uuid4()
    err.event_time = datetime.now(tz=timezone.utc)
    err.service = "app-service"
    err.actor_id = "u1"
    err.action = "POST /api/v1/apps"
    err.outcome = "server_error"
    err.ip_address = "10.0.0.1"
    err.tenant_slug = "dot"
    mock_db.execute = AsyncMock(return_value=_mock_result([err]))

    app = _make_test_app(_auditor(), mock_db)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/failed-actions")

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["outcome"] == "server_error"
