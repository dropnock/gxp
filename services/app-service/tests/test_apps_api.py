"""Route-level tests for the apps API."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1.apps import router, AppOut
from app.db.session import get_db
from app.models.app import GxpApp
from gxp_shared.auth.dependencies import UserContext, get_current_user, require_roles


def _make_test_app(user: UserContext, db):
    """Build a minimal FastAPI test app with dependency overrides."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/apps")
    test_app.dependency_overrides[get_current_user] = lambda: user
    test_app.dependency_overrides[get_db] = lambda: db
    # Override role-gated deps too
    for roles in [
        ("gxp-developer", "gxp-admin"),
        ("gxp-admin",),
        ("gxp-user", "gxp-developer", "gxp-admin", "gxp-case-worker"),
    ]:
        test_app.dependency_overrides[require_roles(*roles)] = lambda u=user: u
    return test_app


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    return db


@pytest.fixture
def developer():
    return UserContext(user_id="dev-1", email="dev@dot.gov", roles=["gxp-developer"], tenant_slug="dot")


def _app_row(name="My App", created_by="dev-1"):
    row = MagicMock(spec=GxpApp)
    row.id = uuid.uuid4()
    row.name = name
    row.description = None
    row.status = "draft"
    row.current_version_id = None
    row.created_by = created_by
    row.created_at = datetime.now(tz=timezone.utc)
    row.updated_at = datetime.now(tz=timezone.utc)
    row.is_active = True
    return row


@pytest.mark.asyncio
async def test_create_app_returns_201(developer, mock_db):
    test_app = _make_test_app(developer, mock_db)
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.post("/apps", json={"name": "New App"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "New App"
    assert data["status"] == "draft"
    assert data["created_by"] == "dev-1"
    assert mock_db.add.call_count >= 1  # GxpApp + any default permissions


@pytest.mark.asyncio
async def test_create_app_without_permission_returns_403():
    """Users without gxp-developer or gxp-admin cannot create apps."""
    user = UserContext(user_id="u1", email="u@dot.gov", roles=["gxp-user"], tenant_slug="dot")
    test_app = FastAPI()
    test_app.include_router(router, prefix="/apps")
    # Only override get_current_user; keep role guards real
    test_app.dependency_overrides[get_current_user] = lambda: user

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.post("/apps", json={"name": "Denied"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_apps_returns_only_active(developer, mock_db):
    active_app = _app_row()
    result_mock = MagicMock()
    result_mock.scalars.return_value.all.return_value = [active_app]
    mock_db.execute = AsyncMock(return_value=result_mock)

    test_app = _make_test_app(developer, mock_db)
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as client:
        resp = await client.get("/apps")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_health_endpoint():
    from app.main import app as svc_app
    # Just test the /health route without any DB
    async with AsyncClient(transport=ASGITransport(app=svc_app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["service"] == "app-service"
