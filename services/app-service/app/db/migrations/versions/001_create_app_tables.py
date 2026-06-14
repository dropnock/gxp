"""create app tables

Revision ID: 001
Revises:
Create Date: 2026-06-13
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "apps",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="draft"),
        sa.Column("current_version_id", UUID(as_uuid=True), nullable=True),
        sa.Column("created_by", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.create_index("ix_apps_status", "apps", ["status"])
    op.create_index("ix_apps_created_by", "apps", ["created_by"])

    op.create_table(
        "app_pages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("app_id", UUID(as_uuid=True), sa.ForeignKey("apps.id"), nullable=False),
        sa.Column("page_id", sa.Text, nullable=False),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("route", sa.Text, nullable=False),
        sa.Column("gjs_data", JSONB, nullable=False, server_default="{}"),
        sa.Column("components", JSONB, nullable=False, server_default="[]"),
        sa.Column("styles", JSONB, nullable=False, server_default="{}"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("app_id", "page_id", name="uq_app_page_id"),
        sa.UniqueConstraint("app_id", "route", name="uq_app_page_route"),
    )
    op.create_index("ix_app_pages_app_id", "app_pages", ["app_id"])

    op.create_table(
        "app_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("app_id", UUID(as_uuid=True), sa.ForeignKey("apps.id"), nullable=False),
        sa.Column("version_number", sa.Integer, nullable=False),
        sa.Column("schema_json", JSONB, nullable=False),
        sa.Column("minio_key", sa.Text, nullable=False),
        sa.Column("published_by", sa.Text, nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("app_id", "version_number", name="uq_app_version"),
    )
    op.create_index("ix_app_versions_app_id", "app_versions", ["app_id"])

    op.create_table(
        "app_permissions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("app_id", UUID(as_uuid=True), sa.ForeignKey("apps.id"), nullable=False),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("permission", sa.String(8), nullable=False, server_default="view"),
        sa.Column("granted_by", sa.Text, nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("app_id", "role", name="uq_app_permission_role"),
    )


def downgrade() -> None:
    op.drop_table("app_permissions")
    op.drop_table("app_versions")
    op.drop_table("app_pages")
    op.drop_table("apps")
