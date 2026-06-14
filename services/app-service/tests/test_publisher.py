"""Tests for the app publish flow."""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.builder import SchemaValidationError
from app.services.publisher import publish_app


def _make_app(pages=None):
    """Build a minimal GxpApp-like mock."""
    app = MagicMock()
    app.id = uuid.uuid4()
    app.name = "Test App"
    app.description = "desc"
    app.versions = []
    app.permissions = []
    app.pages = pages or []
    app.current_version_id = None
    app.status = "under_review"
    return app


def _make_page(route="/", name="Home", sort_order=0):
    page = MagicMock()
    page.page_id = "page-1"
    page.name = name
    page.route = route
    page.sort_order = sort_order
    page.gjs_data = {"components": []}
    page.styles = {}
    return page


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = MagicMock()
    return db


@pytest.mark.asyncio
async def test_publish_app_creates_version(mock_db):
    app = _make_app(pages=[_make_page()])
    with patch("app.services.publisher.put_schema", return_value="schemas/app/1.json"):
        version = await publish_app(app, tenant_slug="dot", publisher_id="user-1", db=mock_db)
    assert version.version_number == 1
    assert version.minio_key == "schemas/app/1.json"
    assert version.published_by == "user-1"
    assert app.status == "published"
    assert app.current_version_id == version.id
    mock_db.add.assert_called_once_with(version)


@pytest.mark.asyncio
async def test_publish_app_increments_version(mock_db):
    existing = MagicMock()
    existing.version_number = 3
    app = _make_app(pages=[_make_page()])
    app.versions = [existing]
    with patch("app.services.publisher.put_schema", return_value="schemas/app/4.json"):
        version = await publish_app(app, tenant_slug="dot", publisher_id="user-1", db=mock_db)
    assert version.version_number == 4


@pytest.mark.asyncio
async def test_publish_app_no_pages_raises(mock_db):
    app = _make_app(pages=[])
    with pytest.raises(SchemaValidationError, match="no pages"):
        await publish_app(app, tenant_slug="dot", publisher_id="user-1", db=mock_db)


@pytest.mark.asyncio
async def test_publish_app_schema_has_correct_structure(mock_db):
    page = _make_page(route="/home", name="Home Page")
    page.gjs_data = {"components": [{"type": "gxp-text", "attributes": {}, "components": []}]}
    app = _make_app(pages=[page])
    captured_schema = {}

    def capture_put_schema(slug, app_id, version, schema):
        captured_schema.update(schema)
        return "key"

    with patch("app.services.publisher.put_schema", side_effect=capture_put_schema):
        await publish_app(app, tenant_slug="dot", publisher_id="u1", db=mock_db)

    assert captured_schema["schemaVersion"] == "1.0"
    assert captured_schema["metadata"]["name"] == "Test App"
    assert len(captured_schema["pages"]) == 1
    assert captured_schema["pages"][0]["route"] == "/home"


@pytest.mark.asyncio
async def test_publish_app_permissions_included(mock_db):
    app = _make_app(pages=[_make_page()])
    p_view = MagicMock(); p_view.role = "gxp-user"; p_view.permission = "view"
    p_edit = MagicMock(); p_edit.role = "gxp-developer"; p_edit.permission = "edit"
    app.permissions = [p_view, p_edit]

    captured = {}
    def capture(slug, app_id, version, schema):
        captured.update(schema)
        return "k"

    with patch("app.services.publisher.put_schema", side_effect=capture):
        await publish_app(app, tenant_slug="dot", publisher_id="u1", db=mock_db)

    assert "gxp-user" in captured["permissions"]["viewRoles"]
    assert "gxp-developer" in captured["permissions"]["editRoles"]
