import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_]{1,61}[a-z0-9]$")


class TenantCreate(BaseModel):
    slug: str = Field(..., description="URL-safe identifier, e.g. 'dot' or 'dept_of_health'")
    name: str = Field(..., min_length=2, max_length=200)

    @field_validator("slug")
    @classmethod
    def slug_must_be_valid(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError("slug must be 3-63 lowercase alphanumeric characters or underscores")
        return v


class TenantUpdate(BaseModel):
    name: str | None = None
    status: Literal["active", "suspended"] | None = None


class TenantRead(BaseModel):
    id: UUID
    slug: str
    name: str
    keycloak_realm: str
    status: str
    created_at: datetime
    suspended_at: datetime | None = None

    model_config = {"from_attributes": True}


class CrossTenantGrantCreate(BaseModel):
    granting_tenant_slug: str
    resource_type: Literal["document", "app", "workflow_definition", "case"]
    resource_id: UUID
    permissions: list[Literal["read", "write"]]
    expires_at: datetime | None = None


class CrossTenantGrantRead(BaseModel):
    id: UUID
    requesting_tenant_id: UUID
    granting_tenant_id: UUID
    resource_type: str
    resource_id: UUID
    permissions: list[str]
    status: str
    expires_at: datetime | None = None
    created_at: datetime
    approved_at: datetime | None = None

    model_config = {"from_attributes": True}


class CatalogTemplateCreate(BaseModel):
    model_config = {"populate_by_name": True}

    category: Literal["app", "workflow", "dmn", "case_type"]
    name: str = Field(..., min_length=2, max_length=200)
    description: str | None = None
    template_body: dict = Field(..., alias="schema_json")
    tags: list[str] | None = None


class CatalogTemplateRead(BaseModel):
    id: UUID
    category: str
    name: str
    description: str | None = None
    version: str
    tags: list[str] | None = None
    published_at: datetime
    is_active: bool

    model_config = {"from_attributes": True}
