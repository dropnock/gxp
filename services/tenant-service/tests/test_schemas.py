"""Tests for tenant-service Pydantic schemas."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.tenant import (
    CatalogTemplateCreate,
    CrossTenantGrantCreate,
    TenantCreate,
    TenantUpdate,
)


# ── TenantCreate ──────────────────────────────────────────────────────────────

@pytest.mark.parametrize("slug", [
    "dot",
    "dept_of_health",
    "abc123",
])
def test_valid_slug(slug):
    t = TenantCreate(slug=slug, name="Test Agency")
    assert t.slug == slug


@pytest.mark.parametrize("slug", [
    "ab",            # too short (< 3 chars)
    "A",             # uppercase
    "dot!",          # invalid character
    "my-agency",     # hyphens not allowed (only alphanumeric + underscore)
    "a" * 64,        # too long
])
def test_invalid_slug_raises(slug):
    with pytest.raises(ValidationError):
        TenantCreate(slug=slug, name="Test Agency")


def test_tenant_name_required():
    with pytest.raises(ValidationError):
        TenantCreate(slug="dot")


def test_tenant_name_min_length():
    with pytest.raises(ValidationError):
        TenantCreate(slug="dot", name="x")  # < 2 chars


def test_tenant_name_max_length():
    with pytest.raises(ValidationError):
        TenantCreate(slug="dot", name="x" * 201)


# ── TenantUpdate ──────────────────────────────────────────────────────────────

def test_tenant_update_all_optional():
    u = TenantUpdate()
    assert u.name is None
    assert u.status is None


def test_tenant_update_valid_status():
    u = TenantUpdate(status="suspended")
    assert u.status == "suspended"


def test_tenant_update_invalid_status():
    with pytest.raises(ValidationError):
        TenantUpdate(status="deprovisioning")  # not in allowed Literal


# ── CrossTenantGrantCreate ────────────────────────────────────────────────────

def test_cross_tenant_grant_create_valid():
    g = CrossTenantGrantCreate(
        granting_tenant_slug="doh",
        resource_type="document",
        resource_id=uuid.uuid4(),
        permissions=["read"],
    )
    assert g.granting_tenant_slug == "doh"
    assert g.permissions == ["read"]


@pytest.mark.parametrize("resource_type", ["document", "app", "workflow_definition", "case"])
def test_cross_tenant_grant_valid_resource_types(resource_type):
    CrossTenantGrantCreate(
        granting_tenant_slug="doh",
        resource_type=resource_type,
        resource_id=uuid.uuid4(),
        permissions=["read"],
    )


def test_cross_tenant_grant_invalid_resource_type():
    with pytest.raises(ValidationError):
        CrossTenantGrantCreate(
            granting_tenant_slug="doh",
            resource_type="folder",  # not in allowed set
            resource_id=uuid.uuid4(),
            permissions=["read"],
        )


def test_cross_tenant_grant_invalid_permission():
    with pytest.raises(ValidationError):
        CrossTenantGrantCreate(
            granting_tenant_slug="doh",
            resource_type="document",
            resource_id=uuid.uuid4(),
            permissions=["delete"],  # not in allowed set
        )


def test_cross_tenant_grant_with_expiry():
    expires = datetime.now(tz=timezone.utc)
    g = CrossTenantGrantCreate(
        granting_tenant_slug="doh",
        resource_type="document",
        resource_id=uuid.uuid4(),
        permissions=["read", "write"],
        expires_at=expires,
    )
    assert g.expires_at == expires


# ── CatalogTemplateCreate ─────────────────────────────────────────────────────

def test_catalog_template_create_valid():
    t = CatalogTemplateCreate(
        category="app",
        name="Permit Application Template",
        schema_json={"pages": []},
    )
    assert t.category == "app"
    assert t.schema_json == {"pages": []}


@pytest.mark.parametrize("category", ["app", "workflow", "dmn", "case_type"])
def test_catalog_template_valid_categories(category):
    CatalogTemplateCreate(
        category=category,
        name="Test Template",
        schema_json={},
    )


def test_catalog_template_invalid_category():
    with pytest.raises(ValidationError):
        CatalogTemplateCreate(
            category="report",  # not allowed
            name="Test",
            schema_json={},
        )


def test_catalog_template_name_too_short():
    with pytest.raises(ValidationError):
        CatalogTemplateCreate(category="app", name="x", schema_json={})


def test_catalog_template_with_tags():
    t = CatalogTemplateCreate(
        category="workflow",
        name="Review Process",
        schema_json={"bpmn": "..."},
        tags=["permits", "review"],
    )
    assert t.tags == ["permits", "review"]
